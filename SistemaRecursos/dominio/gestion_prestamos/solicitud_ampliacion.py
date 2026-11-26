"""Solicitudes de ampliación hechas por el usuario y revisadas por el encargado (AMP-01).

La ampliación directa del encargado sigue existiendo; la solicitud solo agrega el paso
de pedirla con un motivo. Al aprobar se revalida todo con las reglas de AmpliacionPrestamo.
"""

from dataclasses import dataclass

from dominio.compartido.codigos import Codigo
from dominio.compartido.validacion import Conflicto, NoEncontrado, validar_entero, validar_texto
from dominio.gestion_control.politica_prestamo import UnidadPlazo

class EstadoSolicitudAmpliacion(Codigo):
    PENDIENTE = 'PENDIENTE'
    APROBADA = 'APROBADA'
    RECHAZADA = 'RECHAZADA'


@dataclass(init=False)
class SolicitudAmpliacion:
    cantidad: int
    unidad: UnidadPlazo
    motivo: str

    def __init__(self, *, cantidad: int | str | None, unidad: str | None, motivo: str | None) -> None:
        self.cantidad = validar_entero(cantidad, 'Tiempo adicional', maximo=87600)
        if unidad not in tuple(UnidadPlazo):
            raise ValueError('Selecciona horas o días.')
        self.unidad = UnidadPlazo(unidad)
        self.motivo = validar_texto(motivo, 'Motivo de la solicitud', 255, True)


def exigir_solicitud_ampliacion_pendiente(solicitud: dict | None) -> dict:
    if solicitud is None:
        raise NoEncontrado('Solicitud inexistente.')
    if solicitud['estado'] != EstadoSolicitudAmpliacion.PENDIENTE:
        raise Conflicto('La solicitud ya fue resuelta. Recarga la lista.')
    return solicitud


def exigir_titular_del_prestamo_para_ampliacion(responsable: str, documento: str) -> None:
    if responsable != documento:
        raise PermissionError('Solo la persona responsable del préstamo puede pedir una ampliación.')
