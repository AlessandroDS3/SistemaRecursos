from dataclasses import dataclass


@dataclass(repr=False)
class Credenciales:
    nombre_usuario: str
    contrasena_hash: str
