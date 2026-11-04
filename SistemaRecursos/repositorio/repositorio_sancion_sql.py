from dominio.gestion_control.i_repositorio_sancion import IRepositorioSancion
from dominio.gestion_control.sancion import Sancion
from repositorio.conexion_mysql import MySQLConnection
from repositorio.sanciones_vencimiento_sql import aplicar_sancion_vencimiento


class RepositorioSancionSQL(IRepositorioSancion):
    def __init__(self, conexion=None):
        self.conexion = conexion or MySQLConnection()

    def aplicar_sanciones_vencidas(self) -> int:
        with self.conexion.sesion() as cursor:
            cursor.execute('''SELECT DISTINCT pr.id_prestamo FROM prestamo pr
                JOIN detalle_prestamo d ON d.id_prestamo=pr.id_prestamo
                WHERE d.estado_devolucion IS NULL AND d.fecha_limite_devolucion < UTC_TIMESTAMP()
                AND NOT EXISTS(SELECT 1 FROM sancion s WHERE s.id_detalle_vencido_ref=d.id_detalle)
                ORDER BY pr.id_prestamo''')
            prestamos = cursor.fetchall()
        aplicadas = 0
        for prestamo in prestamos:
            with self.conexion.sesion(escritura=True) as cursor:
                cursor.execute('SELECT dni_persona FROM prestamo WHERE id_prestamo=%s FOR UPDATE', (prestamo['id_prestamo'],))
                persona = cursor.fetchone()
                if persona is None:
                    continue
                cursor.execute('''SELECT * FROM detalle_prestamo WHERE id_prestamo=%s
                    AND estado_devolucion IS NULL AND fecha_limite_devolucion < UTC_TIMESTAMP()
                    ORDER BY id_detalle FOR UPDATE''', (prestamo['id_prestamo'],))
                detalles = cursor.fetchall()
                cursor.execute('SELECT UTC_TIMESTAMP() AS ahora')
                ahora = cursor.fetchone()['ahora']
                for detalle in detalles:
                    resultado = aplicar_sancion_vencimiento(cursor, detalle, persona['dni_persona'], ahora)
                    if resultado and resultado['creada']:
                        aplicadas += 1
        return aplicadas

    def levantar_sancion_vencimiento(self, id_prestamo, id_detalle, justificacion, dni_encargado) -> None:
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute('SELECT estado FROM persona WHERE dni=%s FOR UPDATE', (dni_encargado,))
            encargado = cursor.fetchone()
            if not encargado or encargado['estado'] != 'ACTIVA':
                raise ValueError('El encargado debe ser una persona activa.')
            cursor.execute('SELECT dni_persona FROM prestamo WHERE id_prestamo=%s FOR UPDATE', (id_prestamo,))
            prestamo = cursor.fetchone()
            if prestamo is None:
                raise LookupError('No se encontró el préstamo.')
            cursor.execute('''SELECT d.*,dev.fecha AS fecha_devolucion FROM detalle_prestamo d
                LEFT JOIN devolucion dev ON dev.id_detalle_ref=d.id_detalle
                WHERE d.id_detalle=%s AND d.id_prestamo=%s FOR UPDATE''', (id_detalle, id_prestamo))
            detalle = cursor.fetchone()
            if detalle is None:
                raise LookupError('El bien no pertenece a este préstamo.')
            cursor.execute('SELECT UTC_TIMESTAMP() AS ahora')
            ahora = cursor.fetchone()['ahora']
            sancion = aplicar_sancion_vencimiento(cursor, detalle, prestamo['dni_persona'], ahora)
            if sancion is None:
                raise ValueError('Este bien no tiene una sanción por tardanza.')
            modelo = Sancion(dni_persona=prestamo['dni_persona'], id_sancion=sancion['id_sancion'],
                id_detalle_vencido_ref=id_detalle, estado=sancion['estado'])
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
