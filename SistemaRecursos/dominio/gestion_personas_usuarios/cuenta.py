"""Reglas de administración de cuentas y protección del último administrador."""

from dataclasses import dataclass, field
import secrets
import string
from typing import Protocol
import unicodedata
import re
from dominio.compartido.contratos import IRepositorioTransaccional
from dominio.compartido.validacion import texto, version

ESTADOS_CUENTA = ('ACTIVA', 'INACTIVA', 'BLOQUEADA')


@dataclass(frozen=True)
class CuentaCreada:
    id_usuario: int
    nombre_usuario: str
    clave_temporal: str = field(repr=False)


def generar_clave_temporal() -> str:
    grupos = (string.ascii_lowercase, string.ascii_uppercase, string.digits, '!@#$%*+-_')
    alfabeto = ''.join(grupos)
    while True:
        clave = ''.join(secrets.choice(alfabeto) for _ in range(20))
        if all(any(caracter in grupo for caracter in clave) for grupo in grupos):
            return clave


def base_nombre_usuario(persona: dict, dominios: tuple[str, ...]) -> str:
    correo = (persona.get('correo') or '').strip().casefold()
    local, separador, dominio = correo.partition('@')
    if separador and dominio in dominios:
        local = unicodedata.normalize('NFKD', local).encode('ascii', 'ignore').decode()
        base = re.sub(r'[^a-z0-9._-]', '_', local).strip('._-')[:50]
        if base:
            return base
    if persona.get('cui'):
        return persona['cui']
    raise ValueError('Registra un correo institucional o introduce un nombre de usuario.')


def nombre_usuario_disponible(base: str, ocupados: list[str]) -> str:
    usados = {
        ''.join(
            c
            for c in unicodedata.normalize('NFKD', nombre.casefold())
            if not unicodedata.combining(c)
        )
        for nombre in ocupados
    }
    if base.casefold() not in usados:
        return base
    for numero in range(2, 100000):
        sufijo = str(numero)
        candidato = base[: 50 - len(sufijo)] + sufijo
        if candidato.casefold() not in usados:
            return candidato
    raise ValueError('No se pudo proponer un usuario disponible. Introduce otro nombre.')


def version_cuenta(cuenta: dict) -> str:
    # El último acceso cambia al iniciar sesión, no al editar la cuenta.
    return version(
        {
            'debe_cambiar_clave': bool(cuenta.get('debe_cambiar_clave', False)),
            **{
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
            },
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
    def consultar_persona_para_cuenta(self, documento: str, bloquear=False) -> dict | None: ...
    def consultar_nombres_usuario(self, prefijo: str) -> list[str]: ...
    def consultar_id_por_nombre_usuario(self, nombre: str) -> int | None: ...
    def consultar_cuenta_para_cambiar_clave(self, identificador: int) -> dict | None: ...
    def consultar_cuenta(self, documento: str) -> dict | None: ...
    def consultar_cuentas_para_actualizar(self) -> list[dict]: ...
    def registrar_cuenta(self, documento: str, nombre: str, hash_clave: str) -> int: ...
    def actualizar_cuenta(self, identificador: int, datos: dict) -> None: ...
    def buscar_cuentas(self, termino: str) -> list[dict]: ...
