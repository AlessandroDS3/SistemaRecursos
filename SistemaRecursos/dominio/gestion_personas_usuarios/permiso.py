from dataclasses import dataclass


@dataclass(frozen=True)
class Permiso:
    id_permiso: int
    codigo: str
    descripcion: str = ""

    def __post_init__(self):
        if self.descripcion is None:
            object.__setattr__(self, "descripcion", "")
