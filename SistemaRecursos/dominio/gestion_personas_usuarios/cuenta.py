"""Reglas de administración de cuentas y protección del último administrador."""

from typing import Protocol
from dominio.compartido.contratos import IRepositorioTransaccional
from dominio.compartido.validacion import texto, version

ESTADOS_CUENTA = ('ACTIVA', 'INACTIVA', 'BLOQUEADA')


def version_cuenta(cuenta: dict) -> str:
    # El último acceso cambia al iniciar sesión, no al editar la cuenta.
    return version(
        {
            campo: cuenta[campo]
            for campo in (
                'id_usuario',
                'dni_persona',
                'nombre_usuario',
                'contrasena_hash',
                'rol',
                'estado_cuenta',
                'estado_persona',
            )
        }
    )


def validar_nombre_usuario(nombre: str) -> str:
    return texto(nombre, 'Nombre de usuario', 50, True)


def validar_clave(clave: str, permitir_vacia: bool = False) -> str:
    if permitir_vacia and clave == '':
        return clave
    if not isinstance(clave, str) or not 12 <= len(clave) <= 256:
        raise ValueError('La contraseña debe tener entre 12 y 256 caracteres.')
    return clave


def proteger_administradores(cuentas: list[dict], actual: dict, nueva: dict, actor: int) -> None:
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
    def consultar_cuenta_para_cambiar_clave(self, identificador: int) -> dict | None: ...
    def consultar_cuenta(self, documento: str) -> dict | None: ...
    def consultar_cuentas_para_actualizar(self) -> list[dict]: ...
    def consultar_estado_persona(self, documento: str) -> str | None: ...
    def registrar_cuenta(self, documento: str, nombre: str, hash_clave: str) -> int: ...
    def actualizar_cuenta(self, identificador: int, datos: dict) -> None: ...
    def buscar_cuentas(self, termino: str) -> list[dict]: ...
