from dataclasses import dataclass, replace
from datetime import datetime, timedelta
import json
from typing import Literal, Mapping, TypedDict

from dominio.compartido.codigos import Codigo
from dominio.compartido.contratos import FilaHistorialEstado
from dominio.compartido.validacion import (
    Conflicto,
    NoEncontrado,
    validar_dni,
    validar_entero,
    convertir_fecha_local_de_lima_a_utc,
    validar_texto,
)
from dominio.gestion_personas_usuarios.persona import (
    PersonaParaPrestamo,
    validar_elegibilidad_del_solicitante,
)
from dominio.gestion_prestamos.prestamo import validar_integrantes


class EstadoReserva(Codigo):
    EN_ESPERA = 'EN_ESPERA'
    LISTA_PARA_RETIRO = 'LISTA_PARA_RETIRO'
    ATENDIDA = 'ATENDIDA'
    CANCELADA = 'CANCELADA'
    EXPIRADA = 'EXPIRADA'
    RECHAZADA = 'RECHAZADA'


EN_ESPERA = EstadoReserva.EN_ESPERA
LISTA_PARA_RETIRO = EstadoReserva.LISTA_PARA_RETIRO
ESTADOS_RESERVA = tuple(EstadoReserva)
ESTADOS_PENDIENTES = (EN_ESPERA, LISTA_PARA_RETIRO)
FILTRO_PENDIENTES = 'PENDIENTES'
ANTICIPACION_MAXIMA = timedelta(days=7)

AccionReserva = Literal['cancelar', 'rechazar', 'expirar', 'preparar', 'entregar']
VentanaReserva = Literal['VENCIDA', 'FUTURA', 'ABIERTA']
ESTADOS_POR_ACCION: dict[AccionReserva, tuple[EstadoReserva, ...]] = {
    'cancelar': ESTADOS_PENDIENTES,
    'rechazar': ESTADOS_PENDIENTES,
    'expirar': ESTADOS_PENDIENTES,
    'preparar': (EN_ESPERA,),
    'entregar': (LISTA_PARA_RETIRO,),
}
ESTADOS_CIERRE = {
    'cancelar': EstadoReserva.CANCELADA,
    'rechazar': EstadoReserva.RECHAZADA,
    'expirar': EstadoReserva.EXPIRADA,
}


class ResumenReserva(TypedDict):
    id_reserva: int
    dni_persona: str
    id_recurso: int
    fecha_solicitud: datetime
    fecha_requerida: datetime
    tipo_gestion: str
    observaciones: str
    salida_solicitada: bool
    fecha_limite_vencimiento: datetime | None
    estado: str
    id_bien: int | None
    fecha_preparacion: datetime | None
    id_prestamo_ref: int | None
    recurso: str
    solicitante: str
    id_reserva_principal: int | None
    participantes: str | list[str] | None


class ReservaEnCola(ResumenReserva):
    posicion: int | None
    cantidad_bienes: int
    recursos: str


class DetalleReserva(ResumenReserva, total=False):
    codigo_inventario: str | None
    estado_bien: str | None
    recurso_bien: int | None
    historial: list[FilaHistorialEstado]
    ventana_atencion: VentanaReserva
    bienes: list['DetalleReserva']


@dataclass(frozen=True, kw_only=True)
class DatosParaValidarReserva:
    persona: PersonaParaPrestamo | None
    existe_recurso: bool
    permite_salida: bool | None
    bloqueado: bool
    duplicada: bool


def ventana_atencion_reserva(
    requerida: datetime, limite: datetime | None, ahora: datetime
) -> VentanaReserva:
    if limite is not None and limite <= ahora:
        return 'VENCIDA'
    return 'FUTURA' if requerida > ahora else 'ABIERTA'


def validar_recursos_de_reserva(datos: Mapping) -> list[int]:
    lineas = datos.get('recursos', [(datos.get('id_recurso'), 1)])
    if not isinstance(lineas, (list, tuple)) or not lineas:
        raise ValueError('Selecciona los bienes.')
    recursos: list[int] = []
    for linea in lineas:
        if not isinstance(linea, (list, tuple)) or len(linea) != 2:
            raise ValueError('Indica la cantidad de cada recurso.')
        recurso, cantidad = linea
        recurso = validar_entero(recurso, 'Recurso')
        cantidad = validar_entero(cantidad, 'Cantidad')
        if len(recursos) + cantidad > 100:
            raise ValueError('La cantidad supera el máximo de bienes de una reserva.')
        recursos.extend([recurso] * cantidad)
    return recursos


