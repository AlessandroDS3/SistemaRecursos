from abc import ABC, abstractmethod

from dominio.gestion_prestamos.ampliacion_prestamo import AmpliacionPrestamo


class IRepositorioAmpliacionPrestamo(ABC):
    @abstractmethod
    def solicitar_ampliacion(self, id_prestamo, ampliacion, dni_responsable) -> AmpliacionPrestamo:
        raise NotImplementedError

    @abstractmethod
    def aprobar_ampliacion(self, id_prestamo, id_ampliacion, id_usuario, observacion='') -> AmpliacionPrestamo:
        raise NotImplementedError

    @abstractmethod
    def rechazar_ampliacion(self, id_prestamo, id_ampliacion, id_usuario, observacion) -> AmpliacionPrestamo:
        raise NotImplementedError

    @abstractmethod
    def consultar_ampliaciones(self, id_prestamo) -> list[dict]:
        raise NotImplementedError
