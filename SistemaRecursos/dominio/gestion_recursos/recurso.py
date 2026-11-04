from dataclasses import dataclass
from dominio.gestion_recursos.validacion_recurso import texto, entero


@dataclass(kw_only=True)
class Recurso:
    nombre: str
    id_categoria_ref: int
    marca: str = ""
    modelo: str = ""
    descripcion: str = ""
    id_recurso: int | None = None

    def __post_init__(self):
        self.nombre = texto(self.nombre, "Nombre del recurso", 120, True)
        self.id_categoria_ref = entero(self.id_categoria_ref, "Categoría")
        self.marca = texto(self.marca, "Marca", 80)
        self.modelo = texto(self.modelo, "Modelo", 80)
        self.descripcion = texto(self.descripcion, "Descripción", 255)

    def clasificar(self, categoria):
        self.id_categoria_ref = entero(categoria.id_categoria, "Categoría")
