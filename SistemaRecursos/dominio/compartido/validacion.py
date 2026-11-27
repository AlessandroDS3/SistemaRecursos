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


def validar_texto(valor, nombre, maximo, obligatorio=False):
    valor = '' if valor is None else valor
    if not isinstance(valor, str):
        raise ValueError(f'{nombre}: debe ser texto.')
    valor = valor.strip()
    if len(valor) > maximo or (obligatorio and not valor):
        raise ValueError(
            f'{nombre}: {"obligatorio; " if obligatorio else ""}máximo {maximo} caracteres.'
        )
    return valor


def validar_entero(valor, nombre='Identificador', minimo=1, maximo=2147483647):
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

def validar_dni(valor):
    if not isinstance(valor, str) or not re.fullmatch(r'\d{8}', valor.strip(), flags=re.ASCII):
        raise ValueError('El DNI debe tener ocho dígitos.')
    return valor.strip()



def normalizar_fecha_hora_utc(valor):
    try:
        fecha = valor if isinstance(valor, datetime) else datetime.fromisoformat(valor)
        return fecha.astimezone(timezone.utc).replace(tzinfo=None) if fecha.tzinfo else fecha
    except (ValueError, TypeError, OverflowError):
        raise ValueError('Introduce una fecha y hora válida.') from None


def convertir_fecha_local_de_lima_a_utc(valor):
    try:
        fecha = datetime.fromisoformat(valor)
        if fecha.tzinfo is not None:
            raise ValueError
        return fecha.replace(tzinfo=LIMA).astimezone(timezone.utc).replace(tzinfo=None)
    except OverflowError:
        raise ValueError('La fecha y hora local de Lima está fuera de rango.') from None
    except (ValueError, TypeError):
        raise ValueError('Indica una fecha y hora local de Lima, sin zona horaria.') from None


def validar_lista_de_ids_de_bienes(valores):
    if not isinstance(valores, (list, tuple)) or not 1 <= len(valores) <= 100:
        raise ValueError('Selecciona los bienes.')
    numeros = [validar_entero(v) for v in valores]
    if len(set(numeros)) != len(numeros):
        raise ValueError('No repitas el mismo bien.')
    return numeros


def calcular_version_de_registro(datos):
    return sha256(
        json.dumps(datos, sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()


def exigir_version_vigente(recibida, actual):
    if recibida != actual:
        raise Conflicto('Los datos cambiaron. Recarga el formulario antes de guardar.')
