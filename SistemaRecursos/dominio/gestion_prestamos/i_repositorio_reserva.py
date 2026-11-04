from __future__ import annotations
from dominio.resultados_consulta import ReservaDetalle, ResultadoReservas
from abc import ABC, abstractmethod

from dominio.gestion_prestamos.reserva import Reserva, AccionReserva


class IRepositorioReserva(ABC):
    @abstractmethod
    def registrar_reserva(self, reserva: Reserva, responsable: str) -> int:
        """Escritura explícita. Devuelve int y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def consultar_reserva(self, identificador: int) -> ReservaDetalle | None:
        """Lectura sin escrituras. Devuelve ReservaDetalle | None; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def consultar_reservas(self, filtros: dict, persona: str | None) -> ResultadoReservas:
        """Lectura sin escrituras. Devuelve ResultadoReservas; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def preparar_reserva(self, identificador: int, responsable: str, gestionar: bool,
                       motivo: str = "", acepta: bool = False) -> int | None:
        """Escritura explícita. Devuelve int | None y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def entregar_reserva(self, identificador: int, responsable: str, gestionar: bool,
                       motivo: str = "", acepta: bool = False) -> int | None:
        """Escritura explícita. Devuelve int | None y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def cancelar_reserva(self, identificador: int, responsable: str, gestionar: bool,
                       motivo: str = "", acepta: bool = False) -> int | None:
        """Escritura explícita. Devuelve int | None y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def rechazar_reserva(self, identificador: int, responsable: str, gestionar: bool,
                       motivo: str = "", acepta: bool = False) -> int | None:
        """Escritura explícita. Devuelve int | None y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def expirar_reserva(self, identificador: int, responsable: str, gestionar: bool,
                       motivo: str = "", acepta: bool = False) -> int | None:
        """Escritura explícita. Devuelve int | None y propaga errores de validación o integridad."""
        raise NotImplementedError


    @abstractmethod
    def expirar_solicitudes_vencidas(self) -> int:
        """Expira solicitudes vencidas, libera bienes e inserta historial."""
        raise NotImplementedError
