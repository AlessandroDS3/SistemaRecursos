"""Asistente local: solicita credenciales sin mostrarlas en pantalla."""
from configparser import ConfigParser
from getpass import getpass
from pathlib import Path
import argparse
import re
import mysql.connector
from app.repository import RecursoMySQLRepository


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=Path(__file__).resolve().parent / 'config.ini')
    args = parser.parse_args()
    if args.config.exists():
        raise SystemExit('Ese archivo ya existe. Edítalo o usa --config con un archivo nuevo.')
    host = input('Host [127.0.0.1]: ').strip() or '127.0.0.1'
    port = int(input('Puerto [3306]: ').strip() or '3306')
    user = input('Usuario [root]: ').strip() or 'root'
    password = getpass('Contraseña de MySQL (no se muestra): ')
    database = input('Base de datos [prestamos_escuela]: ').strip() or 'prestamos_escuela'
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', database):
        raise ValueError('Nombre de base inválido.')
    config = dict(host=host, port=port, user=user, password=password, connection_timeout=10)
    try:
        conn = mysql.connector.connect(**config, database=database)
    except mysql.connector.Error as exc:
        if exc.errno != 1049:
            raise
        with mysql.connector.connect(**config) as admin, admin.cursor() as cursor:
            cursor.execute(f'CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
    else:
        conn.close()
    RecursoMySQLRepository({**config, 'database': database, 'charset': 'utf8mb4',
                           'sql_mode': 'STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION'}).initialize()
    settings = ConfigParser(interpolation=None)
    settings['mysql'] = dict(host=host, port=str(port), user=user, password=password, database=database)
    with args.config.open('x', encoding='utf-8') as handle:
        settings.write(handle)
    print('Conexión verificada y configuración guardada. Ya puedes abrir iniciar.cmd.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, mysql.connector.Error) as exc:
        raise SystemExit(f'No se pudo configurar MySQL: {exc}') from None
