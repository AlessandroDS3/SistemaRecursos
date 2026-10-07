"""Configuración local; nunca incluir config.ini en Git."""
from configparser import ConfigParser
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent.parent

def load_config(path=None):
    parser = ConfigParser(interpolation=None)
    if not parser.read(path or BASE / 'config.ini', encoding='utf-8') or not parser.has_section('mysql'):
        raise ValueError('Falta config.ini. Ejecuta configurar_mysql.cmd.')
    section = parser['mysql']
    database = section.get('database', 'prestamos_escuela')
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', database):
        raise ValueError('Nombre de base inválido.')
    port = section.getint('port', 3306)
    if not 1 <= port <= 65535:
        raise ValueError('Puerto MySQL inválido.')
    return dict(host=section.get('host', '127.0.0.1'), port=port,
                user=section.get('user', 'root'), password=section.get('password', ''),
                database=database, charset='utf8mb4', connection_timeout=10,
                autocommit=False, sql_mode='STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION')
