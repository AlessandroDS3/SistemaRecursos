from abc import ABC, abstractmethod


class IOperacionPrestamo(ABC):
    """Acceso a datos de una escritura; sus bloqueos duran hasta salir de la transacción."""

    @abstractmethod
    def cargar_entrega(self, solicitud):
        raise NotImplementedError

    @abstractmethod
    def guardar_entrega(self, prestamo, bienes, ahora):
        raise NotImplementedError

    @abstractmethod
    def cargar_recepcion(self, id_prestamo, dni_encargado):
        raise NotImplementedError

    @abstractmethod
    def guardar_devoluciones(self, prestamo, anterior, devoluciones, detalles, dni_encargado, ahora):
        raise NotImplementedError

    @abstractmethod
    def registrar_sancion_vencimiento(self, detalle, ahora):
        raise NotImplementedError

    @abstractmethod
    def guardar_perdida(self, prestamo, detalle, motivo, dni_encargado):
        raise NotImplementedError

    @abstractmethod
    def cargar_vencidos(self, dni=None):
        raise NotImplementedError

    @abstractmethod
    def guardar_estado(self, prestamo, anterior, observacion, dni_encargado):
        raise NotImplementedError

    @abstractmethod
    def ahora(self):
        raise NotImplementedError

    @abstractmethod
    def cargar_cuenta_ampliacion(self, id_usuario):
        raise NotImplementedError

    @abstractmethod
    def cargar_politica_ampliacion(self, id_politica):
        raise NotImplementedError

    @abstractmethod
    def guardar_fecha_limite(self, id_detalle, anterior, nueva):
        raise NotImplementedError
