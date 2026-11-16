from dataclasses import dataclass
from repositorio.base_sql import RepositorioSQL
from repositorio.repositorio_prestamo_sql import ESTADO_SQL
from dominio.gestion_control.reporte import FILAS_POR_PAGINA, paginas_reporte
from repositorio.repositorio_persona_sql import TABLAS_TIPO
from dominio.gestion_prestamos.reserva import ESTADOS_PENDIENTES

SQL_SELECT = 'SELECT '
SQL_AND = ' AND '

BUSQUEDA_PRESTAMO = '''p.dni_persona LIKE %s OR CONCAT(per.nombres,' ',per.apellidos) LIKE %s
    OR b.codigo_inventario LIKE %s OR r.nombre LIKE %s OR EXISTS (
        SELECT 1 FROM participante_prestamo pp JOIN persona integrante ON integrante.dni=pp.dni_persona
        WHERE pp.id_prestamo=p.id_prestamo AND (pp.dni_persona LIKE %s OR
        CONCAT(integrante.nombres,' ',integrante.apellidos) LIKE %s))'''
JOINS_PRESTAMO = '''FROM prestamo p JOIN persona per ON per.dni=p.dni_persona
    JOIN detalle_prestamo d ON d.id_prestamo=p.id_prestamo
    JOIN bien_material b ON b.id_bien=d.id_bien JOIN recurso r ON r.id_recurso=b.id_recurso
    JOIN categoria_recurso c ON c.id_categoria=r.id_categoria'''
PERIODO_SQL = "DATE_FORMAT(CONVERT_TZ(p.fecha_entrega,'+00:00','-05:00'),'%Y-%m')"


@dataclass
class ConsultaReporte:
    filas: str
    resumen: str
    parametros: list


