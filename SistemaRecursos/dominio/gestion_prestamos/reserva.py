from datetime import datetime, timedelta
from typing import Final, Mapping, TypedDict

from dominio.compartido.validacion import Conflicto, NoEncontrado, entero, fecha_local, texto
from dominio.gestion_personas_usuarios.persona import validar_elegibilidad

EN_ESPERA: Final = 'EN_ESPERA'
LISTA_PARA_RETIRO: Final = 'LISTA_PARA_RETIRO'
ATENDIDA: Final = 'ATENDIDA'
CANCELADA: Final = 'CANCELADA'
EXPIRADA: Final = 'EXPIRADA'
RECHAZADA: Final = 'RECHAZADA'

ESTADOS_RESERVA = (EN_ESPERA, LISTA_PARA_RETIRO, ATENDIDA, CANCELADA, EXPIRADA, RECHAZADA)
ESTADOS_PENDIENTES = (EN_ESPERA, LISTA_PARA_RETIRO)
FILTRO_PENDIENTES = 'PENDIENTES'
ANTICIPACION_MAXIMA = timedelta(days=7)

ESTADOS_POR_ACCION = {
    'cancelar': ESTADOS_PENDIENTES,
    'rechazar': ESTADOS_PENDIENTES,
    'expirar': ESTADOS_PENDIENTES,
    'preparar': (EN_ESPERA,),
    'entregar': (LISTA_PARA_RETIRO,),
}
ESTADOS_CIERRE = {
    'cancelar': CANCELADA,
    'rechazar': RECHAZADA,
    'expirar': EXPIRADA,
}


class NuevaReserva(TypedDict):
    dni_persona: str
    id_recurso: int
    fecha_solicitud: datetime
    fecha_requerida: datetime
    tipo_gestion: str
    observaciones: str
    salida_solicitada: bool
    fecha_limite_vencimiento: datetime | None


class Reserva(NuevaReserva):
    id_reserva: int
    estado: str
    id_bien: int | None
    fecha_preparacion: datetime | None
    id_prestamo_ref: int | None
    recurso: str
    solicitante: str


class HistorialReserva(TypedDict, total=False):
    historial: list[dict]
    ventana_atencion: str


class DetalleReserva(Reserva, HistorialReserva):
    codigo_inventario: str | None
    estado_bien: str | None
    recurso_bien: int | None


class ContextoReserva(TypedDict):
    persona: dict | None
    recurso: dict | None
    politica: dict | None
    vencido: bool
    sancion: bool
    duplicada: bool


class CambiosReserva(TypedDict, total=False):
    estado: str
    id_bien: int | None
    fecha_preparacion: datetime
    fecha_limite_vencimiento: datetime
    id_prestamo_ref: int


def nueva_reserva(datos: Mapping[str, str], documento: str, ahora: datetime) -> NuevaReserva:
    if datos.get('tipo_gestion', 'RESERVA') != 'RESERVA':
        raise ValueError('El préstamo inmediato se registra presencialmente con el encargado.')
    if datos.get('acepta_condiciones') != '1':
        raise ValueError('Confirma que revisaste el plazo y el permiso de salida del recurso.')
    requerida = fecha_local(datos.get('fecha_requerida'))
    if requerida <= ahora:
        raise ValueError('La reserva debe indicar una fecha futura.')
    if requerida - ahora > ANTICIPACION_MAXIMA:
        raise ValueError('Puedes reservar con un máximo de 7 días de anticipación.')
    return {
        'dni_persona': documento,
        'id_recurso': entero(datos.get('id_recurso'), 'Recurso'),
        'fecha_solicitud': ahora,
        'fecha_requerida': requerida,
        'tipo_gestion': 'RESERVA',
        'observaciones': texto(datos.get('observaciones'), 'Observaciones', 220),
        'salida_solicitada': datos.get('salida_solicitada') == '1',
        'fecha_limite_vencimiento': None,
    }


def validar_solicitud(
    reserva: NuevaReserva, contexto: ContextoReserva, comprobar_duplicada: bool = False
) -> None:
    validar_elegibilidad(contexto['persona'])
    if contexto['recurso'] is None:
        raise NoEncontrado('Recurso inexistente.')
    if contexto['vencido'] or contexto['sancion']:
        raise Conflicto('El solicitante tiene bienes vencidos o una sanción activa.')
    if contexto['politica'] is None:
        raise ValueError('No hay una política vigente para este recurso y tipo de persona.')
    if reserva['salida_solicitada'] and not contexto['politica']['permite_salida']:
        raise ValueError('La política no permite la salida externa.')
    if comprobar_duplicada and contexto['duplicada']:
        raise Conflicto('Ya tienes una solicitud o reserva pendiente para este recurso.')


def validar_accion(
    reserva: Reserva, accion: str, actor: str, gestionar: bool, ahora: datetime
) -> None:
    if accion not in ESTADOS_POR_ACCION:
        raise ValueError('Acción de reserva inválida.')
    if accion == 'cancelar':
        if not gestionar and reserva['dni_persona'] != actor:
            raise PermissionError('Solo puedes cancelar tus reservas.')
        if reserva['estado'] not in ESTADOS_POR_ACCION[accion]:
            raise Conflicto('La reserva ya no se puede cancelar.')
        return

    if not gestionar:
        raise PermissionError('La acción requiere gestionar préstamos.')

    esperados = ESTADOS_POR_ACCION[accion]
    if reserva['estado'] not in esperados:
        raise Conflicto('El estado de la reserva no permite esta acción.')

    if accion == 'expirar' and ventana_atencion_reserva(reserva, ahora) != 'VENCIDA':
        raise Conflicto('La reserva solo puede marcarse vencida después de su plazo.')
    if accion not in ('preparar', 'entregar'):
        return

    ventana = ventana_atencion_reserva(reserva, ahora)
    if ventana == 'VENCIDA':
        raise Conflicto('El plazo de la reserva venció.')
    if ventana == 'FUTURA':
        raise Conflicto('Todavía no llegó la fecha requerida.')


def ventana_atencion_reserva(reserva: Reserva, ahora: datetime) -> str:
    limite = reserva['fecha_limite_vencimiento']
    if limite is not None and limite <= ahora:
        return 'VENCIDA'
    if reserva['fecha_requerida'] > ahora:
        return 'FUTURA'
    return 'ABIERTA'
