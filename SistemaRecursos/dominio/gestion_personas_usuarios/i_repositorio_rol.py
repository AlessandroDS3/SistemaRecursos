from __future__ import annotations
from dominio.gestion_personas_usuarios.permiso import Permiso
from dominio.gestion_personas_usuarios.rol import Rol
from abc import ABC, abstractmethod


class IRepositorioRol(ABC):
    @abstractmethod
    def registrar_rol(self, rol) -> Rol:
        """Operación administrativa de persistencia; no tiene entrada web en el sistema actual."""
        raise NotImplementedError

    @abstractmethod
    def consultar_rol(self, id_rol) -> Rol | None:
        """Lectura sin escrituras. Devuelve Rol | None; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def consultar_roles(self) -> list[Rol]:
        """Lectura sin escrituras. Devuelve list[Rol]; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def actualizar_rol(self, rol) -> Rol:
        """Operación administrativa de persistencia; no tiene entrada web en el sistema actual."""
        raise NotImplementedError

    @abstractmethod
    def desactivar_rol(self, id_rol) -> None:
        """Operación administrativa de persistencia; no tiene entrada web en el sistema actual."""
        raise NotImplementedError

    @abstractmethod
    def consultar_permisos(self) -> list[Permiso]:
        """Lectura sin escrituras. Devuelve list[Permiso]; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def actualizar_matriz_permisos(self, permisos_por_rol) -> None:
        """Escritura explícita. Devuelve None y propaga errores de validación o integridad."""
        raise NotImplementedError
