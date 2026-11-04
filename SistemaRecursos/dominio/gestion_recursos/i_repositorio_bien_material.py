from __future__ import annotations
from dominio.gestion_recursos.bien_material import BienMaterial
from dominio.gestion_recursos.registro_fuera_servicio import RegistroFueraServicio
from dominio.resultados_consulta import BienDisponible, BienListado, ResultadoBienes
from typing import Any
from abc import ABC, abstractmethod


class IRepositorioBienMaterial(ABC):
    @abstractmethod
    def registrar_bien_material(self, bien_material) -> BienMaterial:
        """Escritura explícita. Devuelve BienMaterial y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def existen_por_recurso(self, id_recurso) -> bool:
        """Escritura explícita. Devuelve bool y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def consultar_bien_material(self, id_bien) -> BienMaterial | None:
        """Lectura sin escrituras. Devuelve BienMaterial | None; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def actualizar_bien_material(self, bien_material) -> BienMaterial:
        """Escritura explícita. Devuelve BienMaterial y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def eliminar_bien_material(self, id_bien) -> None:
        """Escritura explícita. Devuelve None y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def contar_disponibles(self) -> int:
        """Escritura explícita. Devuelve int y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def consultar_bienes_por_recurso(self, id_recurso=None) -> list[BienListado]:
        """Lectura sin escrituras. Devuelve list[BienListado]; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def consultar_bienes_materiales(self, filtros) -> ResultadoBienes:
        """Lectura sin escrituras. Devuelve ResultadoBienes; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def consultar_bienes_disponibles(self, texto="", id_recurso=None) -> list[BienDisponible]:
        """Lectura sin escrituras. Devuelve list[BienDisponible]; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def cambiar_estado_bien_material(
        self,
        id_bien,
        estado,
        motivo,
        dni_responsable,
        estado_esperado,
        fecha_fin_estimada=None,
        descripcion="",
    ) -> BienMaterial:
        """Escritura explícita. Devuelve BienMaterial y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def consultar_prestamo_pendiente(self, id_bien) -> int | None:
        """Lectura sin escrituras. Devuelve int | None; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def consultar_historial_bien_material(self, id_bien) -> list[dict[str, Any]]:
        """Devuelve todos los registros de estado."""
        raise NotImplementedError

    @abstractmethod
    def consultar_registros_fuera_servicio(self, id_bien) -> list[RegistroFueraServicio]:
        """Devuelve todas las entidades de registros fuera de servicio."""
        raise NotImplementedError
