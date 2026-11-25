from dominio.compartido.validacion import Conflicto
from dominio.gestion_prestamos.ampliacion_prestamo import ContextoAmpliacion
from repositorio.base_datos.base_sql import RepositorioSQL


class RepositorioAmpliacionPrestamoSQL(RepositorioSQL):
    def consultar_contexto_ampliacion_prestamo(self, prestamo, detalle) -> ContextoAmpliacion:
        cabecera = self.consultar_sql(
            'SELECT * FROM prestamo WHERE id_prestamo=%s FOR UPDATE', (prestamo,), una=True
        )
        contexto: ContextoAmpliacion = dict(
            prestamo=cabecera, detalle=None, politica=None, horario=None
        )
        if cabecera is None:
            return contexto
        fila = self.consultar_sql(
            '''SELECT d.*,b.estado AS estado_bien FROM detalle_prestamo d
            JOIN bien_material b ON b.id_bien=d.id_bien WHERE d.id_prestamo=%s AND d.id_detalle=%s FOR UPDATE''',
            (prestamo, detalle),
            una=True,
        )
        contexto['detalle'] = fila
        if fila is None:
            return contexto
        politica = self.consultar_sql(
            'SELECT * FROM politica_prestamo WHERE id_politica=%s FOR UPDATE',
            (fila['id_politica'],),
            una=True,
        )
        horario = self.consultar_sql(
            'SELECT hora_apertura,hora_cierre,dias_atencion FROM configuracion_general '
            'WHERE id_configuracion=1 FOR UPDATE',
            una=True,
        )
        contexto['politica'] = politica
        contexto['horario'] = horario
        return contexto

    # Solicitudes del usuario (AMP-01)

    def registrar_solicitud_ampliacion(self, prestamo, detalle, solicitante, solicitud, fecha_anterior):
        return self.ejecutar(
            '''INSERT INTO solicitud_ampliacion(id_prestamo,id_detalle,dni_solicitante,cantidad,
            unidad,motivo,fecha_solicitud,fecha_limite_anterior)
            VALUES(%s,%s,%s,%s,%s,%s,UTC_TIMESTAMP(),%s)''',
            (prestamo, detalle, solicitante, solicitud.cantidad, solicitud.unidad,
             solicitud.motivo, fecha_anterior),
        )

    def consultar_solicitud_ampliacion(self, identificador, bloquear=False):
        return self.consultar_sql(
            'SELECT * FROM solicitud_ampliacion WHERE id_solicitud=%s'
            + (' FOR UPDATE' if bloquear else ''),
            (identificador,),
            una=True,
        )

    def consultar_solicitudes_ampliacion(self, estado=None, prestamo=None):
        condiciones, parametros = [], []
        if estado:
            condiciones.append('s.estado=%s')
            parametros.append(estado)
        if prestamo:
            condiciones.append('s.id_prestamo=%s')
            parametros.append(prestamo)
        sql = '''SELECT s.*,b.codigo_inventario,r.nombre AS recurso,d.fecha_limite_devolucion,
            d.fecha_devolucion,d.fecha_regularizacion,
            CONCAT(p.nombres,' ',p.apellidos) AS solicitante,
            CONCAT(pr.nombres,' ',pr.apellidos) AS responsable_resolucion
            FROM solicitud_ampliacion s
            JOIN detalle_prestamo d ON d.id_detalle=s.id_detalle
            JOIN bien_material b ON b.id_bien=d.id_bien
            JOIN recurso r ON r.id_recurso=b.id_recurso
            JOIN persona p ON p.dni=s.dni_solicitante
            LEFT JOIN persona pr ON pr.dni=s.dni_resolucion'''
        if condiciones:
            sql += ' WHERE ' + ' AND '.join(condiciones)
        return self.consultar_sql(
            sql + " ORDER BY s.estado<>'PENDIENTE', s.fecha_solicitud DESC LIMIT 200", parametros
        )

    def resolver_solicitud_ampliacion(self, identificador, estado, actor, nueva, observacion):
        self.ejecutar(
            """UPDATE solicitud_ampliacion SET estado=%s,fecha_resolucion=UTC_TIMESTAMP(),
            dni_resolucion=%s,fecha_limite_nueva=%s,observacion_resolucion=%s
            WHERE id_solicitud=%s AND estado='PENDIENTE'""",
            (estado, actor, nueva, observacion, identificador),
        )
        if self._cursor.rowcount != 1:
            raise Conflicto('La solicitud ya fue resuelta. Recarga la lista.')

    def actualizar_plazo_prestamo(self, detalle, anterior, nueva):
        self.ejecutar(
            '''UPDATE detalle_prestamo SET fecha_limite_devolucion=%s
            WHERE id_detalle=%s AND fecha_limite_devolucion=%s
            AND fecha_devolucion IS NULL AND fecha_regularizacion IS NULL''',
            (nueva, detalle, anterior),
        )
        if self._cursor.rowcount != 1:
            raise Conflicto('El plazo cambió. Recarga el préstamo.')
