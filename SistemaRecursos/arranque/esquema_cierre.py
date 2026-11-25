"""Comprobación y migración del esquema de cierre de pendientes en la base configurada."""

from pathlib import Path
import sys

from mysql.connector import Error

from repositorio.base_datos.conexion_mysql import MySQLConnection

MIGRACION = Path(__file__).parents[1] / 'sql/migraciones/20261124_cierre_pendientes.sql'


def comprobar_esquema_cierre(conexion):
    """Falla con 1054 o 1146 si la base no tiene las columnas o tablas del cierre."""
    with conexion.sesion() as cursor:
        cursor.execute(
            """SELECT b.identificador_sistema, b.fecha_registro, m.id_mantenimiento,
            s.id_solicitud, u.id_sesion, e.ultima_ejecucion_correcta
            FROM bien_material b CROSS JOIN mantenimiento_bien m
            CROSS JOIN solicitud_ampliacion s CROSS JOIN sesion_usuario u
            CROSS JOIN estado_procesador e LIMIT 0"""
        )


def migrar_esquema_cierre(conexion):
    with conexion.sesion(escritura=True) as cursor:
        cursor.execute(MIGRACION.read_text(encoding='utf-8'))
        while cursor.nextset():
            pass
    comprobar_esquema_cierre(conexion)


def main():
    conexion = MySQLConnection()
    try:
        migrar_esquema_cierre(conexion)
    except Error as error:
        print(f'No se pudo actualizar la base {conexion.config["database"]}: {error}', file=sys.stderr)
        return 1
    print(f'Esquema de cierre de pendientes actualizado en {conexion.config["database"]}.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
