from dataclasses import dataclass

from dominio.compartido.validacion import validar_entero, validar_texto, calcular_version_de_registro

CAMPOS_RECURSO = ('nombre', 'id_categoria', 'marca', 'modelo', 'descripcion')


def version_recurso(datos: dict) -> str:
    return calcular_version_de_registro({campo: datos[campo] for campo in ('id_recurso', *CAMPOS_RECURSO)})


def version_categoria(datos: dict) -> str:
    return calcular_version_de_registro({campo: datos[campo] for campo in ('id_categoria', 'nombre', 'descripcion')})


@dataclass(kw_only=True)
class Recurso:
    nombre: str
    id_categoria: int
    marca: str = ''
    modelo: str = ''
    descripcion: str | None = None
    id_recurso: int | None = None

    def __post_init__(self):
        self.id_categoria = validar_entero(self.id_categoria, 'Categoría')
        self.nombre = validar_texto(self.nombre, 'Nombre', 120, True)
        self.marca = validar_texto(self.marca, 'Marca', 80)
        self.modelo = validar_texto(self.modelo, 'Modelo', 80)
        self.descripcion = validar_texto(self.descripcion, 'Descripción', 255) or None
