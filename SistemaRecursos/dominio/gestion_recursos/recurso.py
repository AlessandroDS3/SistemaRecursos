from dataclasses import dataclass

from dominio.compartido.validacion import entero, texto, version

CAMPOS_RECURSO = ('nombre', 'id_categoria', 'marca', 'modelo', 'descripcion')


def version_recurso(datos: dict) -> str:
    return version({campo: datos[campo] for campo in ('id_recurso', *CAMPOS_RECURSO)})


def version_categoria(datos: dict) -> str:
    return version({campo: datos[campo] for campo in ('id_categoria', 'nombre', 'descripcion')})


@dataclass(kw_only=True)
class Recurso:
    nombre: str
    id_categoria: int
    marca: str = ''
    modelo: str = ''
    descripcion: str | None = None
    id_recurso: int | None = None

    def __post_init__(self):
        self.id_categoria = entero(self.id_categoria, 'Categoría')
        self.nombre = texto(self.nombre, 'Nombre', 120, True)
        self.marca = texto(self.marca, 'Marca', 80)
        self.modelo = texto(self.modelo, 'Modelo', 80)
        self.descripcion = texto(self.descripcion, 'Descripción', 255) or None