class RepositorioReporteSQL(RepositorioSQL):
    def _consulta_reporte(self, filtro):
        consultas = {
            'prestamos': self._consulta_prestamos,
            'devoluciones': self._consulta_devoluciones,
            'atrasados': self._consulta_atrasados,
            'inventario': self._consulta_inventario,
            'uso_recursos': self._consulta_uso_recursos,
            'reservas': self._consulta_reservas,
            'sanciones': self._consulta_sanciones,
            'danos_perdidas': self._consulta_danos_perdidas,
        }
        return consultas[filtro.tipo](filtro)

    def consultar_filas_reporte(self, filtro):
        consulta = self._consulta_reporte(filtro)
        filas = self.consultar_sql(consulta.filas, consulta.parametros)
        if filtro.tipo in ('prestamos', 'devoluciones', 'sanciones'):
            self._consultar_integrantes_prestamos(filas)
        return filas

    def consultar_reportes(self, filtro, paginar=True):
        consulta = self._consulta_reporte(filtro)
        resumen = self.consultar_sql(consulta.resumen, consulta.parametros, una=True)
        resumen = {k: (v if v is not None else 0) for k, v in resumen.items()}
        resumen['detalles'] = int(resumen['detalles'])
        sql, parametros = consulta.filas, list(consulta.parametros)
        if paginar:
            paginas = paginas_reporte(resumen['detalles'])
            filtro.pagina = min(filtro.pagina, paginas)
            sql += f' LIMIT {FILAS_POR_PAGINA} OFFSET %s'
            parametros.append((filtro.pagina - 1) * FILAS_POR_PAGINA)
        filas = self.consultar_sql(sql, parametros)
        if filtro.tipo in ('prestamos', 'devoluciones', 'sanciones'):
            self._consultar_integrantes_prestamos(filas)
        return filas, resumen

    def _filtros_comunes(self, filtro, busqueda, campo_fecha=None, campo_estado=None):
        condiciones, parametros = ['1=1'], []
        if campo_fecha:
            for fecha, operador in ((filtro.inicio, '>='), (filtro.fin, '<')):
                if fecha:
                    condiciones.append(campo_fecha + operador + '%s')
                    parametros.append(fecha)
        if filtro.id_categoria:
            condiciones.append('r.id_categoria=%s')
            parametros.append(filtro.id_categoria)
        if filtro.estado and campo_estado:
            condiciones.append('(' + campo_estado + ')=%s')
            parametros.append(filtro.estado)
        if filtro.q:
            condiciones.append('(' + busqueda + ')')
            parametros.extend(['%' + filtro.q + '%'] * busqueda.count('%s'))
        return condiciones, parametros

    def _filtros_personas(self, filtro, condiciones, parametros):
        if filtro.modalidad:
            condiciones.append('p.tipo_prestamo=%s')
            parametros.append(filtro.modalidad)
        if filtro.tipo_persona:
            tabla = TABLAS_TIPO[filtro.tipo_persona]
            condiciones.append(f'EXISTS(SELECT 1 FROM {tabla} t WHERE t.dni=p.dni_persona)')

    def _consulta_prestamos(self, filtro):
        condiciones, parametros = self._filtros_comunes(
            filtro, BUSQUEDA_PRESTAMO, 'p.fecha_entrega', ESTADO_SQL
        )
        self._filtros_personas(filtro, condiciones, parametros)
        columnas = '''p.id_prestamo,p.dni_persona,CONCAT(per.nombres,' ',per.apellidos) AS solicitante,
            p.tipo_prestamo,p.fecha_entrega,b.codigo_inventario,r.nombre AS recurso,
            c.nombre AS categoria,d.fecha_limite_devolucion,d.fecha_devolucion,
            CASE WHEN d.fecha_devolucion IS NOT NULL THEN 'DEVUELTO'
                WHEN d.fecha_limite_devolucion<UTC_TIMESTAMP() THEN 'VENCIDO' ELSE 'PENDIENTE' END AS situacion'''
        resumen = '''COUNT(*) AS detalles,COUNT(DISTINCT p.id_prestamo) AS prestamos,
            COALESCE(SUM(d.fecha_devolucion IS NOT NULL),0) AS devueltos,
            COALESCE(SUM(d.fecha_devolucion IS NULL),0) AS pendientes,
            COALESCE(SUM(d.fecha_devolucion IS NULL AND d.fecha_limite_devolucion<UTC_TIMESTAMP()),0) AS vencidos'''
        origen = JOINS_PRESTAMO + ' WHERE ' + SQL_AND.join(condiciones)
        return ConsultaReporte(
            SQL_SELECT
            + columnas
            + ' '
            + origen
            + ' ORDER BY p.fecha_entrega DESC,p.id_prestamo DESC,d.id_detalle',
            SQL_SELECT + resumen + ' ' + origen,
            parametros,
        )

    def _consulta_devoluciones(self, filtro):
        condiciones, parametros = self._filtros_comunes(
            filtro, BUSQUEDA_PRESTAMO, 'd.fecha_devolucion', ESTADO_SQL
        )
        self._filtros_personas(filtro, condiciones, parametros)
        condiciones.append('d.fecha_devolucion IS NOT NULL')
        if filtro.cumplimiento:
            operador = '<=' if filtro.cumplimiento == 'A_TIEMPO' else '>'
            condiciones.append('d.fecha_devolucion' + operador + 'd.fecha_limite_devolucion')
        retraso = 'GREATEST(TIMESTAMPDIFF(MINUTE,d.fecha_limite_devolucion,d.fecha_devolucion),0)'
        columnas = f'''p.id_prestamo,p.dni_persona,CONCAT(per.nombres,' ',per.apellidos) AS solicitante,
            p.tipo_prestamo,b.codigo_inventario,r.nombre AS recurso,c.nombre AS categoria,
            p.fecha_entrega,d.fecha_limite_devolucion,d.fecha_devolucion,d.condicion_devolucion,
            CASE WHEN d.fecha_devolucion<=d.fecha_limite_devolucion THEN 'A_TIEMPO'
                ELSE 'TARDIA' END AS cumplimiento,{retraso} AS retraso_minutos'''
        resumen = f'''COUNT(*) AS detalles,
            COALESCE(SUM(d.fecha_devolucion<=d.fecha_limite_devolucion),0) AS puntuales,
            COALESCE(SUM(d.fecha_devolucion>d.fecha_limite_devolucion),0) AS tardias,
            COALESCE(100.0*SUM(d.fecha_devolucion<=d.fecha_limite_devolucion)/NULLIF(COUNT(*),0),0) AS porcentaje_puntual,
            COALESCE(AVG(CASE WHEN d.fecha_devolucion>d.fecha_limite_devolucion THEN {retraso} END),0) AS retraso_promedio'''
        origen = JOINS_PRESTAMO + ' WHERE ' + SQL_AND.join(condiciones)
        return ConsultaReporte(
            SQL_SELECT
            + columnas
            + ' '
            + origen
            + ' ORDER BY d.fecha_devolucion DESC,p.id_prestamo DESC,d.id_detalle',
            SQL_SELECT + resumen + ' ' + origen,
            parametros,
        )

    def _consulta_atrasados(self, filtro):
        condiciones, parametros = self._filtros_comunes(
            filtro, BUSQUEDA_PRESTAMO, 'd.fecha_limite_devolucion'
        )
        self._filtros_personas(filtro, condiciones, parametros)
        condiciones.extend(
            ('d.fecha_devolucion IS NULL', 'd.fecha_limite_devolucion<UTC_TIMESTAMP()')
        )
        retraso = 'TIMESTAMPDIFF(MINUTE,d.fecha_limite_devolucion,UTC_TIMESTAMP())'
        columnas = f'''p.id_prestamo,p.dni_persona,CONCAT(per.nombres,' ',per.apellidos) AS solicitante,
            b.codigo_inventario,r.nombre AS recurso,p.fecha_entrega,d.fecha_limite_devolucion,
            {retraso} AS retraso_minutos'''
        resumen = f'''COUNT(*) AS detalles,COUNT(DISTINCT p.id_prestamo) AS prestamos,
            COUNT(DISTINCT p.dni_persona) AS responsables,COALESCE(MAX({retraso}),0) AS retraso_maximo'''
        origen = '''FROM detalle_prestamo d JOIN prestamo p ON p.id_prestamo=d.id_prestamo
            JOIN persona per ON per.dni=p.dni_persona JOIN bien_material b ON b.id_bien=d.id_bien
            JOIN recurso r ON r.id_recurso=b.id_recurso WHERE ''' + SQL_AND.join(condiciones)
        return ConsultaReporte(
            SQL_SELECT
            + columnas
            + ' '
            + origen
            + ' ORDER BY d.fecha_limite_devolucion,p.id_prestamo,d.id_detalle',
            SQL_SELECT + resumen + ' ' + origen,
            parametros,
        )

    def _consulta_inventario(self, filtro):
        condiciones, parametros = self._filtros_comunes(
            filtro,
            'b.codigo_inventario LIKE %s OR r.nombre LIKE %s OR r.marca LIKE %s OR r.modelo LIKE %s OR b.numero_serie LIKE %s',
            campo_estado='b.estado',
        )
        if filtro.ubicacion:
            condiciones.append('b.ubicacion LIKE %s')
            parametros.append('%' + filtro.ubicacion + '%')
        origen = '''FROM bien_material b JOIN recurso r ON r.id_recurso=b.id_recurso
            JOIN categoria_recurso c ON c.id_categoria=r.id_categoria WHERE ''' + SQL_AND.join(
            condiciones
        )
        columnas = '''b.id_bien,b.codigo_inventario,r.nombre AS recurso,c.nombre AS categoria,
            r.marca,r.modelo,b.numero_serie,b.estado,b.ubicacion,b.fecha_adquisicion'''
        estados = {
            'DISPONIBLE': 'disponibles',
            'PRESTADO': 'prestados',
            'RESERVADO': 'reservados',
            'DANADO': 'danados',
            'MANTENIMIENTO': 'mantenimiento',
            'PERDIDO': 'perdidos',
        }
        resumen = 'COUNT(*) AS detalles,COUNT(DISTINCT r.id_recurso) AS recursos,' + ','.join(
            f"COALESCE(SUM(b.estado='{estado}'),0) AS {campo}" for estado, campo in estados.items()
        )
        return ConsultaReporte(
            SQL_SELECT
            + columnas
            + ' '
            + origen
            + ' ORDER BY r.nombre,b.codigo_inventario,b.id_bien',
            SQL_SELECT + resumen + ' ' + origen,
            parametros,
        )

    def _consulta_uso_recursos(self, filtro):
        condiciones, parametros = self._filtros_comunes(
            filtro, BUSQUEDA_PRESTAMO, 'p.fecha_entrega'
        )
        self._filtros_personas(filtro, condiciones, parametros)
        condiciones.append('p.fecha_entrega IS NOT NULL')
        origen = JOINS_PRESTAMO + ' WHERE ' + SQL_AND.join(condiciones)
        columnas = f'''{PERIODO_SQL} AS periodo,r.nombre AS recurso,c.nombre AS categoria,
            COUNT(DISTINCT p.id_prestamo) AS prestamos,COUNT(*) AS bienes_prestados,
            COUNT(DISTINCT p.dni_persona) AS solicitantes'''
        resumen = f'''COUNT(DISTINCT {PERIODO_SQL},r.id_recurso) AS detalles,
            COUNT(DISTINCT p.id_prestamo) AS prestamos,COUNT(*) AS bienes_prestados,
            COUNT(DISTINCT r.id_recurso) AS recursos,COUNT(DISTINCT p.dni_persona) AS solicitantes'''
        return ConsultaReporte(
            SQL_SELECT
            + columnas
            + ' '
            + origen
            + ' GROUP BY periodo,r.id_recurso,r.nombre,c.nombre ORDER BY periodo DESC,bienes_prestados DESC,r.nombre,r.id_recurso',
            SQL_SELECT + resumen + ' ' + origen,
            parametros,
        )

    def _consulta_reservas(self, filtro):
        condiciones, parametros = self._filtros_comunes(
            filtro,
            "p.dni_persona LIKE %s OR CONCAT(per.nombres,' ',per.apellidos) LIKE %s OR r.nombre LIKE %s",
            'p.fecha_solicitud',
            'p.estado',
        )
        self._filtros_personas(filtro, condiciones, parametros)
        if filtro.tipo_gestion:
            condiciones.append('p.tipo_gestion=%s')
            parametros.append(filtro.tipo_gestion)
        origen = '''FROM reserva p JOIN persona per ON per.dni=p.dni_persona
            JOIN recurso r ON r.id_recurso=p.id_recurso
            JOIN categoria_recurso c ON c.id_categoria=r.id_categoria WHERE ''' + SQL_AND.join(
            condiciones
        )
        columnas = '''p.id_reserva,p.tipo_gestion,p.dni_persona,
            CONCAT(per.nombres,' ',per.apellidos) AS solicitante,
            r.nombre AS recurso,c.nombre AS categoria,p.fecha_solicitud,p.fecha_requerida,
            p.estado,p.fecha_limite_vencimiento'''
        pendientes = ','.join("'" + e + "'" for e in ESTADOS_PENDIENTES)
        resumen = f'''COUNT(*) AS detalles,COALESCE(SUM(p.estado IN ({pendientes})),0) AS pendientes,
            COALESCE(SUM(p.estado='ATENDIDA'),0) AS atendidas,
            COALESCE(SUM(p.estado='CANCELADA'),0) AS canceladas,
            COALESCE(SUM(p.estado='RECHAZADA'),0) AS rechazadas,
            COALESCE(SUM(p.estado='EXPIRADA'),0) AS expiradas'''
        return ConsultaReporte(
            SQL_SELECT
            + columnas
            + ' '
            + origen
            + ' ORDER BY p.fecha_solicitud DESC,p.id_reserva DESC',
            SQL_SELECT + resumen + ' ' + origen,
            parametros,
        )

    def _consulta_sanciones(self, filtro):
        condiciones, parametros = self._filtros_comunes(
            filtro, BUSQUEDA_PRESTAMO, 's.fecha', 's.estado'
        )
        self._filtros_personas(filtro, condiciones, parametros)
        origen = (
            JOINS_PRESTAMO
            + ''' JOIN incidencia i ON i.id_detalle=d.id_detalle
            JOIN sancion s ON s.id_incidencia_ref=i.id_incidencia WHERE '''
            + SQL_AND.join(condiciones)
        )
        columnas = '''s.id_sancion,p.id_prestamo,p.dni_persona,
            CONCAT(per.nombres,' ',per.apellidos) AS solicitante,
            p.tipo_prestamo,b.codigo_inventario,r.nombre AS recurso,c.nombre AS categoria,
            s.fecha,s.motivo,s.descripcion,s.estado,s.fecha_levantamiento,s.justificacion_levantamiento'''
        resumen = '''COUNT(*) AS detalles,COALESCE(SUM(s.estado='ACTIVA'),0) AS activas,
            COALESCE(SUM(s.estado='LEVANTADA'),0) AS levantadas,
            COALESCE(SUM(s.estado='CUMPLIDA'),0) AS cumplidas,
            COALESCE(SUM(s.estado='ANULADA'),0) AS anuladas'''
        return ConsultaReporte(
            SQL_SELECT + columnas + ' ' + origen + ' ORDER BY s.fecha DESC,s.id_sancion DESC',
            SQL_SELECT + resumen + ' ' + origen,
            parametros,
        )

    def _consulta_danos_perdidas(self, filtro):
        condiciones, parametros = self._filtros_comunes(
            filtro,
            "b.codigo_inventario LIKE %s OR r.nombre LIKE %s OR h.dni_responsable LIKE %s OR CONCAT(reg.nombres,' ',reg.apellidos) LIKE %s OR h.observacion LIKE %s",
            'h.fecha',
            'h.estado_nuevo',
        )
        condiciones.extend(("h.entidad='BIEN_MATERIAL'", "h.estado_nuevo IN ('DANADO','PERDIDO')"))
        origen = '''FROM historial_estado h JOIN bien_material b ON b.id_bien=h.id_entidad
            JOIN recurso r ON r.id_recurso=b.id_recurso
            JOIN categoria_recurso c ON c.id_categoria=r.id_categoria
            LEFT JOIN persona reg ON reg.dni=h.dni_responsable WHERE ''' + SQL_AND.join(condiciones)
        columnas = '''h.id_historial_estado,h.fecha,b.id_bien,b.codigo_inventario,r.nombre AS recurso,
            c.nombre AS categoria,h.estado_nuevo AS tipo_evento,b.estado AS estado_actual,
            h.dni_responsable AS dni_registrador,CONCAT(reg.nombres,' ',reg.apellidos) AS registrador,
            h.observacion'''
        resumen = '''COUNT(*) AS detalles,COUNT(DISTINCT b.id_bien) AS bienes,
            COALESCE(SUM(h.estado_nuevo='DANADO'),0) AS danos,
            COALESCE(SUM(h.estado_nuevo='PERDIDO'),0) AS perdidas'''
        return ConsultaReporte(
            SQL_SELECT
            + columnas
            + ' '
            + origen
            + ' ORDER BY h.fecha DESC,h.id_historial_estado DESC',
            SQL_SELECT + resumen + ' ' + origen,
            parametros,
        )

    def _consultar_integrantes_prestamos(self, filas):
        for fila in filas:
            fila['integrantes'] = ''
        identificadores = sorted(
            {fila['id_prestamo'] for fila in filas if fila['tipo_prestamo'] == 'GRUPAL'}
        )
        if not identificadores:
            return
        marcas = ','.join(['%s'] * len(identificadores))
        integrantes = self.consultar_sql(
            f'''SELECT pp.id_prestamo,pp.dni_persona,
            CONCAT(p.nombres,' ',p.apellidos) AS nombre FROM participante_prestamo pp
            JOIN persona p ON p.dni=pp.dni_persona WHERE pp.id_prestamo IN ({marcas})
            ORDER BY pp.id_prestamo,pp.responsable DESC,pp.id_participante''',
            identificadores,
        )
        por_prestamo: dict[int, list[str]] = {i: [] for i in identificadores}
        for persona in integrantes:
            por_prestamo[persona['id_prestamo']].append(
                f'{persona["nombre"]} ({persona["dni_persona"]})'
            )
        for fila in filas:
            fila['integrantes'] = '; '.join(por_prestamo.get(fila['id_prestamo'], []))
