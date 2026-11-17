from dataclasses import dataclass
from typing import Protocol
from dominio.compartido.contratos import IRepositorioTransaccional
from dominio.gestion_recursos.bien_material import BienMaterial
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


class IRepositorioRecurso(IRepositorioTransaccional, Protocol):
    def consultar_recursos(self, filtros: dict, contar_bienes=True) -> list[dict]: ...
    def consultar_disponibilidad(self) -> int: ...
    def consultar_recurso(self, identificador: int, bloquear=False) -> dict | None: ...
    def guardar_recurso(self, recurso: Recurso) -> int: ...
    def eliminar_recurso(self, identificador: int) -> None: ...
    def consultar_relaciones_recurso(self, identificador: int) -> dict: ...
    def consultar_bienes_materiales(self, filtros: dict) -> list[dict]: ...
    def consultar_categoria(self, identificador: int, bloquear=False) -> dict | None: ...
    def consultar_relaciones_categoria(self, identificador: int) -> dict: ...
    def consultar_categorias(self) -> list[dict]: ...
    def guardar_categoria(self, nombre: str, descripcion: str, identificador=None) -> int: ...
    def guardar_bien_material(self, bien: BienMaterial) -> int: ...
    def eliminar_categoria(self, identificador: int) -> None: ...
