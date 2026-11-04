from __future__ import annotations
from dominio.gestion_prestamos.solicitud_prestamo import SolicitudPrestamo
from dominio.gestion_prestamos.prestamo import Prestamo
from dominio.resultados_consulta import PrestamoDetalle, PrestamoListado, ResumenPrestamos
from abc import ABC, abstractmethod


class IRepositorioPrestamo(ABC):
    @abstractmethod
    def registrar_prestamo(self, solicitud: SolicitudPrestamo) -> Prestamo:
        """Recibe SolicitudPrestamo y devuelve la entrega con políticas, fechas e ID definitivos."""
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

    @abstractmethod
    def actualizar_prestamos_vencidos(self, dni_responsable, dni=None) -> None:
        """Escritura explícita. Devuelve None y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def registrar_devolucion(self, id_prestamo, devoluciones, dni_encargado) -> None:
        """Escritura explícita. Devuelve None y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def reportar_perdida(self, id_prestamo, id_detalle, motivo, dni_encargado) -> None:
        """Escritura explícita. Devuelve None y propaga errores de validación o integridad."""
        raise NotImplementedError
