from dominio.gestion_control.fabrica_politica_prestamo import FabricaPoliticaPrestamo
from dominio.gestion_control.horario_atencion import HorarioAtencion
from dominio.gestion_prestamos.ampliacion_prestamo import (
    AmpliacionPrestamo, ConflictoAmpliacionError, EstadoAmpliacion,
)
from dominio.gestion_prestamos.i_repositorio_ampliacion_prestamo import IRepositorioAmpliacionPrestamo
from repositorio.conexion_mysql import MySQLConnection


class RepositorioAmpliacionPrestamoSQL(IRepositorioAmpliacionPrestamo):
    def __init__(self, conexion=None):
        self.conexion = conexion or MySQLConnection()

    @staticmethod
    def _bloquear_detalle(cursor, id_prestamo, id_detalle):
        cursor.execute('SELECT id_prestamo,dni_persona,estado FROM prestamo WHERE id_prestamo=%s FOR UPDATE', (id_prestamo,))
        prestamo = cursor.fetchone()
        if prestamo is None:
            raise LookupError('No se encontró el préstamo.')
        cursor.execute('''SELECT d.*,b.estado AS estado_bien,b.codigo_inventario
            FROM detalle_prestamo d JOIN bien_material b ON b.id_bien=d.id_bien
            WHERE d.id_detalle=%s AND d.id_prestamo=%s FOR UPDATE''', (id_detalle, id_prestamo))
        detalle = cursor.fetchone()
        if detalle is None:
            raise LookupError('El bien no pertenece a este préstamo.')
        return prestamo, detalle

    @staticmethod
    def _validar_cuenta(cursor, permiso, *, dni=None, id_usuario=None):
        campo, valor = ('u.dni_persona', dni) if dni is not None else ('u.id_usuario', id_usuario)
        cursor.execute('''SELECT u.id_usuario,u.dni_persona FROM usuario_sistema u
            JOIN persona p ON p.dni=u.dni_persona
            WHERE ''' + campo + '''=%s AND u.estado_cuenta='ACTIVA' AND p.estado='ACTIVA'
            AND EXISTS(SELECT 1 FROM rol_permiso rp WHERE rp.rol=u.rol AND rp.permiso=%s)''', (valor, permiso))
        cuenta = cursor.fetchone()
        if cuenta is None:
            raise PermissionError('La cuenta no tiene permiso para esta operación.')
        return cuenta

    @staticmethod
    def _validar_plazo(cursor, ampliacion, detalle):
        if detalle['fecha_devolucion'] is not None or detalle['estado_bien'] != 'PRESTADO':
            raise ConflictoAmpliacionError('Solo se pueden ampliar bienes prestados y pendientes de devolución.')
        cursor.execute('''SELECT p.*,c.hora_apertura,c.hora_cierre FROM politica_prestamo p
            LEFT JOIN configuracion_general c ON c.id_configuracion=1
            WHERE p.id_politica=%s FOR UPDATE''', (detalle['id_politica'],))
        fila = cursor.fetchone()
        if fila is None:
            raise ValueError('No se encontró la política aplicada al bien.')
        politica = FabricaPoliticaPrestamo.construir(fila)
        horario = None
        if politica.unidad_plazo == 'HORAS':
            if fila['hora_apertura'] is None or fila['hora_cierre'] is None:
                raise ValueError('Configura el horario de atención antes de ampliar un préstamo por horas.')
            horario = HorarioAtencion(hora_apertura=fila['hora_apertura'], hora_cierre=fila['hora_cierre'])
        cursor.execute('SELECT UTC_TIMESTAMP() AS ahora')
        ahora = cursor.fetchone()['ahora']
        ampliacion.validar_plazo(detalle['fecha_limite_devolucion'], ahora, politica, horario)
        return ahora

    @staticmethod
    def _historial(cursor, prestamo, ampliacion, observacion, dni_actor):
        cursor.execute('''INSERT INTO historial_estado
            (entidad,id_entidad,estado_anterior,estado_nuevo,fecha,observacion,dni_responsable)
            VALUES('PRESTAMO',%s,%s,%s,UTC_TIMESTAMP(),%s,%s)''',
            (prestamo['id_prestamo'], prestamo['estado'], prestamo['estado'],
             f'Ampliación #{ampliacion.id_ampliacion}: {observacion}', dni_actor))

    def solicitar_ampliacion(self, id_prestamo, ampliacion, dni_responsable):
        with self.conexion.sesion(escritura=True) as cursor:
            prestamo, detalle = self._bloquear_detalle(cursor, id_prestamo, ampliacion.id_detalle)
            if prestamo['dni_persona'] != dni_responsable:
                raise PermissionError('Solo el responsable del préstamo puede solicitar la ampliación.')
            self._validar_cuenta(cursor, 'AMPLIACIONES_SOLICITAR', dni=dni_responsable)
            if ampliacion.estado != EstadoAmpliacion.PENDIENTE:
                raise ValueError('Una solicitud nueva debe estar pendiente.')
            ahora = self._validar_plazo(cursor, ampliacion, detalle)
            cursor.execute("SELECT id_ampliacion FROM ampliacion_prestamo WHERE id_detalle=%s AND estado='PENDIENTE' FOR UPDATE", (ampliacion.id_detalle,))
            if cursor.fetchall():
                raise ConflictoAmpliacionError('Este bien ya tiene una ampliación pendiente.')
            cursor.execute('''INSERT INTO ampliacion_prestamo
                (id_detalle,fecha_solicitud,fecha_limite_anterior,fecha_limite_nueva,motivo,estado)
                VALUES(%s,%s,%s,%s,%s,'PENDIENTE')''',
                (ampliacion.id_detalle, ahora, ampliacion.fecha_limite_anterior,
                 ampliacion.fecha_limite_nueva, ampliacion.motivo))
            ampliacion.id_ampliacion = cursor.lastrowid
            ampliacion.fecha_solicitud = ahora
            self._historial(cursor, prestamo, ampliacion, 'solicitud registrada', dni_responsable)
        return ampliacion

    def aprobar_ampliacion(self, id_prestamo, id_ampliacion, id_usuario, observacion=''):
        return self._resolver(id_prestamo, id_ampliacion, id_usuario, observacion, aprobar=True)

    def rechazar_ampliacion(self, id_prestamo, id_ampliacion, id_usuario, observacion):
        return self._resolver(id_prestamo, id_ampliacion, id_usuario, observacion, aprobar=False)

    def _resolver(self, id_prestamo, id_ampliacion, id_usuario, observacion, aprobar):
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute('SELECT id_detalle FROM ampliacion_prestamo WHERE id_ampliacion=%s', (id_ampliacion,))
            referencia = cursor.fetchone()
            if referencia is None:
                raise LookupError('No se encontró la ampliación.')
            prestamo, detalle = self._bloquear_detalle(cursor, id_prestamo, referencia['id_detalle'])
            cuenta = self._validar_cuenta(cursor, 'PRESTAMOS_GESTIONAR', id_usuario=id_usuario)
            cursor.execute('SELECT * FROM ampliacion_prestamo WHERE id_ampliacion=%s FOR UPDATE', (id_ampliacion,))
            ampliacion = AmpliacionPrestamo(**cursor.fetchone())
            if ampliacion.estado != EstadoAmpliacion.PENDIENTE:
                raise ConflictoAmpliacionError('Esta ampliación ya fue resuelta. Recarga el préstamo.')
            if aprobar:
                ahora = self._validar_plazo(cursor, ampliacion, detalle)
                ampliacion.aprobar(id_usuario, ahora, observacion)
                cursor.execute('''UPDATE detalle_prestamo SET fecha_limite_devolucion=%s
                    WHERE id_detalle=%s AND fecha_devolucion IS NULL AND fecha_limite_devolucion=%s''',
                    (ampliacion.fecha_limite_nueva, ampliacion.id_detalle, ampliacion.fecha_limite_anterior))
                if cursor.rowcount != 1:
                    raise ConflictoAmpliacionError('El detalle cambió mientras se aprobaba la ampliación.')
            else:
                cursor.execute('SELECT UTC_TIMESTAMP() AS ahora')
                ampliacion.rechazar(id_usuario, cursor.fetchone()['ahora'], observacion)
            cursor.execute('''UPDATE ampliacion_prestamo SET estado=%s,fecha_resolucion=%s,
                id_usuario_resolucion=%s,observacion_resolucion=%s WHERE id_ampliacion=%s''',
                (ampliacion.estado.value, ampliacion.fecha_resolucion, ampliacion.id_usuario_resolucion,
                 ampliacion.observacion_resolucion, ampliacion.id_ampliacion))
            self._historial(cursor, prestamo, ampliacion, ampliacion.estado.value.lower(), cuenta['dni_persona'])
        return ampliacion

    def consultar_ampliaciones(self, id_prestamo):
        with self.conexion.sesion() as cursor:
            cursor.execute('''SELECT a.*,b.codigo_inventario,r.nombre AS recurso,
                d.fecha_devolucion,d.fecha_limite_devolucion AS fecha_limite_actual,
                b.estado AS estado_bien,CONCAT(p.nombres,' ',p.apellidos) AS encargado
                FROM ampliacion_prestamo a JOIN detalle_prestamo d ON d.id_detalle=a.id_detalle
                JOIN bien_material b ON b.id_bien=d.id_bien JOIN recurso r ON r.id_recurso=b.id_recurso
                LEFT JOIN usuario_sistema u ON u.id_usuario=a.id_usuario_resolucion
                LEFT JOIN persona p ON p.dni=u.dni_persona
                WHERE d.id_prestamo=%s ORDER BY a.fecha_solicitud DESC,a.id_ampliacion DESC''', (id_prestamo,))
            return cursor.fetchall()
