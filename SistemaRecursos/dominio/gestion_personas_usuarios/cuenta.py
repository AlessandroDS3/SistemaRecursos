"""Reglas de administración de cuentas y protección del último administrador."""

from typing import Protocol
from dominio.compartido.contratos import IRepositorioTransaccional
from dominio.compartido.validacion import texto


def validar_credenciales_nuevas(nombre, clave, permitir_clave_vacia=False):
    nombre = texto(nombre, 'Nombre de usuario', 50, True)
    if not (permitir_clave_vacia and clave == ''):
        if not isinstance(clave, str) or not 12 <= len(clave) <= 256:
            raise ValueError('La contraseña debe tener entre 12 y 256 caracteres.')
    return nombre


def proteger_administradores(cuentas, actual, nueva, actor):
    if actual['id_usuario'] == actor and nueva['estado_cuenta'] != 'ACTIVA':
        raise ValueError('No puedes desactivar tu propia cuenta.')

    def activa(c):
        return c['rol'] == 'ADMINISTRADOR' and c['estado_cuenta'] == c['estado_persona'] == 'ACTIVA'

    if (
        activa(actual)
        and not activa(nueva)
        and not any(activa(c) and c['id_usuario'] != actual['id_usuario'] for c in cuentas)
    ):
        raise ValueError('Debe conservarse al menos una cuenta administradora activa.')


class IRepositorioCuenta(IRepositorioTransaccional, Protocol):
    def consultar(self, documento: str) -> dict | None: ...
    def cargar_cuentas(self) -> list[dict]: ...
    def estado_persona(self, documento: str) -> str | None: ...
    def guardar(self, documento: str, nombre: str, hash_clave: str): ...
    def actualizar(self, identificador: int, datos: dict): ...
    def buscar(self, termino: str) -> list[dict]: ...
