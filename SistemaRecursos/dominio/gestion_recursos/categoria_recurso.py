from dataclasses import dataclass
from dominio.gestion_recursos.validacion_recurso import texto


@dataclass(kw_only=True)
class CategoriaRecurso:
    nombre: str
    descripcion: str = ""
    id_categoria: int | None = None

    def __post_init__(self):
        self.nombre = texto(self.nombre, "Nombre de categoría", 80, True)
        self.descripcion = texto(self.descripcion, "Descripción", 255)
