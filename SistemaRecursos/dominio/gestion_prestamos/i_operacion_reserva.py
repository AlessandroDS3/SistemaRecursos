from abc import ABC, abstractmethod
from dominio.gestion_prestamos.i_operacion_prestamo import IOperacionPrestamo


class IOperacionEntregaReserva(ABC):
    @property
    @abstractmethod
    def prestamos(self) -> IOperacionPrestamo:
        raise NotImplementedError

    @abstractmethod
    def cargar_reserva(self, id_reserva, responsable, gestionar):
        raise NotImplementedError

    @abstractmethod
    def guardar_entrega(self, reserva, anterior, id_prestamo, motivo, responsable):
        raise NotImplementedError

    @abstractmethod
    def ahora(self):
        raise NotImplementedError
