from __future__ import annotations
from dominio.gestion_recursos.categoria_recurso import CategoriaRecurso
from dominio.gestion_recursos.recurso import Recurso
from dominio.resultados_consulta import RecursoListado
from abc import ABC, abstractmethod


class IRepositorioRecurso(ABC):
    @abstractmethod
    def registrar_recurso(self, recurso) -> Recurso:
        """Escritura explícita. Devuelve Recurso y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def registrar_recurso_con_bien(self, recurso, datos_bien) -> Recurso:
        """Escritura explícita. Devuelve Recurso y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def consultar_recurso(self, id_recurso) -> Recurso | None:
        """Lectura sin escrituras. Devuelve Recurso | None; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def actualizar_recurso(self, recurso) -> Recurso:
        """Escritura explícita. Devuelve Recurso y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def eliminar_recurso(self, id_recurso) -> None:
        """Escritura explícita. Devuelve None y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def consultar_recursos(self, filtros=None) -> list[RecursoListado]:
        """Lectura sin escrituras. Devuelve list[RecursoListado]; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def consultar_categorias(self) -> list[CategoriaRecurso]:
        """Lectura sin escrituras. Devuelve list[CategoriaRecurso]; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def consultar_categoria(self, id_categoria) -> CategoriaRecurso | None:
        """Lectura sin escrituras. Devuelve CategoriaRecurso | None; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def registrar_categoria(self, categoria) -> CategoriaRecurso:
        """Escritura explícita. Devuelve CategoriaRecurso y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def actualizar_categoria(self, categoria) -> CategoriaRecurso:
        """Escritura explícita. Devuelve CategoriaRecurso y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def eliminar_categoria(self, id_categoria) -> None:
        """Escritura explícita. Devuelve None y propaga errores de validación o integridad."""
        raise NotImplementedError
