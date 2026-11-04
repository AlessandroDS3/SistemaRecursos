from abc import ABC, abstractmethod


class IRepositorioSancion(ABC):
    @abstractmethod
    def aplicar_sanciones_vencidas(self) -> int:
        """Comando automático e idempotente: una sanción por detalle vencido."""
        raise NotImplementedError

    @abstractmethod
    def levantar_sancion_vencimiento(self, id_prestamo: int, id_detalle: int, justificacion: str, dni_encargado: str) -> None:
        """Retira la sanción por tardanza con responsable y justificación."""
        raise NotImplementedError
