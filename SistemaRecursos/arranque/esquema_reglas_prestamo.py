"""Actualiza el esquema de las reglas de préstamo y su auditoría."""

from pathlib import Path
import sys

from mysql.connector import Error, ProgrammingError

from repositorio.base_datos.conexion_mysql import MySQLConnection

MIGRACION = Path(__file__).parents[1] / 'sql/migraciones/20261125_reglas_prestamo.sql'


def comprobar_esquema_reglas_prestamo(conexion):
    with conexion.sesion() as cursor:
        cursor.execute('''SELECT d.ampliado,s.fecha_recuperacion_original,h.dni_objetivo,h.datos
            FROM detalle_prestamo d CROSS JOIN sancion s CROSS JOIN historial_estado h LIMIT 0''')
        cursor.execute("""SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE()
            AND TABLE_NAME='historial_estado' AND COLUMN_NAME='entidad' AND COLUMN_TYPE LIKE '%''CUENTA''%'""")
        if cursor.fetchone() is None:
            raise ProgrammingError('Falta la categoría CUENTA en el historial de estados.', errno=1054)


def migrar_esquema_reglas_prestamo(conexion):
    with conexion.sesion(escritura=True) as cursor:
        cursor.execute(MIGRACION.read_text(encoding='utf-8'))
        while cursor.nextset():
            pass
    comprobar_esquema_reglas_prestamo(conexion)


def main():
    try:
        migrar_esquema_reglas_prestamo(MySQLConnection())
    except Error as error:
        print(f'No se pudo actualizar el esquema de reglas de préstamo: {error}', file=sys.stderr)
        return 1
    print('Esquema de reglas de préstamo actualizado.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
