from dataclasses import dataclass

from repositorio.base_datos.base_sql import RepositorioSQL
from repositorio.prestamos.repositorio_prestamo_sql import ESTADO_SQL, SITUACION_BIEN_SQL
from repositorio.personas_usuarios.repositorio_persona_sql import TABLAS_TIPO
from repositorio.reportes.repositorio_historial_sql import RepositorioHistorialSQL

BUSQUEDA_PRESTAMO = """
    p.dni_persona LIKE %s
    OR CONCAT(per.nombres, ' ', per.apellidos) LIKE %s
    OR b.codigo_inventario LIKE %s
    OR r.nombre LIKE %s
    OR EXISTS (
        SELECT 1
        FROM participante_prestamo pp
        JOIN persona integrante ON integrante.dni = pp.dni_persona
        WHERE pp.id_prestamo = p.id_prestamo
          AND (
              pp.dni_persona LIKE %s
              OR CONCAT(integrante.nombres, ' ', integrante.apellidos) LIKE %s
          )
    )
"""

JOINS_PRESTAMO = """
    FROM prestamo p
    JOIN persona per ON per.dni = p.dni_persona
    JOIN detalle_prestamo d ON d.id_prestamo = p.id_prestamo
    JOIN bien_material b ON b.id_bien = d.id_bien
    JOIN recurso r ON r.id_recurso = b.id_recurso
    JOIN categoria_recurso c ON c.id_categoria = r.id_categoria
"""

@dataclass
class ConsultaReporte:
    sql_reporte: str
    parametros: list

