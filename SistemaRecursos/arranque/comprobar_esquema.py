"""Verifica la base configurada desde el comando de mantenimiento."""

import sys

from mysql.connector import Error

from arranque.esquema_cierre import comprobar_esquema_cierre
from arranque.esquema_horario import comprobar_esquema_horario
from arranque.esquema_reglas_prestamo import comprobar_esquema_reglas_prestamo
from arranque.esquema_sanciones import comprobar_esquema_sanciones
from repositorio.base_datos.conexion_mysql import MySQLConnection


def main():
    conexion = MySQLConnection()
    for comprobar, paso in (
        (comprobar_esquema_sanciones, 'Sanciones'),
        (comprobar_esquema_cierre, 'Cierre'),
        (comprobar_esquema_horario, 'Horario'),
        (comprobar_esquema_reglas_prestamo, 'ReglasPrestamo'),
    ):
        try:
            comprobar(conexion)
        except Error as error:
            if error.errno in (1054, 1146):
                print(f'Falta el esquema requerido. Revisa la guía y ejecuta .\\migrate.ps1 -Paso {paso}.',
                      file=sys.stderr)
            else:
                print(f'No se pudo comprobar la base configurada: {error}', file=sys.stderr)
            return 1
    print(f'Esquema actualizado en {conexion.config["database"]}.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