@dataclass(frozen=True, kw_only=True)
class Reserva:
    dni_persona: str
    id_recurso: int
    fecha_solicitud: datetime
    fecha_requerida: datetime
    tipo_gestion: str = 'RESERVA'
    observaciones: str = ''
    salida_solicitada: bool = False
    id_reserva: int | None = None
    estado: EstadoReserva = EN_ESPERA
    fecha_limite_vencimiento: datetime | None = None
    id_bien: int | None = None
    fecha_preparacion: datetime | None = None
    id_prestamo_ref: int | None = None
    id_reserva_principal: int | None = None
    participantes: tuple[str, ...] = ()

    @classmethod
    def desde_formulario(cls, datos: Mapping, documento: str, ahora: datetime) -> 'Reserva':
        if datos.get('tipo_gestion', 'RESERVA') != 'RESERVA':
            raise ValueError('El préstamo inmediato se registra presencialmente con el encargado.')
        if datos.get('acepta_condiciones') != '1':
            raise ValueError('Confirma que revisaste el plazo y el permiso de salida del recurso.')
        requerida = convertir_fecha_local_de_lima_a_utc(datos.get('fecha_requerida'))
        if requerida <= ahora:
            raise ValueError('La reserva debe indicar una fecha futura.')
        if requerida - ahora > ANTICIPACION_MAXIMA:
            raise ValueError('Puedes reservar con un máximo de 7 días de anticipación.')
        documento = validar_dni(documento)
        participantes = validar_integrantes(
            documento, datos.get('participantes', []), datos.get('tipo_prestamo', 'INDIVIDUAL'),
        )
        return cls(
            dni_persona=documento, id_recurso=validar_entero(datos.get('id_recurso'), 'Recurso'),
            fecha_solicitud=ahora, fecha_requerida=requerida,
            observaciones=validar_texto(datos.get('observaciones'), 'Observaciones', 220),
            salida_solicitada=datos.get('salida_solicitada') == '1',
            participantes=tuple(participantes),
        )

    @classmethod
    def desde_detalle(cls, fila: ResumenReserva) -> 'Reserva':
        participantes = fila.get('participantes')
        return cls(
            id_reserva=fila['id_reserva'], dni_persona=fila['dni_persona'], id_recurso=fila['id_recurso'],
            fecha_solicitud=fila['fecha_solicitud'], fecha_requerida=fila['fecha_requerida'],
            estado=EstadoReserva(fila['estado']), tipo_gestion=fila['tipo_gestion'],
            observaciones=fila['observaciones'] or '', salida_solicitada=bool(fila['salida_solicitada']),
            fecha_limite_vencimiento=fila['fecha_limite_vencimiento'], id_bien=fila['id_bien'],
            fecha_preparacion=fila['fecha_preparacion'], id_prestamo_ref=fila['id_prestamo_ref'],
            id_reserva_principal=fila.get('id_reserva_principal'),
            participantes=tuple(json.loads(participantes) if isinstance(participantes, str) else participantes or ()),
        )

    def con_plazo_de_espera(self, limite: datetime) -> 'Reserva':
        return replace(self, fecha_limite_vencimiento=limite)

    @property
    def identificador(self) -> int:
        if self.id_reserva is None:
            raise ValueError('La reserva todavía no está registrada.')
        return self.id_reserva

    def ventana_atencion(self, ahora: datetime) -> VentanaReserva:
        return ventana_atencion_reserva(self.fecha_requerida, self.fecha_limite_vencimiento, ahora)

    def validar_accion_reserva(self, accion: AccionReserva, ahora: datetime) -> None:
        if self.estado not in ESTADOS_POR_ACCION[accion]:
            if accion == 'cancelar':
                raise Conflicto('La reserva ya no se puede cancelar.')
            raise Conflicto('El estado de la reserva no permite esta acción.')
        ventana = self.ventana_atencion(ahora)
        if accion == 'expirar' and ventana != 'VENCIDA':
            raise Conflicto('La reserva solo puede marcarse vencida después de su plazo.')
        if accion in ('preparar', 'entregar') and ventana == 'VENCIDA':
            raise Conflicto('El plazo de la reserva venció.')

    def asignar_bien_para_retiro(self, bien: int, ahora: datetime, limite: datetime) -> 'Reserva':
        self.validar_accion_reserva('preparar', ahora)
        return replace(self, estado=LISTA_PARA_RETIRO, id_bien=bien, fecha_preparacion=ahora,
                       fecha_limite_vencimiento=limite)

    def marcar_atendida_con_prestamo(self, prestamo: int, ahora: datetime) -> 'Reserva':
        self.validar_accion_reserva('entregar', ahora)
        if self.id_bien is None:
            raise Conflicto('El bien asignado no corresponde al recurso reservado.')
        return replace(self, estado=EstadoReserva.ATENDIDA, id_prestamo_ref=prestamo)

    def cerrar_sin_entrega(self, accion: Literal['cancelar', 'rechazar', 'expirar'], ahora: datetime) -> 'Reserva':
        self.validar_accion_reserva(accion, ahora)
        return replace(self, estado=ESTADOS_CIERRE[accion])

    def puede_expirar(self, ahora: datetime) -> bool:
        return self.estado in ESTADOS_PENDIENTES and self.ventana_atencion(ahora) == 'VENCIDA'


def validar_solicitante_y_recurso_para_reserva(
    reserva: Reserva, contexto: DatosParaValidarReserva, comprobar_duplicada: bool = False
) -> PersonaParaPrestamo:
    persona = validar_integrante_de_reserva(contexto)
    if not contexto.existe_recurso:
        raise NoEncontrado('Recurso inexistente.')
    if contexto.permite_salida is None:
        raise ValueError('No hay una política vigente para este recurso y tipo de persona.')
    if reserva.salida_solicitada and not contexto.permite_salida:
        raise ValueError('La política no permite la salida externa.')
    if comprobar_duplicada and contexto.duplicada:
        raise Conflicto('Ya tienes una solicitud o reserva pendiente para este recurso.')
    return persona


def validar_integrante_de_reserva(contexto: DatosParaValidarReserva) -> PersonaParaPrestamo:
    persona = validar_elegibilidad_del_solicitante(contexto.persona)
    if contexto.bloqueado:
        raise Conflicto(f'{persona["nombres"]} {persona["apellidos"]} tiene bienes vencidos o una sanción activa.')
    return persona
