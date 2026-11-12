from abc import ABC, abstractmethod
from dominio.resultados_consulta import ResultadoReportePrestamos


class IRepositorioReporte(ABC):
    @abstractmethod
    def consultar_prestamos(self, filtros, paginar=True) -> ResultadoReportePrestamos:
        """Consulta entregas y devoluciones sin modificar registros."""
        raise NotImplementedError
