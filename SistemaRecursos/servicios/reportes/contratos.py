"""Operaciones de consulta requeridas por los reportes."""

from typing import Protocol

from servicios.reportes.filtro_reporte import FiltroReporte


class IRepositorioReporte(Protocol):
    def consultar_filas_reporte(self, filtro: FiltroReporte) -> list[dict]: ...
    def consultar_historial(self, filtro: FiltroReporte, solo_prestamos: bool = False) -> dict: ...
