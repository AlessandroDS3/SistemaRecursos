"""Comprobación y migración del esquema de sanciones en la base configurada."""

from pathlib import Path
import sys

from mysql.connector import Error

from repositorio.base_datos.conexion_mysql import MySQLConnection


def comprobar_esquema_sanciones(conexion):
    with conexion.sesion() as cursor:
        cursor.execute(
            """SELECT d.fecha_regularizacion, s.gravedad, s.fecha_revision, c.dias_leve
            FROM detalle_prestamo d CROSS JOIN sancion s
            CROSS JOIN configuracion_general c LIMIT 0"""
        )


def migrar_esquema_sanciones(conexion):
    ruta = Path(__file__).parents[1] / 'sql/migraciones/20261123_sanciones_por_gravedad.sql'
    with conexion.sesion() as cursor:
        cursor.execute(ruta.read_text(encoding='utf-8'))
        while cursor.nextset():
            pass
    comprobar_esquema_sanciones(conexion)


def main():
    conexion = MySQLConnection()
    try:
        migrar_esquema_sanciones(conexion)
    except Error as error:
        print(f'No se pudo actualizar la base {conexion.config["database"]}: {error}', file=sys.stderr)
        return 1
    print(f'Esquema de sanciones actualizado en {conexion.config["database"]}.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
