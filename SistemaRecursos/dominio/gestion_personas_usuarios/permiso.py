from dataclasses import dataclass


@dataclass(frozen=True)
class Permiso:
    id_permiso: int
    codigo: str
    descripcion: str = ""
