from repositorio.base_sql import RepositorioSQL
from repositorio.repositorio_prestamo_sql import ESTADO_SQL
from dominio.gestion_control.reporte import FILAS_POR_PAGINA

TIPO_PERSONA_SQL = '''CASE WHEN EXISTS(SELECT 1 FROM estudiante e WHERE e.dni=p.dni_persona) THEN 'ESTUDIANTE'
    WHEN EXISTS(SELECT 1 FROM docente doc WHERE doc.dni=p.dni_persona) THEN 'DOCENTE'
    WHEN EXISTS(SELECT 1 FROM administrativo adm WHERE adm.dni=p.dni_persona) THEN 'ADMINISTRATIVO' END'''


class RepositorioReporteSQL(RepositorioSQL):
    def consultar_reportes(self, filtro, paginar=True):
        es_devolucion = filtro.tipo == 'devoluciones'
        campo_fecha = 'd.fecha_devolucion' if es_devolucion else 'p.fecha_entrega'
        condiciones = ['d.fecha_devolucion IS NOT NULL'] if es_devolucion else ['1=1']
        parametros = []
        for fecha, operador in ((filtro.inicio, '>='), (filtro.fin, '<')):
            if fecha:
                condiciones.append(campo_fecha + operador + '%s')
                parametros.append(fecha)
        if filtro.estado:
            condiciones.append('(' + ESTADO_SQL + ')=%s')
            parametros.append(filtro.estado)
        if filtro.modalidad:
            condiciones.append('p.tipo_prestamo=%s')
            parametros.append(filtro.modalidad)
        if filtro.tipo_persona:
            condiciones.append('(' + TIPO_PERSONA_SQL + ')=%s')
            parametros.append(filtro.tipo_persona)
        if filtro.q:
            condiciones.append(
                '''(p.dni_persona LIKE %s OR CONCAT(per.nombres,' ',per.apellidos) LIKE %s
                OR b.codigo_inventario LIKE %s OR r.nombre LIKE %s OR EXISTS (
                    SELECT 1 FROM participante_prestamo pp JOIN persona integrante ON integrante.dni=pp.dni_persona
                    WHERE pp.id_prestamo=p.id_prestamo AND (pp.dni_persona LIKE %s OR
                    CONCAT(integrante.nombres,' ',integrante.apellidos) LIKE %s)))'''
            )
            parametros += ['%' + filtro.q + '%'] * 6
        joins = ''' FROM prestamo p JOIN persona per ON per.dni=p.dni_persona
            JOIN detalle_prestamo d ON d.id_prestamo=p.id_prestamo
            JOIN bien_material b ON b.id_bien=d.id_bien JOIN recurso r ON r.id_recurso=b.id_recurso
            WHERE ''' + ' AND '.join(condiciones)
        columnas = f'''SELECT p.id_prestamo,p.dni_persona,CONCAT(per.nombres,' ',per.apellidos) AS solicitante,
            p.tipo_prestamo,p.fecha_entrega,{ESTADO_SQL} AS estado,d.id_detalle,b.codigo_inventario,
            r.nombre AS recurso,d.fecha_limite_devolucion,d.fecha_devolucion,d.condicion_devolucion,
            {TIPO_PERSONA_SQL} AS tipo_persona,
            CASE WHEN d.fecha_devolucion IS NOT NULL THEN 'DEVUELTO'
                WHEN d.fecha_limite_devolucion<UTC_TIMESTAMP() THEN 'VENCIDO' ELSE 'PENDIENTE' END AS situacion'''
        resumen = self.consultar_sql(
            '''SELECT COUNT(*) AS detalles,COUNT(DISTINCT p.id_prestamo) AS prestamos,
            COALESCE(SUM(d.fecha_devolucion IS NOT NULL),0) AS devueltos,
            COALESCE(SUM(d.fecha_devolucion IS NULL),0) AS pendientes,
            COALESCE(SUM(d.fecha_devolucion IS NULL AND d.fecha_limite_devolucion<UTC_TIMESTAMP()),0) AS vencidos'''
            + joins,
            parametros,
            una=True,
        )
        resumen = {k: int(v) for k, v in resumen.items()}
        sql = (
            columnas + joins + ' ORDER BY ' + campo_fecha + ' DESC,p.id_prestamo DESC,d.id_detalle'
        )
        if paginar:
            filtro.pagina = min(
                filtro.pagina,
                max(1, (resumen['detalles'] + FILAS_POR_PAGINA - 1) // FILAS_POR_PAGINA),
            )
            sql += f' LIMIT {FILAS_POR_PAGINA} OFFSET %s'
            parametros.append((filtro.pagina - 1) * FILAS_POR_PAGINA)
        filas = self.consultar_sql(sql, parametros)
        self._consultar_integrantes_prestamos(filas)
        return filas, resumen

    def _consultar_integrantes_prestamos(self, filas):
        identificadores = sorted({fila['id_prestamo'] for fila in filas})
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
        por_prestamo = {i: [] for i in identificadores}
        for persona in integrantes:
            por_prestamo[persona['id_prestamo']].append(
                f'{persona["nombre"]} ({persona["dni_persona"]})'
            )
        for fila in filas:
            fila['integrantes'] = '; '.join(por_prestamo[fila['id_prestamo']])
