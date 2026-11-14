"""Contratos de consulta para reportes; no realizan escrituras."""
from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TypedDict


# I repositorio reporte

class IRepositorioReporte(ABC):
    @abstractmethod
    def consultar_prestamos(self, filtros, paginar=True) -> ResultadoReportePrestamos:
        """Consulta entregas y devoluciones sin modificar registros."""
        raise NotImplementedError


# Resultados de consulta

class IntegranteReporte(TypedDict):
    dni: str
    nombre: str
    responsable: bool


class FilaReportePrestamo(TypedDict):
    id_prestamo: int
    id_detalle: int
    tipo_prestamo: str
    estado: str
    dni_persona: str
    solicitante: str
    tipo_persona: str
    codigo_inventario: str
    recurso: str
    fecha_entrega: datetime
    fecha_limite_devolucion: datetime
    fecha_devolucion: datetime | None
    condicion_devolucion: str | None
    situacion: str
    integrantes: list[IntegranteReporte]


class ResumenReportePrestamos(TypedDict):
    prestamos: int
    bienes: int
    devueltos: int
    pendientes: int
    vencidos: int


class ResultadoReportePrestamos(TypedDict):
    filas: list[FilaReportePrestamo]
    resumen: ResumenReportePrestamos
    pagina: int
    paginas: int
