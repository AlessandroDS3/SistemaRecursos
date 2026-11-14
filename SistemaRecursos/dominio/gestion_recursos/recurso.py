from dataclasses import dataclass
from typing import Protocol
from dominio.compartido.contratos import IRepositorioTransaccional
from dominio.gestion_recursos.bien_material import BienMaterial
from dominio.compartido.validacion import entero, texto


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
    def listar(self, filtros: dict) -> list[dict]: ...
    def consultar(self, identificador: int) -> dict | None: ...
    def guardar(self, recurso: Recurso): ...
    def eliminar(self, identificador: int): ...
    def categorias(self) -> list[dict]: ...
    def guardar_categoria(self, nombre: str, descripcion: str, identificador=None): ...
    def guardar_bien(self, bien: BienMaterial): ...
    def eliminar_categoria(self, identificador: int): ...