class RepositorioReporteSQL(RepositorioSQL):

    def consultar_historial(self, filtro, solo_prestamos=False):
        resultado = RepositorioHistorialSQL(self.conexion, self._cursor).consultar_historial(
            filtro, solo_prestamos
        )
        self._consultar_integrantes_prestamos(resultado['prestamos'])
        return resultado

    def _preparar_consulta_sql_del_reporte(self, filtro):
        funciones = {
            'prestamos': self._consulta_prestamos,
            'devoluciones': self._consulta_devoluciones,
            'atrasados': self._consulta_atrasados,
            'inventario': self._consulta_inventario,
            'reservas': self._consulta_reservas,
            'sanciones': self._consulta_sanciones,
            'danos_perdidas': self._consulta_danos_perdidas,
            'personas': self._consulta_personas,
        }
        if filtro.tipo not in funciones:
            raise ValueError(f'Tipo de reporte no válido: {filtro.tipo}')
        return funciones[filtro.tipo](filtro)

    def consultar_filas_reporte(self, filtro):
        consulta = self._preparar_consulta_sql_del_reporte(filtro)
        filas = self.consultar_sql(consulta.sql_reporte, consulta.parametros)
        if filtro.tipo in ('prestamos', 'devoluciones', 'sanciones'):
            self._consultar_integrantes_prestamos(filas)
        return filas

    @staticmethod
    def _armar_clausula_where(condiciones):
        return 'WHERE ' + ' AND '.join(condiciones) if condiciones else ''

    def _construir_filtros_sql_comunes(self, filtro, busqueda, campo_fecha=None, campo_estado=None):
        condiciones = []
        parametros = []

        if campo_fecha and filtro.inicio_del_rango_utc:
            condiciones.append(f'{campo_fecha} >= %s')
            parametros.append(filtro.inicio_del_rango_utc)
        if campo_fecha and filtro.fin_exclusivo_del_rango_utc:
            condiciones.append(f'{campo_fecha} < %s')
            parametros.append(filtro.fin_exclusivo_del_rango_utc)

        if filtro.id_categoria:
            condiciones.append('r.id_categoria = %s')
            parametros.append(filtro.id_categoria)

        if campo_estado and filtro.estado:
            condiciones.append(f'({campo_estado}) = %s')
            parametros.append(filtro.estado)

        if filtro.q:
            condiciones.append(f'({busqueda})')
            texto = f'%{filtro.q}%'
            parametros.extend([texto] * busqueda.count('%s'))

        return condiciones, parametros

    def _agregar_filtros_sql_de_personas(self, filtro, condiciones, parametros, incluir_modalidad=True):

        if incluir_modalidad and filtro.modalidad:
            condiciones.append('p.tipo_prestamo = %s')
            parametros.append(filtro.modalidad)

        if filtro.tipo_persona:
            tabla = TABLAS_TIPO[filtro.tipo_persona]
            condiciones.append(f'EXISTS (SELECT 1 FROM {tabla} t WHERE t.dni = p.dni_persona)')

    # Préstamos

    def _consulta_prestamos(self, filtro):
        condiciones, parametros = self._construir_filtros_sql_comunes(
            filtro, BUSQUEDA_PRESTAMO, 'p.fecha_entrega', ESTADO_SQL
        )
        self._agregar_filtros_sql_de_personas(filtro, condiciones, parametros)
        where_sql = self._armar_clausula_where(condiciones)

        tablas = JOINS_PRESTAMO

        sql_reporte = f"""
            SELECT
                p.id_prestamo, p.dni_persona,
                CONCAT(per.nombres, ' ', per.apellidos) AS solicitante,
                p.tipo_prestamo, p.fecha_entrega,
                b.codigo_inventario, r.nombre AS recurso,
                c.nombre AS categoria,
                d.fecha_limite_devolucion, d.fecha_devolucion,
                {SITUACION_BIEN_SQL} AS situacion
            {tablas}
            {where_sql}
            ORDER BY p.fecha_entrega DESC, p.id_prestamo DESC, d.id_detalle
        """

        return ConsultaReporte(
            sql_reporte=sql_reporte,
            parametros=parametros,
        )

    # Devoluciones y cumplimiento

    def _consulta_devoluciones(self, filtro):
        condiciones, parametros = self._construir_filtros_sql_comunes(
            filtro, BUSQUEDA_PRESTAMO, 'd.fecha_devolucion'
        )
        condiciones.append('d.fecha_devolucion IS NOT NULL')

        if filtro.cumplimiento == 'A_TIEMPO':
            condiciones.append('d.fecha_devolucion <= d.fecha_limite_devolucion')
        elif filtro.cumplimiento:
            condiciones.append('d.fecha_devolucion > d.fecha_limite_devolucion')

        where_sql = self._armar_clausula_where(condiciones)
        retraso = (
            'GREATEST(TIMESTAMPDIFF(MINUTE, d.fecha_limite_devolucion, d.fecha_devolucion), 0)'
        )
        tablas = JOINS_PRESTAMO

        sql_reporte = f"""
            SELECT
                p.id_prestamo, p.dni_persona,
                CONCAT(per.nombres, ' ', per.apellidos) AS solicitante,
                p.tipo_prestamo, b.codigo_inventario,
                r.nombre AS recurso, c.nombre AS categoria,
                p.fecha_entrega, d.fecha_limite_devolucion,
                d.fecha_devolucion, d.condicion_devolucion,
                CASE
                    WHEN d.fecha_devolucion <= d.fecha_limite_devolucion THEN 'A_TIEMPO'
                    ELSE 'TARDIA'
                END AS cumplimiento,
                {retraso} AS retraso_minutos
            {tablas}
            {where_sql}
            ORDER BY d.fecha_devolucion DESC, p.id_prestamo DESC, d.id_detalle
        """

        return ConsultaReporte(
            sql_reporte=sql_reporte,
            parametros=parametros,
        )

    # Bienes atrasados

    def _consulta_atrasados(self, filtro):

        condiciones, parametros = self._construir_filtros_sql_comunes(
            filtro, BUSQUEDA_PRESTAMO, 'd.fecha_limite_devolucion'
        )
        condiciones.append('d.fecha_devolucion IS NULL AND d.fecha_regularizacion IS NULL')
        condiciones.append('d.fecha_limite_devolucion < UTC_TIMESTAMP()')
        where_sql = self._armar_clausula_where(condiciones)

        tablas = """
            FROM detalle_prestamo d
            JOIN prestamo p ON p.id_prestamo = d.id_prestamo
            JOIN persona per ON per.dni = p.dni_persona
            JOIN bien_material b ON b.id_bien = d.id_bien
            JOIN recurso r ON r.id_recurso = b.id_recurso
        """

        retraso = 'TIMESTAMPDIFF(MINUTE, d.fecha_limite_devolucion, UTC_TIMESTAMP())'

        sql_reporte = f"""
            SELECT
                p.id_prestamo, p.dni_persona,
                CONCAT(per.nombres, ' ', per.apellidos) AS solicitante,
                b.codigo_inventario, r.nombre AS recurso,
                p.fecha_entrega, d.fecha_limite_devolucion,
                {retraso} AS retraso_minutos
            {tablas}
            {where_sql}
            ORDER BY d.fecha_limite_devolucion, p.id_prestamo, d.id_detalle
        """

        return ConsultaReporte(
            sql_reporte=sql_reporte,
            parametros=parametros,
        )

    # Inventario

    def _consulta_inventario(self, filtro):
        busqueda = """
            b.codigo_inventario LIKE %s OR r.nombre LIKE %s
            OR r.marca LIKE %s OR r.modelo LIKE %s OR b.numero_serie LIKE %s
            OR b.identificador_sistema LIKE %s
        """
        condiciones, parametros = self._construir_filtros_sql_comunes(filtro, busqueda, campo_estado='b.estado')
        if filtro.ubicacion:
            condiciones.append('b.ubicacion LIKE %s')
            parametros.append(f'%{filtro.ubicacion}%')
        where_sql = self._armar_clausula_where(condiciones)

        tablas = """
            FROM bien_material b
            JOIN recurso r ON r.id_recurso = b.id_recurso
            JOIN categoria_recurso c ON c.id_categoria = r.id_categoria
        """

        sql_reporte = f"""
            SELECT
                b.id_bien, b.codigo_inventario, b.identificador_sistema,
                r.nombre AS recurso, c.nombre AS categoria,
                r.marca, r.modelo, b.numero_serie,
                b.estado, b.ubicacion, b.fecha_adquisicion, b.fecha_registro
            {tablas}
            {where_sql}
            ORDER BY r.nombre, b.codigo_inventario, b.id_bien
        """

        return ConsultaReporte(
            sql_reporte=sql_reporte,
            parametros=parametros,
        )

    # Solicitudes y reservas

    def _consulta_reservas(self, filtro):
        busqueda = """
            p.dni_persona LIKE %s
            OR CONCAT(per.nombres, ' ', per.apellidos) LIKE %s
            OR r.nombre LIKE %s
        """
        condiciones, parametros = self._construir_filtros_sql_comunes(
            filtro, busqueda, 'p.fecha_solicitud', 'p.estado'
        )
        self._agregar_filtros_sql_de_personas(filtro, condiciones, parametros, incluir_modalidad=False)
        if filtro.tipo_gestion:
            condiciones.append('p.tipo_gestion = %s')
            parametros.append(filtro.tipo_gestion)
        where_sql = self._armar_clausula_where(condiciones)

        tablas = """
            FROM reserva p
            JOIN persona per ON per.dni = p.dni_persona
            JOIN recurso r ON r.id_recurso = p.id_recurso
            JOIN categoria_recurso c ON c.id_categoria = r.id_categoria
        """

        sql_reporte = f"""
            SELECT
                COALESCE(p.id_reserva_principal,p.id_reserva) AS id_reserva, p.tipo_gestion, p.dni_persona,
                CONCAT(per.nombres, ' ', per.apellidos) AS solicitante,
                r.nombre AS recurso, c.nombre AS categoria,
                p.fecha_solicitud, p.fecha_requerida,
                p.estado, p.fecha_limite_vencimiento
            {tablas}
            {where_sql}
            ORDER BY p.fecha_solicitud DESC, p.id_reserva DESC
        """

        return ConsultaReporte(
            sql_reporte=sql_reporte,
            parametros=parametros,
        )

    # Sanciones

    def _consulta_sanciones(self, filtro):
        condiciones, parametros = self._construir_filtros_sql_comunes(
            filtro, BUSQUEDA_PRESTAMO, 's.fecha', 's.estado'
        )
        where_sql = self._armar_clausula_where(condiciones)

        tablas = JOINS_PRESTAMO + """
            JOIN incidencia i ON i.id_detalle = d.id_detalle
            JOIN sancion s ON s.id_incidencia_ref = i.id_incidencia
        """

        sql_reporte = f"""
            SELECT
                s.id_sancion, s.gravedad, s.fecha_fin, s.fecha_regularizacion, s.tipo_regularizacion,
                p.id_prestamo, p.dni_persona,
                CONCAT(per.nombres, ' ', per.apellidos) AS solicitante,
                p.tipo_prestamo, b.codigo_inventario,
                r.nombre AS recurso, c.nombre AS categoria,
                s.fecha, s.motivo, s.descripcion, s.estado,
                s.fecha_levantamiento, s.justificacion_levantamiento
            {tablas}
            {where_sql}
            ORDER BY s.fecha DESC, s.id_sancion DESC
        """

        return ConsultaReporte(
            sql_reporte=sql_reporte,
            parametros=parametros,
        )

    # Daños y pérdidas

    def _consulta_danos_perdidas(self, filtro):
        busqueda = """
            b.codigo_inventario LIKE %s OR r.nombre LIKE %s
            OR h.dni_responsable LIKE %s
            OR CONCAT(reg.nombres, ' ', reg.apellidos) LIKE %s
            OR h.observacion LIKE %s
        """
        condiciones, parametros = self._construir_filtros_sql_comunes(
            filtro, busqueda, 'h.fecha', 'h.estado_nuevo'
        )
        condiciones.append("h.entidad = 'BIEN_MATERIAL'")
        condiciones.append("h.estado_nuevo IN ('DANADO', 'PERDIDO')")
        where_sql = self._armar_clausula_where(condiciones)

        tablas = """
            FROM historial_estado h
            JOIN bien_material b ON b.id_bien = h.id_entidad
            JOIN recurso r ON r.id_recurso = b.id_recurso
            JOIN categoria_recurso c ON c.id_categoria = r.id_categoria
            LEFT JOIN persona reg ON reg.dni = h.dni_responsable
        """

        sql_reporte = f"""
            SELECT
                h.id_historial_estado, h.fecha, b.id_bien,
                b.codigo_inventario, r.nombre AS recurso,
                c.nombre AS categoria, h.estado_nuevo AS tipo_evento,
                b.estado AS estado_actual,
                h.dni_responsable AS dni_registrador,
                CONCAT(reg.nombres, ' ', reg.apellidos) AS registrador,
                h.observacion
            {tablas}
            {where_sql}
            ORDER BY h.fecha DESC, h.id_historial_estado DESC
        """

        return ConsultaReporte(
            sql_reporte=sql_reporte,
            parametros=parametros,
        )

    # Personas

    def _consulta_personas(self, filtro):
        condiciones, parametros = [], []
        if filtro.tipo_persona:
            condiciones.append('personas.tipo_persona = %s')
            parametros.append(filtro.tipo_persona)
        if filtro.estado:
            condiciones.append('personas.estado = %s')
            parametros.append(filtro.estado)
        if filtro.q:
            condiciones.append("""(
                personas.dni LIKE %s
                OR personas.nombres LIKE %s
                OR personas.apellidos LIKE %s
                OR CONCAT(personas.nombres, ' ', personas.apellidos) LIKE %s
                OR personas.correo LIKE %s
            )""")
            parametros.extend([f'%{filtro.q}%'] * 5)
        where_sql = self._armar_clausula_where(condiciones)
        sql_reporte = f"""
            SELECT personas.dni, personas.nombres, personas.apellidos,
                personas.tipo_persona, personas.telefono, personas.correo, personas.estado
            FROM (
                SELECT per.dni, per.nombres, per.apellidos, per.telefono, per.correo, per.estado,
                    CASE
                        WHEN e.dni IS NOT NULL THEN 'ESTUDIANTE'
                        WHEN doc.dni IS NOT NULL THEN 'DOCENTE'
                        WHEN a.dni IS NOT NULL THEN 'ADMINISTRATIVO'
                        ELSE 'SIN_TIPO'
                    END AS tipo_persona
                FROM persona per
                LEFT JOIN estudiante e ON e.dni = per.dni
                LEFT JOIN docente doc ON doc.dni = per.dni
                LEFT JOIN administrativo a ON a.dni = per.dni
            ) personas
            {where_sql}
            ORDER BY personas.apellidos, personas.nombres, personas.dni
        """
        return ConsultaReporte(sql_reporte=sql_reporte, parametros=parametros)

    # Integrantes de préstamos grupales

    def _consultar_integrantes_prestamos(self, filas):
        identificadores = sorted(
            {fila['id_prestamo'] for fila in filas if fila['tipo_prestamo'] == 'GRUPAL'}
        )

        for fila in filas:
            fila['integrantes'] = ''
        if not identificadores:
            return

        marcas = ', '.join(['%s'] * len(identificadores))
        sql = f"""
            SELECT
                pp.id_prestamo, pp.dni_persona,
                CONCAT(p.nombres, ' ', p.apellidos) AS nombre
            FROM participante_prestamo pp
            JOIN persona p ON p.dni = pp.dni_persona
            WHERE pp.id_prestamo IN ({marcas})
            ORDER BY pp.id_prestamo, pp.responsable DESC, pp.id_participante
        """
        integrantes = self.consultar_sql(sql, identificadores)

        por_prestamo = {identificador: [] for identificador in identificadores}
        for persona in integrantes:
            nombre = f'{persona["nombre"]} ({persona["dni_persona"]})'
            por_prestamo[persona['id_prestamo']].append(nombre)

        for fila in filas:
            fila['integrantes'] = '; '.join(por_prestamo.get(fila['id_prestamo'], []))
