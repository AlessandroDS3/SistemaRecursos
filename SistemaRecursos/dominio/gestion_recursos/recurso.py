from dataclasses import dataclass
from dominio.gestion_recursos.validacion_recurso import texto, entero


@dataclass(kw_only=True)
class Recurso:
    nombre: str
    id_categoria: int
    marca: str = ""
    modelo: str = ""
    descripcion: str | None = None
    id_recurso: int | None = None

    def __post_init__(self):
        self.nombre = texto(self.nombre, "Nombre del recurso", 120, True)
        self.id_categoria = entero(self.id_categoria, "Categoría")
        self.marca = texto(self.marca, "Marca", 80)
        self.modelo = texto(self.modelo, "Modelo", 80)
        self.descripcion = texto(self.descripcion, "Descripción", 255) or None

    def clasificar(self, categoria):
        self.id_categoria = entero(categoria.id_categoria, "Categoría")
