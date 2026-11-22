from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol, TypedDict
from dominio.compartido.contratos import IRepositorioTransaccional
from dominio.compartido.validacion import Conflicto, entero, instante, texto


@dataclass(kw_only=True)
class AmpliacionPrestamo:
    cantidad: int
    unidad: str
    fecha_anterior: object
    motivo: str = ''

    def __post_init__(self):
        self.cantidad = entero(self.cantidad, 'Tiempo adicional', maximo=87600)
        if self.unidad not in ('HORAS', 'DIAS'):
            raise ValueError('Selecciona horas o días.')
        self.fecha_anterior = instante(self.fecha_anterior)
        self.motivo = texto(self.motivo, 'Motivo', 120)

    def calcular(self, detalle, ahora, politica, horario):
        actual = detalle['fecha_limite_devolucion']
        if actual != self.fecha_anterior:
            raise Conflicto('El plazo cambió. Recarga antes de volver a ampliar.')
        if (
            actual <= ahora
            or detalle['fecha_devolucion'] is not None
            or detalle.get('fecha_regularizacion') is not None
            or detalle['estado_bien'] != 'PRESTADO'
        ):
            raise Conflicto(
                'Solo se amplían bienes prestados, no vencidos y pendientes de devolución.'
            )
        extra = timedelta(**{'hours' if self.unidad == 'HORAS' else 'days': self.cantidad})
        if extra > politica.duracion:
            raise ValueError('La ampliación no puede superar otro plazo de la política.')
        try:
            nueva = actual + extra
        except OverflowError:
            raise ValueError('La ampliación produce una fecha fuera de rango.') from None
        if politica.unidad_plazo == 'HORAS' and (horario is None or nueva > horario.cierre(actual)):
            raise ValueError('La ampliación debe respetar el cierre de atención.')
        return nueva


class ContextoAmpliacion(TypedDict):
    prestamo: dict | None
    detalle: dict | None
    politica: dict | None
    horario: dict | None


class IRepositorioAmpliacionPrestamo(IRepositorioTransaccional, Protocol):
    def consultar_contexto_ampliacion_prestamo(
        self, prestamo: int, detalle: int
    ) -> ContextoAmpliacion: ...
    def actualizar_plazo_prestamo(self, detalle: int, anterior, nueva): ...
