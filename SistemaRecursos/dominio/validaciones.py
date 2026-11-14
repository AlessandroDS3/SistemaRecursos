"""Validaciones de valores y versiones de edición compartidas."""
from __future__ import annotations
import json
from dataclasses import asdict
from datetime import date, datetime, timezone
from hashlib import sha256


# Validacion recurso

def texto(valor, campo, limite, obligatorio=False):
    if valor is None:
        valor = ""
    if not isinstance(valor, str):
        raise ValueError(f"{campo}: debe ser texto.")
    valor = valor.strip()
    if (obligatorio and not valor) or len(valor) > limite:
        raise ValueError(
            f'{campo}: {"obligatorio, " if obligatorio else ""}máximo {limite} caracteres.'
        )
    return valor


def entero(valor, campo=None):
    try:
        if isinstance(valor, bool):
            raise ValueError
        numero = int(valor)
        if numero < 1 or str(numero) != str(valor).strip():
            raise ValueError
        return numero
    except (ValueError, TypeError):
        mensaje = f"{campo}: selecciona un identificador válido." if campo else "Selecciona un identificador válido."
        raise ValueError(mensaje) from None


def fecha(valor, campo):
    try:
        if isinstance(valor, datetime):
            valor = valor.date()
        return valor if isinstance(valor, date) else date.fromisoformat(valor)
    except (ValueError, TypeError):
        raise ValueError(f"{campo}: introduce una fecha válida.") from None


def instante_utc(valor, campo):
    """Normaliza instantes a UTC sin zona, como las columnas DATETIME del sistema."""
    if not isinstance(valor, datetime):
        raise ValueError(f"{campo}: introduce una fecha y hora válidas.")
    if valor.tzinfo is not None:
        return valor.astimezone(timezone.utc).replace(tzinfo=None)
    return valor


# Version edicion

class ConflictoEdicion(Exception):
    """El formulario no representa el estado que sigue guardado."""


def huella(datos):
    contenido = json.dumps(datos, ensure_ascii=False, sort_keys=True)
    return sha256(contenido.encode("utf-8")).hexdigest()


def version_persona(persona):
    return huella(asdict(persona))


def version_matriz(roles, permisos):
    asignaciones = sorted(
        (rol.nombre.value, sorted(p.codigo for p in rol.permisos))
        for rol in roles
    )
    return huella([asignaciones, sorted(p.codigo for p in permisos)])


def exigir_version(recibida, actual):
    if recibida != actual:
        raise ConflictoEdicion("El formulario venció o los datos cambiaron. Vuelve a abrirlo antes de guardar.")
