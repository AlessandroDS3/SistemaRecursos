"""Reglas puras de entrega y cálculo de estado. Los datos se cargan bajo bloqueo."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TypedDict

from dominio.compartido.validacion import Conflicto, NoEncontrado, dni, ids, texto
from dominio.gestion_personas_usuarios.persona import validar_elegibilidad
from dominio.gestion_control.politica_prestamo import HorarioAtencion, PoliticaPrestamo

ESTADOS_PRESTAMO = {
    'ACTIVO': 'Activos',
    'VENCIDO': 'Vencidos',
    'DEVUELTO': 'Devueltos',
    'REGULARIZADO': 'Regularizados por reposición',
    'PARCIALMENTE_DEVUELTO': 'Parcialmente devueltos',
}
FILTROS_ESTADO_PRESTAMO = {
    **ESTADOS_PRESTAMO,
    'PENDIENTES': 'Con bienes pendientes',
    'PERDIDOS': 'Con bienes perdidos pendientes',
}


class ContextoEntrega(TypedDict):
    personas: dict[str, dict]
    sancion: bool
    vencido: bool
    limites_por_persona: dict[str, int | None]
    pendientes_por_persona: dict[str, int]
    reservas_por_persona: dict[str, int]
    bienes: list[dict]
    entregas_pendientes: bool
    cola_prioritaria: bool
    politicas: dict[int, dict]
    horario: HorarioAtencion | None
    ahora: datetime


def validar_cupo_articulos(persona, limite, pendientes, reservas, nuevos=1):
    if limite is None:
        raise ValueError(f'Configura el límite de artículos para el tipo {persona["tipo"].lower()}.')
    if pendientes + reservas + nuevos <= limite:
        return
    nombre = f'{persona["nombres"]} {persona["apellidos"]}'
    ocupados = f'{pendientes} bienes pendientes'
    if reservas:
        ocupados += f' y {reservas} reservas activas'
    raise Conflicto(f'{nombre} tiene {ocupados}. Esta operación superaría su límite de {limite}.')


@dataclass(kw_only=True)
class SolicitudPrestamo:
    dni_persona: str
    dni_encargado: str
    bienes: list[int]
    participantes: list[str] = field(default_factory=list)
    tipo_prestamo: str = 'INDIVIDUAL'
    salida_solicitada: bool = False
    observaciones: str = ''

    def __post_init__(self):
        self.dni_persona, self.dni_encargado = dni(self.dni_persona), dni(self.dni_encargado)
        self.bienes = ids(self.bienes)
        if not isinstance(self.participantes, (list, tuple)) or len(self.participantes) > 100:
            raise ValueError('Participantes inválidos.')
        self.participantes = [dni(d) for d in self.participantes]
        if (
            len(set(self.participantes)) != len(self.participantes)
            or self.dni_persona in self.participantes
        ):
            raise ValueError('No repitas al responsable ni a los integrantes.')
        if self.tipo_prestamo not in ('INDIVIDUAL', 'GRUPAL') or (
            (self.tipo_prestamo == 'GRUPAL') != bool(self.participantes)
        ):
            raise ValueError(
                'El préstamo grupal requiere otros integrantes; el individual no los admite.'
            )
        self.observaciones = texto(self.observaciones, 'Observaciones', 220)

    @property
    def solicitantes(self):
        return [self.dni_persona, *self.participantes]

    @property
    def observaciones_registro(self):
        uso = (
            'Salida externa autorizada. '
            if self.salida_solicitada
            else 'Uso dentro de la institución. '
        )
        return uso + self.observaciones

    def planificar(self, contexto: ContextoEntrega, bien_reservado=None):
        for documento in self.solicitantes:
            validar_elegibilidad(contexto['personas'].get(documento))
        if contexto['sancion']:
            raise Conflicto('El solicitante o un integrante tiene una sanción activa.')
        if contexto['vencido']:
            raise Conflicto('El solicitante o un integrante tiene bienes vencidos pendientes.')
        for documento in self.solicitantes:
            validar_cupo_articulos(
                contexto['personas'][documento], contexto['limites_por_persona'][documento],
                contexto['pendientes_por_persona'][documento], contexto['reservas_por_persona'][documento],
                len(self.bienes),
            )
        bienes = contexto['bienes']
        if {b['id_bien'] for b in bienes} != set(self.bienes):
            raise NoEncontrado('Uno de los bienes no existe.')
        if contexto['entregas_pendientes']:
            raise Conflicto('Uno de los bienes ya tiene una entrega pendiente.')
        if contexto['cola_prioritaria']:
            raise Conflicto('Atiende primero las reservas en espera de este recurso.')
        horario = contexto['horario']
        if horario is None:
            raise ValueError('Configura el horario de atención.')
        horario.cierre(contexto['ahora'])
        return [self._planificar_bien(bien, contexto, bien_reservado) for bien in bienes]

    def _planificar_bien(self, bien, contexto, bien_reservado):
        esperado = 'RESERVADO' if bien['id_bien'] == bien_reservado else 'DISPONIBLE'
        if bien['estado'] != esperado:
            raise Conflicto('Uno de los bienes dejó de estar disponible.')
        fila = contexto['politicas'].get(bien['id_categoria'])
        if fila is None:
            raise ValueError('Falta una política para una categoría seleccionada.')
        politica = PoliticaPrestamo.desde_datos(fila)
        if self.salida_solicitada and not politica.permite_salida:
            raise ValueError('La política de un bien no permite la salida externa.')
        return {
            'id_bien': bien['id_bien'],
            'id_politica': politica.id_politica,
            'fecha_limite_devolucion': politica.vencimiento(contexto['ahora'], contexto['horario']),
            'condicion_entrega': 'BUENO',
            'estado_anterior': bien['estado'],
        }


def estado_prestamo(detalles, ahora):
    pendientes = [d for d in detalles if d['fecha_devolucion'] is None and not d.get('fecha_regularizacion')]
    if not pendientes:
        return 'REGULARIZADO' if any(d.get('fecha_regularizacion') for d in detalles) else 'DEVUELTO'
    if any(d['fecha_limite_devolucion'] < ahora for d in pendientes):
        return 'VENCIDO'
    return 'PARCIALMENTE_DEVUELTO' if len(pendientes) < len(detalles) else 'ACTIVO'
