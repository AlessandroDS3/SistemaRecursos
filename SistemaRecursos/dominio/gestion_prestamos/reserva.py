from dominio.compartido.validacion import NoEncontrado
from typing import Protocol
from dominio.compartido.validacion import entero, fecha_local, texto
from dominio.compartido.contratos import IRepositorioTransaccional
from dominio.gestion_personas_usuarios.persona import validar_elegibilidad
from dominio.gestion_prestamos.prestamo import IRepositorioPrestamo
from dominio.compartido.validacion import Conflicto

ESTADOS_RESERVA = (
    'EN_ESPERA',
    'LISTA_PARA_RETIRO',
    'ATENDIDA',
    'CANCELADA',
    'EXPIRADA',
    'RECHAZADA',
)


def nueva_reserva(datos, documento, ahora):
    tipo = datos.get('tipo_gestion', 'PRESTAMO')
    if tipo not in ('PRESTAMO', 'RESERVA'):
        raise ValueError('Tipo de gestión inválido.')
    if datos.get('acepta_condiciones') != '1':
        raise ValueError('Confirma que revisaste el plazo y el permiso de salida del recurso.')
    requerida = ahora if tipo == 'PRESTAMO' else fecha_local(datos.get('fecha_requerida'))
    if tipo == 'RESERVA' and requerida <= ahora:
        raise ValueError('La reserva debe indicar una fecha futura.')
    return dict(
        dni_persona=documento,
        id_recurso=entero(datos.get('id_recurso'), 'Recurso'),
        fecha_solicitud=ahora,
        fecha_requerida=requerida,
        tipo_gestion=tipo,
        observaciones=texto(datos.get('observaciones'), 'Observaciones', 220),
        salida_solicitada=datos.get('salida_solicitada') == '1',
    )


def validar_solicitud(reserva, contexto, comprobar_duplicada=False):
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


def validar_accion(reserva, accion, actor, gestionar, ahora):
    if accion == 'cancelar':
        if not gestionar and reserva['dni_persona'] != actor:
            raise PermissionError('Solo puedes cancelar tus reservas.')
        if reserva['estado'] not in ('EN_ESPERA', 'LISTA_PARA_RETIRO'):
            raise Conflicto('La reserva ya no se puede cancelar.')
    else:
        if not gestionar:
            raise PermissionError('La acción requiere gestionar préstamos.')
        esperados = (
            ('EN_ESPERA', 'LISTA_PARA_RETIRO')
            if accion in ('rechazar', 'expirar')
            else (('EN_ESPERA',) if accion == 'preparar' else ('LISTA_PARA_RETIRO',))
        )
        if reserva['estado'] not in esperados:
            raise Conflicto('El estado de la reserva no permite esta acción.')
    if accion in ('preparar', 'entregar'):
        if (
            reserva['fecha_limite_vencimiento'] is not None
            and reserva['fecha_limite_vencimiento'] <= ahora
        ):
            raise Conflicto('El plazo de la reserva venció.')
        if reserva['fecha_requerida'] > ahora:
            raise Conflicto('Todavía no llegó la fecha requerida.')


class IRepositorioReserva(IRepositorioTransaccional, Protocol):
    def opciones(self, documento: str) -> list[dict]: ...
    @property
    def prestamos(self) -> IRepositorioPrestamo: ...
    def consultar(self, identificador: int, bloquear=False) -> dict | None: ...
    def listar(self, documento: str | None = None, filtros: dict | None = None) -> list[dict]: ...
    def guardar(self, datos: dict): ...
    def cambiar(self, identificador: int, datos: dict): ...
    def cargar_solicitud(self, documento: str, recurso: int) -> dict: ...
    def configuracion(self) -> dict | None: ...
    def bloquear_recurso(self, identificador: int) -> dict | None: ...
    def primera_en_espera(self, recurso: int, ahora) -> dict | None: ...
    def bien_disponible(self, recurso: int) -> dict | None: ...
    def cambiar_bien(
        self, bien: int, estado: str, esperado: str, actor: str | None, reserva: int
    ): ...
    def candidatas_vencidas(self) -> list[dict]: ...
