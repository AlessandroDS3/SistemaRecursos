"""Reglas puras de entrega y cálculo de estado. Los datos se cargan bajo bloqueo."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TypedDict

from dominio.compartido.codigos import Codigo
from dominio.compartido.validacion import (
    Conflicto,
    NoEncontrado,
    validar_dni,
    validar_lista_de_ids_de_bienes,
    validar_texto,
)
from dominio.gestion_personas_usuarios.persona import (
    PersonaParaPrestamo,
    validar_elegibilidad_del_solicitante,
)
from dominio.gestion_control.politica_prestamo import HorarioAtencion, PoliticaPrestamo
from dominio.gestion_recursos.bien_material import EstadoBien


class TipoPrestamo(Codigo):
    INDIVIDUAL = 'INDIVIDUAL'
    GRUPAL = 'GRUPAL'


class EstadoPrestamo(Codigo):
    ACTIVO = 'ACTIVO'
    VENCIDO = 'VENCIDO'
    DEVUELTO = 'DEVUELTO'
    REGULARIZADO = 'REGULARIZADO'
    PARCIALMENTE_DEVUELTO = 'PARCIALMENTE_DEVUELTO'

ESTADOS_PRESTAMO: dict[str, str] = {
    EstadoPrestamo.ACTIVO: 'Activos',
    EstadoPrestamo.VENCIDO: 'Vencidos',
    EstadoPrestamo.DEVUELTO: 'Devueltos',
    EstadoPrestamo.REGULARIZADO: 'Regularizados por reposición',
    EstadoPrestamo.PARCIALMENTE_DEVUELTO: 'Parcialmente devueltos',
}
FILTROS_ESTADO_PRESTAMO = {
    **ESTADOS_PRESTAMO,
    'PENDIENTES': 'Con bienes pendientes',
    'PERDIDOS': 'Con bienes perdidos pendientes',
}


@dataclass(frozen=True)
class CupoArticulos:
    limite: int | None
    pendientes: int
    reservas: int


@dataclass(frozen=True)
class SolicitanteEntrega:
    persona: PersonaParaPrestamo
    cupo: CupoArticulos


@dataclass(frozen=True)
class BienParaEntrega:
    id_bien: int
    estado: EstadoBien
    id_categoria: int


@dataclass(frozen=True)
class DetalleEntregaPlanificado:
    id_bien: int
    id_politica: int
    fecha_limite_devolucion: datetime
    estado_anterior: EstadoBien


@dataclass(frozen=True, kw_only=True)
class DatosParaValidarPrestamo:
    solicitantes: dict[str, SolicitanteEntrega]
    hay_sancion_activa: bool
    hay_bienes_vencidos: bool
    bienes: list[BienParaEntrega]
    hay_entregas_pendientes: bool
    hay_reservas_con_prioridad: bool
    politicas: dict[int, PoliticaPrestamo]
    horario: HorarioAtencion | None
    ahora: datetime


def validar_cupo_articulos(persona: PersonaParaPrestamo, cupo: CupoArticulos, nuevos: int = 1) -> None:
    if cupo.limite is None:
        tipo = (persona['tipo'] or 'desconocido').lower()
        raise ValueError(f'Configura el límite de bienes para {tipo}.')
    if cupo.pendientes + cupo.reservas + nuevos <= cupo.limite:
        return
    nombre = f'{persona["nombres"]} {persona["apellidos"]}'
    ocupados = f'{cupo.pendientes} bienes pendientes'
    if cupo.reservas:
        ocupados += f' y {cupo.reservas} bienes en reservas activas'
    raise Conflicto(f'{nombre} tiene {ocupados}. Esta operación superaría su límite de {cupo.limite}.')


def validar_integrantes(
    titular: str, participantes: list[str] | tuple[str, ...], tipo: str,
) -> list[str]:
    if not isinstance(participantes, (list, tuple)) or len(participantes) > 100:
        raise ValueError('Participantes inválidos.')
    documentos = [validar_dni(d) for d in participantes]
    if len(set(documentos)) != len(documentos) or titular in documentos:
        raise ValueError('No repitas al responsable ni a los integrantes.')
    if tipo not in tuple(TipoPrestamo) or (tipo == TipoPrestamo.GRUPAL) != bool(documentos):
        raise ValueError('Agrega integrantes para la modalidad grupal o elige individual.')
    return documentos


@dataclass(kw_only=True)
class SolicitudPrestamo:
    dni_persona: str
    dni_encargado: str
    bienes: list[int]
    participantes: list[str] = field(default_factory=list)
    tipo_prestamo: TipoPrestamo = TipoPrestamo.INDIVIDUAL
    salida_solicitada: bool = False
    observaciones: str = ''

    def __post_init__(self):
        self.dni_persona, self.dni_encargado = validar_dni(self.dni_persona), validar_dni(self.dni_encargado)
        self.bienes = validar_lista_de_ids_de_bienes(self.bienes)
        self.participantes = validar_integrantes(self.dni_persona, self.participantes, self.tipo_prestamo)
        self.observaciones = validar_texto(self.observaciones, 'Observaciones', 220)
        self.tipo_prestamo = TipoPrestamo(self.tipo_prestamo)

    @property
    def solicitantes(self) -> list[str]:
        return [self.dni_persona, *self.participantes]

    @property
    def observaciones_registro(self) -> str:
        uso = (
            'Salida externa autorizada. '
            if self.salida_solicitada
            else 'Uso dentro de la institución. '
        )
        return uso + self.observaciones

    def validar_entrega_y_calcular_plazos(
        self, datos: DatosParaValidarPrestamo, bienes_reservados: frozenset[int] = frozenset(),
    ) -> list[DetalleEntregaPlanificado]:
        for documento in self.solicitantes:
            solicitante = datos.solicitantes.get(documento)
            validar_elegibilidad_del_solicitante(solicitante.persona if solicitante else None)
        if datos.hay_sancion_activa:
            raise Conflicto('El solicitante o un integrante tiene una sanción activa.')
        if datos.hay_bienes_vencidos:
            raise Conflicto('El solicitante o un integrante tiene bienes vencidos pendientes.')
        for documento in self.solicitantes:
            solicitante = datos.solicitantes[documento]
            validar_cupo_articulos(solicitante.persona, solicitante.cupo, len(self.bienes))
        if {bien.id_bien for bien in datos.bienes} != set(self.bienes):
            raise NoEncontrado('Uno de los bienes no existe.')
        if datos.hay_entregas_pendientes:
            raise Conflicto('Uno de los bienes ya tiene una entrega pendiente.')
        if datos.hay_reservas_con_prioridad:
            raise Conflicto('Atiende primero las reservas en espera de este recurso.')
        horario = datos.horario
        if horario is None:
            raise ValueError('Configura el horario de atención.')
        horario.obtener_cierre_si_hay_atencion(datos.ahora)
        return [self._validar_bien_y_calcular_plazo(bien, datos, bienes_reservados, horario) for bien in datos.bienes]

    def _validar_bien_y_calcular_plazo(
        self, bien: BienParaEntrega, datos: DatosParaValidarPrestamo,
        bienes_reservados: frozenset[int], horario: HorarioAtencion,
    ) -> DetalleEntregaPlanificado:
        esperado = EstadoBien.RESERVADO if bien.id_bien in bienes_reservados else EstadoBien.DISPONIBLE
        if bien.estado is not esperado:
            raise Conflicto('Uno de los bienes dejó de estar disponible.')
        politica = datos.politicas.get(bien.id_categoria)
        if politica is None or politica.id_politica is None:
            raise ValueError('Falta una política para una categoría seleccionada.')
        if self.salida_solicitada and not politica.permite_salida:
            raise ValueError('La política de un bien no permite la salida externa.')
        return DetalleEntregaPlanificado(
            bien.id_bien, politica.id_politica, politica.calcular_fecha_limite_devolucion(datos.ahora, horario), bien.estado,
        )


class PlazoDetallePrestamo(TypedDict, total=False):
    fecha_devolucion: datetime | None
    fecha_regularizacion: datetime | None
    fecha_limite_devolucion: datetime


def calcular_estado_prestamo(detalles: list[PlazoDetallePrestamo], ahora: datetime) -> EstadoPrestamo:
    pendientes = [d for d in detalles if d['fecha_devolucion'] is None and not d.get('fecha_regularizacion')]
    if not pendientes:
        return EstadoPrestamo.REGULARIZADO if any(d.get('fecha_regularizacion') for d in detalles) else EstadoPrestamo.DEVUELTO
    if any(d['fecha_limite_devolucion'] < ahora for d in pendientes):
        return EstadoPrestamo.VENCIDO
    return EstadoPrestamo.PARCIALMENTE_DEVUELTO if len(pendientes) < len(detalles) else EstadoPrestamo.ACTIVO
