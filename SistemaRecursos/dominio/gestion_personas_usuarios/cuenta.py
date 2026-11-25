"""Reglas de administración de cuentas y protección del último administrador."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from hmac import compare_digest
import secrets
import unicodedata
import re
from dominio.compartido.validacion import texto, version

ESTADOS_CUENTA = ('ACTIVA', 'INACTIVA', 'BLOQUEADA')
PREFIJO_ACTIVACION = 'activacion$'
VIGENCIA_ACTIVACION = timedelta(hours=24)


@dataclass(frozen=True)
class CuentaCreada:
    id_usuario: int
    nombre_usuario: str
    codigo_activacion: str = field(repr=False)


def generar_activacion(ahora: datetime) -> tuple[str, str]:
    codigo = secrets.token_urlsafe(32)
    vence = int((ahora.replace(tzinfo=timezone.utc) + VIGENCIA_ACTIVACION).timestamp())
    return codigo, f'{PREFIJO_ACTIVACION}{vence}${sha256(codigo.encode()).hexdigest()}'


def activacion_valida(registro: str, codigo: str, ahora: datetime) -> bool:
    if not registro.startswith(PREFIJO_ACTIVACION) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', codigo):
        return False
    _, _, resto = registro.partition('$')
    vence, _, huella = resto.partition('$')
    return vence.isascii() and vence.isdecimal() and ahora.replace(tzinfo=timezone.utc).timestamp() < int(vence) and compare_digest(
        huella, sha256(codigo.encode()).hexdigest(),
    )


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


def validar_clave(clave: str) -> str:
    if not isinstance(clave, str) or not 12 <= len(clave) <= 256:
        raise ValueError('La contraseña debe tener entre 12 y 256 caracteres.')
    return clave


def proteger_administradores(cuentas: list[dict], actual: dict, nueva: dict, actor: int) -> None:
    if actual['id_usuario'] == actor and nueva['estado_cuenta'] != 'ACTIVA':
        raise ValueError('No puedes desactivar tu propia cuenta.')

    def activa(c):
        return (c['rol'] == 'ADMINISTRADOR' and c['estado_cuenta'] == c['estado_persona'] == 'ACTIVA'
                and not c.get('debe_cambiar_clave', False))

    if (
        activa(actual)
        and not activa(nueva)
        and not any(activa(c) and c['id_usuario'] != actual['id_usuario'] for c in cuentas)
    ):
        raise ValueError('Debe conservarse al menos una cuenta administradora activa.')
