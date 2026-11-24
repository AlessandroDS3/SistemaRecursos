"""Crea desde la terminal la primera cuenta de una base recién instalada."""

from argparse import ArgumentParser
import os
import sys

from mysql.connector import Error as ErrorMySQL

from repositorio.base_datos.conexion_mysql import MySQLConnection
from repositorio.personas_usuarios.repositorio_cuenta_sql import RepositorioCuentaSQL
from servicios.personas_usuarios.servicio_cuenta import ServicioAplicacionCuenta


def main(argv=None):
    parser = ArgumentParser(description='Crea la primera cuenta administradora del sistema.')
    for campo in ('dni', 'nombres', 'apellidos', 'correo', 'codigo-empleado', 'area', 'usuario'):
        parser.add_argument('--' + campo, required=True)
    datos = vars(parser.parse_args(argv))
    if not os.getenv('DB_NAME', '').strip():
        parser.error('Define DB_NAME con el nombre de la base que quieres inicializar.')

    nombre = datos.pop('usuario')
    try:
        servicio = ServicioAplicacionCuenta(RepositorioCuentaSQL(MySQLConnection()))
        cuenta = servicio.registrar_primer_administrador(datos, nombre)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    except ErrorMySQL:
        print('Revisa la conexión a MySQL y que la base tenga el esquema instalado.', file=sys.stderr)
        return 1

    print(f'Cuenta administradora creada: {cuenta.nombre_usuario}')
    print(f'Contraseña temporal: {cuenta.clave_temporal}')
    print('El sistema pedirá cambiarla al iniciar sesión.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
