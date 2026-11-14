from dominio.gestion_control.control import IRepositorioSancion, Sancion
from repositorio.conexion_mysql import MySQLConnection
from repositorio.sanciones_vencimiento_sql import aplicar_sancion_vencimiento


def consultar_sanciones_activas(cursor, dnis):
    """Consulta común para préstamos y reservas, usando la transacción del llamante."""
    dnis = tuple(sorted(set(dnis)))
    if not dnis:
        return False
    marcadores = ','.join(['%s'] * len(dnis))
    cursor.execute(f'''SELECT s.id_sancion FROM sancion s
        JOIN incidencia i ON i.id_incidencia=s.id_incidencia_ref
        JOIN detalle_prestamo d ON d.id_detalle=i.id_detalle
        JOIN prestamo pr ON pr.id_prestamo=d.id_prestamo
        WHERE (pr.dni_persona IN ({marcadores}) OR EXISTS (
            SELECT 1 FROM participante_prestamo pp
            WHERE pp.id_prestamo=pr.id_prestamo AND pp.dni_persona IN ({marcadores})))
        AND s.estado='ACTIVA' FOR UPDATE''', dnis * 2)
    return bool(cursor.fetchall())


class RepositorioSancionSQL(IRepositorioSancion):
    def __init__(self, conexion=None):
        self.conexion = conexion or MySQLConnection()

    def aplicar_sanciones_vencidas(self) -> int:
        with self.conexion.sesion() as cursor:
            cursor.execute('''SELECT DISTINCT pr.id_prestamo FROM prestamo pr
                JOIN detalle_prestamo d ON d.id_prestamo=pr.id_prestamo
                WHERE d.fecha_devolucion IS NULL AND d.fecha_limite_devolucion < UTC_TIMESTAMP()
                AND NOT EXISTS(SELECT 1 FROM incidencia i JOIN sancion s ON s.id_incidencia_ref=i.id_incidencia
                    WHERE i.id_detalle=d.id_detalle AND i.tipo='RETRASO')
                ORDER BY pr.id_prestamo''')
            prestamos = cursor.fetchall()
        aplicadas = 0
        for prestamo in prestamos:
            with self.conexion.sesion(escritura=True) as cursor:
                cursor.execute('SELECT id_prestamo FROM prestamo WHERE id_prestamo=%s FOR UPDATE', (prestamo['id_prestamo'],))
                if cursor.fetchone() is None:
                    continue
                cursor.execute('''SELECT * FROM detalle_prestamo WHERE id_prestamo=%s
                    AND fecha_devolucion IS NULL AND fecha_limite_devolucion < UTC_TIMESTAMP()
                    ORDER BY id_detalle FOR UPDATE''', (prestamo['id_prestamo'],))
                detalles = cursor.fetchall()
                cursor.execute('SELECT UTC_TIMESTAMP() AS ahora')
                ahora = cursor.fetchone()['ahora']
                for detalle in detalles:
                    resultado = aplicar_sancion_vencimiento(cursor, detalle, ahora)
                    if resultado and resultado['creada']:
                        aplicadas += 1
        return aplicadas

    def levantar_sancion_vencimiento(self, id_prestamo, id_detalle, justificacion, dni_encargado) -> None:
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute('SELECT estado FROM persona WHERE dni=%s FOR UPDATE', (dni_encargado,))
            encargado = cursor.fetchone()
            if not encargado or encargado['estado'] != 'ACTIVA':
                raise ValueError('El encargado debe ser una persona activa.')
            cursor.execute('SELECT id_prestamo FROM prestamo WHERE id_prestamo=%s FOR UPDATE', (id_prestamo,))
            prestamo = cursor.fetchone()
            if prestamo is None:
                raise LookupError('No se encontró el préstamo.')
            cursor.execute('''SELECT d.* FROM detalle_prestamo d
                WHERE d.id_detalle=%s AND d.id_prestamo=%s FOR UPDATE''', (id_detalle, id_prestamo))
            detalle = cursor.fetchone()
            if detalle is None:
                raise LookupError('El bien no pertenece a este préstamo.')
            cursor.execute('SELECT UTC_TIMESTAMP() AS ahora')
            ahora = cursor.fetchone()['ahora']
            sancion = aplicar_sancion_vencimiento(cursor, detalle, ahora)
            if sancion is None:
                raise ValueError('Este bien no tiene una sanción por tardanza.')
            modelo = Sancion(id_sancion=sancion['id_sancion'],
                id_incidencia_ref=sancion['id_incidencia_ref'], estado=sancion['estado'])
            modelo.levantar(justificacion, dni_encargado, ahora)
            cursor.execute('''UPDATE sancion SET estado='LEVANTADA',fecha_levantamiento=%s,
                dni_levantamiento=%s,justificacion_levantamiento=%s WHERE id_sancion=%s AND estado='ACTIVA' ''',
                (modelo.fecha_levantamiento, modelo.dni_levantamiento, modelo.justificacion_levantamiento, modelo.id_sancion))
            cursor.execute('''UPDATE incidencia i JOIN sancion s ON s.id_incidencia_ref=i.id_incidencia
                SET i.estado='RESUELTA' WHERE s.id_sancion=%s''', (sancion['id_sancion'],))
            cursor.execute('''INSERT INTO historial_estado
                (entidad,id_entidad,estado_anterior,estado_nuevo,fecha,observacion,dni_responsable)
                VALUES('SANCION',%s,'ACTIVA','LEVANTADA',%s,%s,%s)''',
                (sancion['id_sancion'], ahora, justificacion, dni_encargado))
