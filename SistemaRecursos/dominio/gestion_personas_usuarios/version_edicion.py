from dataclasses import asdict
from hashlib import sha256
import json


class ConflictoEdicion(Exception):
    """El formulario no representa el estado que sigue guardado."""


def huella(datos):
    contenido = json.dumps(datos, ensure_ascii=False, sort_keys=True)
    return sha256(contenido.encode("utf-8")).hexdigest()


def version_persona(persona):
    return huella(asdict(persona))


def version_matriz(roles, permisos):
    asignaciones = sorted(
        (rol.id_rol, sorted(p.id_permiso for p in rol.permisos))
        for rol in roles if rol.activo
    )
    return huella([asignaciones, sorted(p.id_permiso for p in permisos)])


def exigir_version(recibida, actual):
    if recibida != actual:
        raise ConflictoEdicion("El formulario venció o los datos cambiaron. Vuelve a abrirlo antes de guardar.")
