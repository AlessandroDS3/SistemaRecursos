"""Validación de valores; no conoce formularios, sesiones ni bases de datos."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import re

LIMA = timezone(timedelta(hours=-5))


class Conflicto(ValueError):
    """La operación contradice el estado vigente o una edición concurrente."""


class NoEncontrado(LookupError):
    """No existe el registro solicitado."""


def texto(valor, nombre, maximo, obligatorio=False):
    valor = '' if valor is None else valor
    if not isinstance(valor, str):
        raise ValueError(f'{nombre}: debe ser texto.')
    valor = valor.strip()
    if len(valor) > maximo or (obligatorio and not valor):
        raise ValueError(
            f'{nombre}: {"obligatorio; " if obligatorio else ""}máximo {maximo} caracteres.'
        )
    return valor


def entero(valor, nombre='Identificador', minimo=1, maximo=2147483647):
    try:
        numero = int(valor)
        if (
            isinstance(valor, bool)
            or str(numero) != str(valor).strip()
            or not minimo <= numero <= maximo
        ):
            raise ValueError
        return numero
    except (ValueError, TypeError, OverflowError):
        raise ValueError(f'{nombre}: introduce un entero entre {minimo} y {maximo}.') from None

def dni(valor):
    if not isinstance(valor, str) or not re.fullmatch(r'\d{8}', valor.strip(), flags=re.ASCII):
        raise ValueError('El DNI debe tener ocho dígitos.')
    return valor.strip()



def instante(valor):
    try:
        fecha = valor if isinstance(valor, datetime) else datetime.fromisoformat(valor)
        return fecha.astimezone(timezone.utc).replace(tzinfo=None) if fecha.tzinfo else fecha
    except (ValueError, TypeError, OverflowError):
        raise ValueError('Introduce una fecha y hora válida.') from None


def fecha_local(valor):
    try:
        fecha = datetime.fromisoformat(valor)
        if fecha.tzinfo is not None:
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError('Indica una fecha y hora local de Lima, sin zona horaria.') from None
    return fecha.replace(tzinfo=LIMA).astimezone(timezone.utc).replace(tzinfo=None)


def ids(valores):
    if not isinstance(valores, (list, tuple)) or not 1 <= len(valores) <= 100:
        raise ValueError('Selecciona entre uno y cien bienes.')
    numeros = [entero(v) for v in valores]
    if len(set(numeros)) != len(numeros):
        raise ValueError('No repitas el mismo bien.')
    return numeros


def version(datos):
    return sha256(
        json.dumps(datos, sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()


def comprobar_version(recibida, actual):
    if recibida != actual:
        raise Conflicto('Los datos cambiaron. Recarga el formulario antes de guardar.')
