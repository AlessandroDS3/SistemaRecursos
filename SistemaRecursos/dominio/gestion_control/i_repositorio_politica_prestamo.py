from __future__ import annotations
from dominio.gestion_control.politica_prestamo import PoliticaPrestamo
from dominio.gestion_control.politica_prestamo import LimiteArticulosPrestamo
from abc import ABC, abstractmethod
from dominio.gestion_control.horario_atencion import HorarioAtencion
from dominio.gestion_control.politica_vencimiento_reserva import PoliticaVencimientoReserva


class IRepositorioPoliticaPrestamo(ABC):
    @abstractmethod
    def registrar_politica(self, politica) -> PoliticaPrestamo:
        """Escritura explícita. Devuelve PoliticaPrestamo y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def consultar_politica(self, id_politica) -> PoliticaPrestamo | None:
        """Lectura sin escrituras. Devuelve PoliticaPrestamo | None; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def actualizar_politica(self, politica) -> PoliticaPrestamo:
        """Escritura explícita. Devuelve PoliticaPrestamo y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def eliminar_politica(self, id_politica) -> None:
        """Escritura explícita. Devuelve None y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def consultar_politicas(self) -> list[PoliticaPrestamo]:
        """Lectura sin escrituras. Devuelve list[PoliticaPrestamo]; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def consultar_politica_aplicable(self, tipo_persona, id_categoria_ref) -> PoliticaPrestamo | None:
        """Lectura sin escrituras. Devuelve PoliticaPrestamo | None; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def consultar_horario_atencion(self) -> HorarioAtencion:
        """Lectura del horario general de la institución, sin escrituras."""
        raise NotImplementedError

    @abstractmethod
    def actualizar_horario_atencion(self, horario: HorarioAtencion) -> HorarioAtencion:
        """Actualiza el horario para las próximas entregas."""
        raise NotImplementedError

    @abstractmethod
    def consultar_politica_vencimiento_reserva(self) -> PoliticaVencimientoReserva:
        raise NotImplementedError

    @abstractmethod
    def actualizar_politica_vencimiento_reserva(self, politica: PoliticaVencimientoReserva) -> PoliticaVencimientoReserva:
        raise NotImplementedError

    @abstractmethod
    def consultar_limites_articulos(self) -> list[LimiteArticulosPrestamo]:
        """Consulta los máximos generales por tipo de persona, sin escrituras."""
        raise NotImplementedError

    @abstractmethod
    def actualizar_limites_articulos(self, limites: list[LimiteArticulosPrestamo]) -> None:
        """Guarda en una transacción los máximos elegidos por el administrador."""
        raise NotImplementedError
