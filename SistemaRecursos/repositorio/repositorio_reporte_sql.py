from dominio.gestion_control.reportes import IRepositorioReporte, ResultadoReportePrestamos
from repositorio.conexion_mysql import MySQLConnection
from repositorio.repositorio_prestamo_sql import ORIGEN_PRESTAMOS_CON_ESTADO


POR_PAGINA = 50
TIPO_PERSONA = """CASE WHEN e.dni IS NOT NULL THEN 'ESTUDIANTE'
                       WHEN doc.dni IS NOT NULL THEN 'DOCENTE'
                       WHEN adm.dni IS NOT NULL THEN 'ADMINISTRATIVO' END"""
ORIGEN_REPORTE = f"""
    FROM {ORIGEN_PRESTAMOS_CON_ESTADO} pr
    JOIN detalle_prestamo d ON d.id_prestamo=pr.id_prestamo
    JOIN persona p ON p.dni=pr.dni_persona
    LEFT JOIN estudiante e ON e.dni=p.dni
    LEFT JOIN docente doc ON doc.dni=p.dni
    LEFT JOIN administrativo adm ON adm.dni=p.dni
    JOIN bien_material b ON b.id_bien=d.id_bien
    JOIN recurso r ON r.id_recurso=b.id_recurso
"""


class RepositorioReporteSQL(IRepositorioReporte):
    def __init__(self, conexion=None):
        self.conexion = conexion or MySQLConnection()

    @staticmethod
    def _condiciones(filtros):
        condiciones, valores = [], []
        for campo, condicion in (
            ('desde_utc', 'pr.fecha_entrega >= %s'),
            ('hasta_utc', 'pr.fecha_entrega < %s'),
            ('estado', 'pr.estado = %s'),
            ('modalidad', 'pr.tipo_prestamo = %s'),
            ('tipo_persona', TIPO_PERSONA + ' = %s'),
        ):
            if filtros.get(campo):
                condiciones.append(condicion)
                valores.append(filtros[campo])
        if filtros['q']:
            condiciones.append("""(p.dni LIKE %s OR CONCAT(p.nombres,' ',p.apellidos) LIKE %s
                OR b.codigo_inventario LIKE %s OR r.nombre LIKE %s OR EXISTS (
                    SELECT 1 FROM participante_prestamo pp
                    JOIN persona integrante ON integrante.dni=pp.dni_persona
                    WHERE pp.id_prestamo=pr.id_prestamo AND
                        (integrante.dni LIKE %s OR CONCAT(integrante.nombres,' ',integrante.apellidos) LIKE %s)
                ))""")
            valores.extend(['%' + filtros['q'] + '%'] * 6)
        return (' WHERE ' + ' AND '.join(condiciones) if condiciones else ''), tuple(valores)

    def consultar_prestamos(self, filtros, paginar=True) -> ResultadoReportePrestamos:
        where, valores = self._condiciones(filtros)
        with self.conexion.sesion() as cursor:
            cursor.execute("""SELECT COUNT(DISTINCT pr.id_prestamo) AS prestamos, COUNT(*) AS bienes,
                SUM(d.fecha_devolucion IS NOT NULL) AS devueltos,
                SUM(d.fecha_devolucion IS NULL) AS pendientes,
                SUM(d.fecha_devolucion IS NULL AND d.fecha_limite_devolucion < UTC_TIMESTAMP()) AS vencidos
                """ + ORIGEN_REPORTE + where, valores)
            resumen = {campo: int(valor or 0) for campo, valor in cursor.fetchone().items()}
            paginas = max(1, (resumen['bienes'] + POR_PAGINA - 1) // POR_PAGINA)
            pagina = min(filtros['pagina'], paginas)
            consulta = f"""SELECT pr.id_prestamo,pr.tipo_prestamo,pr.estado,pr.dni_persona,
                CONCAT(p.nombres,' ',p.apellidos) AS solicitante,{TIPO_PERSONA} AS tipo_persona,
                d.id_detalle,b.codigo_inventario,r.nombre AS recurso,pr.fecha_entrega,
                d.fecha_limite_devolucion,d.fecha_devolucion,d.condicion_devolucion,
                CASE WHEN d.fecha_devolucion IS NOT NULL THEN 'DEVUELTO'
                     WHEN d.fecha_limite_devolucion < UTC_TIMESTAMP() THEN 'VENCIDO'
                     ELSE 'PENDIENTE' END AS situacion
                """ + ORIGEN_REPORTE + where + ' ORDER BY pr.fecha_entrega DESC,pr.id_prestamo DESC,d.id_detalle'
            parametros = valores
            if paginar:
                consulta += ' LIMIT %s OFFSET %s'
                parametros += (POR_PAGINA, (pagina - 1) * POR_PAGINA)
            cursor.execute(consulta, parametros)
            filas = cursor.fetchall()
            self._cargar_integrantes(cursor, filas)
        return dict(filas=filas, resumen=resumen, pagina=pagina, paginas=paginas)

    @staticmethod
    def _cargar_integrantes(cursor, filas):
        # Se consultan aparte para que un grupo no multiplique los bienes del reporte.
        ids = sorted({fila['id_prestamo'] for fila in filas if fila['tipo_prestamo'] == 'GRUPAL'})
        integrantes = {identificador: [] for identificador in ids}
        for inicio in range(0, len(ids), 1000):
            lote = ids[inicio:inicio + 1000]
            marcadores = ','.join(['%s'] * len(lote))
            cursor.execute("""SELECT pp.id_prestamo,p.dni,CONCAT(p.nombres,' ',p.apellidos) AS nombre,
                pp.responsable FROM participante_prestamo pp JOIN persona p ON p.dni=pp.dni_persona
                WHERE pp.id_prestamo IN (""" + marcadores + ') ORDER BY pp.responsable DESC,p.apellidos,p.nombres,p.dni', tuple(lote))
            for persona in cursor.fetchall():
                integrantes[persona['id_prestamo']].append(dict(
                    dni=persona['dni'], nombre=persona['nombre'], responsable=bool(persona['responsable'])))
        for fila in filas:
            fila['integrantes'] = integrantes.get(fila['id_prestamo'], [])
