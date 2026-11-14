from dataclasses import dataclass
from datetime import datetime, timedelta

from dominio.gestion_recursos.validacion_recurso import entero, instante_utc, texto


class ConflictoAmpliacionError(ValueError):
    pass


@dataclass(kw_only=True)
class AmpliacionPrestamo:
    """Regla de ampliación directa; no representa una tabla ni una solicitud."""
    cantidad: int
    unidad: str
    fecha_limite_anterior: datetime
    motivo: str = ''

    def __post_init__(self):
        try:
            self.cantidad = entero(self.cantidad, 'Tiempo adicional')
        except ValueError:
            raise ValueError('Indica una cantidad entera y positiva de tiempo adicional.') from None
        if self.unidad not in ('HORAS', 'DIAS'):
            raise ValueError('Selecciona horas o días para la ampliación.')
        self.fecha_limite_anterior = instante_utc(self.fecha_limite_anterior, 'Fecha actual de devolución')
        self.motivo = texto(self.motivo, 'Observación de la ampliación', 120)

    def calcular_fecha(self, detalle, ahora, politica, horario=None):
        if detalle['fecha_devolucion'] is not None or detalle['estado_actual'] != 'PRESTADO':
            raise ConflictoAmpliacionError('Solo se pueden ampliar bienes prestados y pendientes de devolución.')
        actual = detalle['fecha_limite_devolucion']
        if actual != self.fecha_limite_anterior:
            raise ConflictoAmpliacionError('El plazo cambió. Recarga el préstamo antes de ampliar de nuevo.')
        if actual <= ahora:
            raise ConflictoAmpliacionError('El plazo del bien ya venció; no se puede ampliar.')
        segundos = self.cantidad * (3600 if self.unidad == 'HORAS' else 86400)
        maximo = politica.plazo_maximo * (3600 if politica.unidad_plazo == 'HORAS' else 86400)
        if segundos > maximo:
            raise ValueError('La ampliación puede añadir como máximo otro plazo de la política del recurso.')
        if politica.unidad_plazo == 'HORAS' and horario is None:
            raise ValueError('Configura el horario de atención antes de ampliar un préstamo por horas.')
        try:
            nueva = actual + timedelta(seconds=segundos)
            limite = politica.fecha_limite(actual, horario)
        except OverflowError:
            raise ValueError('La nueva fecha de devolución está fuera del rango permitido.') from None
        if nueva > limite:
            raise ValueError('La ampliación debe respetar el cierre de atención.')
        return nueva
