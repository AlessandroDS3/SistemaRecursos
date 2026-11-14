from __future__ import annotations
from dominio.resultados_consulta import PrestamoDetalle, PrestamoListado, ResumenPrestamos
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from dominio.gestion_prestamos.i_operacion_prestamo import IOperacionPrestamo


class IRepositorioPrestamo(ABC):
    @abstractmethod
    def transaccion(self) -> AbstractContextManager[IOperacionPrestamo]:
        """Abre una operación de escritura sin exponer conexiones ni cursores."""
        raise NotImplementedError

    @abstractmethod
    def consultar_prestamo(self, id_prestamo) -> PrestamoDetalle | None:
        """Lectura sin escrituras. Devuelve PrestamoDetalle | None; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def consultar_resumen_prestamos(self, dni=None) -> ResumenPrestamos:
        """Lectura sin escrituras. Devuelve ResumenPrestamos; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def consultar_prestamos(self, filtros=None, dni=None) -> list[PrestamoListado]:
        """Lectura sin escrituras. Devuelve list[PrestamoListado]; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError
