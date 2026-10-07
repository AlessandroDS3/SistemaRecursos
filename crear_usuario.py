"""Alta local de cuentas. No hay contraseñas predeterminadas."""
import argparse
from getpass import getpass
from pathlib import Path
import re
import mysql.connector
from app.auth import UsuarioRepository
from app.config import load_config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path)
    args = parser.parse_args()
    repository = UsuarioRepository(load_config(args.config))
    repository.initialize()
    username = input('Nombre de usuario (letras, números, punto, guion o guion bajo): ').strip()
    if not re.fullmatch(r'[A-Za-z0-9._-]{3,80}', username):
        raise ValueError('El usuario debe tener entre 3 y 80 caracteres válidos.')
    password = getpass('Contraseña (mínimo 10 caracteres): ')
    if not 10 <= len(password) <= 128:
        raise ValueError('La contraseña debe tener entre 10 y 128 caracteres.')
    if password != getpass('Repite la contraseña: '):
        raise ValueError('Las contraseñas no coinciden.')
    try:
        repository.crear_usuario(username, password)
    except mysql.connector.IntegrityError as exc:
        if exc.errno == 1062:
            raise ValueError('Ese usuario ya existe.') from None
        raise
    print('Usuario creado. Ya puedes iniciar sesión en la página.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, mysql.connector.Error) as exc:
        raise SystemExit(f'No se pudo crear el usuario: {exc}') from None
