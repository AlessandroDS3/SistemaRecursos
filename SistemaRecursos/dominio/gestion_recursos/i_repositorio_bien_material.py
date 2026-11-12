from __future__ import annotations
from dominio.gestion_recursos.bien_material import BienMaterial
from dominio.resultados_consulta import BienDisponible, BienListado, ResultadoBienes
from typing import Any
from abc import ABC, abstractmethod


class IRepositorioBienMaterial(ABC):
    @abstractmethod
    def registrar_bien_material(self, bien_material) -> BienMaterial:
        """Guarda un nuevo bien."""
        raise NotImplementedError

    @abstractmethod
    def existen_por_recurso(self, id_recurso) -> bool:
        """Indica si el recurso tiene bienes registrados."""
        raise NotImplementedError

    @abstractmethod
    def consultar_bien_material(self, id_bien) -> BienMaterial | None:
        """Busca un bien por su ID; devuelve None si no existe."""
        raise NotImplementedError

    @abstractmethod
    def actualizar_bien_material(self, bien_material) -> BienMaterial:
        """Actualiza los datos de un bien."""
        raise NotImplementedError

    @abstractmethod
    def eliminar_bien_material(self, id_bien) -> None:
        """Elimina un bien."""
        raise NotImplementedError

    @abstractmethod
    def contar_disponibles(self) -> int:
        """Cuenta los bienes disponibles."""
        raise NotImplementedError

    @abstractmethod
    def consultar_bienes_por_recurso(self, id_recurso=None) -> list[BienListado]:
        """Lista los bienes de un recurso, o todos si no se indica uno."""
        raise NotImplementedError

    @abstractmethod
    def consultar_bienes_materiales(self, filtros) -> ResultadoBienes:
        """Consulta los bienes y su resumen según los filtros."""
        raise NotImplementedError

    @abstractmethod
    def consultar_bienes_disponibles(self, texto="", id_recurso=None) -> list[BienDisponible]:
        """Busca bienes disponibles por texto y recurso."""
        raise NotImplementedError

    @abstractmethod
    def cambiar_estado_bien_material(
        self,
        id_bien,
        estado,
        motivo,
        dni_responsable,
        estado_esperado,
    ) -> BienMaterial:
        """Cambia el estado de un bien y registra el motivo y el responsable."""
        raise NotImplementedError

    @abstractmethod
    def consultar_prestamo_pendiente(self, id_bien) -> int | None:
        """Devuelve el ID del préstamo pendiente del bien, o None si no tiene."""
        raise NotImplementedError

    @abstractmethod
    def consultar_historial_bien_material(self, id_bien) -> list[dict[str, Any]]:
        """Consulta el historial de estados del bien."""
        raise NotImplementedError
