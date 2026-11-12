from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from dominio.gestion_recursos.validacion_recurso import entero, instante_utc, texto


class EstadoAmpliacion(str, Enum):
    PENDIENTE = 'PENDIENTE'
    APROBADA = 'APROBADA'
    RECHAZADA = 'RECHAZADA'


class ConflictoAmpliacionError(ValueError):
    pass


@dataclass(kw_only=True)
class AmpliacionPrestamo:
    id_detalle: int
    fecha_limite_nueva: datetime
    motivo: str
    id_ampliacion: int | None = None
    fecha_solicitud: datetime | None = None
    fecha_limite_anterior: datetime | None = None
    estado: EstadoAmpliacion = EstadoAmpliacion.PENDIENTE
    fecha_resolucion: datetime | None = None
    id_usuario_resolucion: int | None = None
    observacion_resolucion: str | None = None

    def __post_init__(self):
        self.id_detalle = entero(self.id_detalle, 'Detalle del préstamo')
        self.fecha_limite_nueva = instante_utc(self.fecha_limite_nueva, 'Nueva fecha de devolución')
        self.motivo = texto(self.motivo, 'Motivo de la ampliación', 255, True)
        self.estado = EstadoAmpliacion(self.estado)
        if self.fecha_limite_anterior is not None:
            self.fecha_limite_anterior = instante_utc(self.fecha_limite_anterior, 'Fecha anterior')

    def validar_plazo(self, fecha_actual, ahora, politica, horario=None):
        fecha_actual = instante_utc(fecha_actual, 'Fecha actual de devolución')
        if self.fecha_limite_anterior is not None and self.fecha_limite_anterior != fecha_actual:
            raise ConflictoAmpliacionError('La fecha del bien cambió desde la solicitud. Rechaza esta ampliación y solicita una nueva.')
        if fecha_actual <= ahora:
            raise ConflictoAmpliacionError('El plazo del bien ya venció; no se puede ampliar.')
        if self.fecha_limite_nueva <= fecha_actual:
            raise ValueError('La nueva fecha debe ser posterior al límite actual.')
        maximo = politica.fecha_limite(fecha_actual, horario)
        if self.fecha_limite_nueva > maximo:
            raise ValueError('La ampliación puede añadir como máximo otro plazo de la política y debe respetar el horario de atención.')
        self.fecha_limite_anterior = fecha_actual

    def aprobar(self, id_usuario, ahora, observacion=''):
        self._resolver(EstadoAmpliacion.APROBADA, id_usuario, ahora, observacion)

    def rechazar(self, id_usuario, ahora, observacion):
        self._resolver(EstadoAmpliacion.RECHAZADA, id_usuario, ahora, observacion)

    def _resolver(self, estado, id_usuario, ahora, observacion):
        if self.estado != EstadoAmpliacion.PENDIENTE:
            raise ConflictoAmpliacionError('Esta ampliación ya fue resuelta. Recarga el préstamo.')
        nota = texto(observacion, 'Observación de la resolución', 255,
                     estado == EstadoAmpliacion.RECHAZADA)
        self.id_usuario_resolucion = entero(id_usuario, 'Usuario que resuelve')
        self.fecha_resolucion = instante_utc(ahora, 'Fecha de resolución')
        self.observacion_resolucion = nota or None
        self.estado = estado
