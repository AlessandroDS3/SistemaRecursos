"""Solicitudes de ampliación hechas por el usuario y revisadas por el encargado (AMP-01).

La ampliación directa del encargado sigue existiendo; la solicitud solo agrega el paso
de pedirla con un motivo. Al aprobar se revalida todo con las reglas de AmpliacionPrestamo.
"""

from dataclasses import dataclass

from dominio.compartido.validacion import Conflicto, NoEncontrado, entero, texto

ESTADOS_SOLICITUD = ('PENDIENTE', 'APROBADA', 'RECHAZADA')


@dataclass(kw_only=True)
class SolicitudAmpliacion:
    cantidad: int
    unidad: str
    motivo: str

    def __post_init__(self):
        self.cantidad = entero(self.cantidad, 'Tiempo adicional', maximo=87600)
        if self.unidad not in ('HORAS', 'DIAS'):
            raise ValueError('Selecciona horas o días.')
        self.motivo = texto(self.motivo, 'Motivo de la solicitud', 255, True)


def exigir_pendiente(solicitud: dict | None) -> dict:
    if solicitud is None:
        raise NoEncontrado('Solicitud inexistente.')
    if solicitud['estado'] != 'PENDIENTE':
        raise Conflicto('La solicitud ya fue resuelta. Recarga la lista.')
    return solicitud


def exigir_responsable(prestamo: dict, documento: str) -> None:
    if prestamo['dni_persona'] != documento:
        raise PermissionError('Solo la persona responsable del préstamo puede pedir una ampliación.')
