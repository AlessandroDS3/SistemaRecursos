from __future__ import annotations
from dominio.gestion_recursos.categoria_recurso import CategoriaRecurso
from dominio.gestion_recursos.recurso import Recurso
from dominio.resultados_consulta import RecursoListado
from abc import ABC, abstractmethod


class IRepositorioRecurso(ABC):
    @abstractmethod
    def registrar_recurso(self, recurso) -> Recurso:
        """Guarda un nuevo recurso."""
        raise NotImplementedError

    @abstractmethod
    def registrar_recurso_con_bien(self, recurso, datos_bien) -> Recurso:
        """Guarda un nuevo recurso junto con su primer bien."""
        raise NotImplementedError

    @abstractmethod
    def consultar_recurso(self, id_recurso) -> Recurso | None:
        """Busca un recurso por su ID; devuelve None si no existe."""
        raise NotImplementedError

    @abstractmethod
    def actualizar_recurso(self, recurso) -> Recurso:
        """Actualiza los datos de un recurso."""
        raise NotImplementedError

    @abstractmethod
    def eliminar_recurso(self, id_recurso) -> None:
        """Elimina un recurso."""
        raise NotImplementedError

    @abstractmethod
    def consultar_recursos(self, filtros=None) -> list[RecursoListado]:
        """Lista los recursos según los filtros."""
        raise NotImplementedError

    @abstractmethod
    def consultar_categorias(self) -> list[CategoriaRecurso]:
        """Lista las categorías de recursos."""
        raise NotImplementedError

    @abstractmethod
    def consultar_categoria(self, id_categoria) -> CategoriaRecurso | None:
        """Busca una categoría por su ID; devuelve None si no existe."""
        raise NotImplementedError

    @abstractmethod
    def registrar_categoria(self, categoria) -> CategoriaRecurso:
        """Guarda una nueva categoría."""
        raise NotImplementedError

    @abstractmethod
    def actualizar_categoria(self, categoria) -> CategoriaRecurso:
        """Actualiza los datos de una categoría."""
        raise NotImplementedError

    @abstractmethod
    def eliminar_categoria(self, id_categoria) -> None:
        """Elimina una categoría."""
        raise NotImplementedError
