"""Actualiza los días de atención de la base configurada."""

import sys

from mysql.connector import Error

from repositorio.base_datos.conexion_mysql import MySQLConnection


def comprobar_esquema_horario(conexion):
    with conexion.sesion() as cursor:
        cursor.execute('SELECT dias_atencion FROM configuracion_general LIMIT 0')


def migrar_esquema_horario(conexion):
    with conexion.sesion(escritura=True) as cursor:
        cursor.execute('''SELECT 1 FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='configuracion_general'
            AND COLUMN_NAME='dias_atencion' ''')
        if cursor.fetchone() is None:
            cursor.execute('''ALTER TABLE configuracion_general
                ADD dias_atencion TINYINT UNSIGNED NOT NULL DEFAULT 31
                CHECK (dias_atencion BETWEEN 1 AND 127) AFTER hora_cierre''')


def main():
    conexion = MySQLConnection()
    try:
        migrar_esquema_horario(conexion)
    except Error as error:
        print(f'No se pudo actualizar el horario de atención: {error}', file=sys.stderr)
        return 1
    print('Días de atención disponibles en Políticas de préstamo.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
