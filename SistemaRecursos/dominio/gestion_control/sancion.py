"""Reglas de sanciones; no conocen HTTP, SQL ni el reloj del sistema."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Literal, TypedDict

from dominio.compartido.codigos import Codigo
from dominio.compartido.validacion import Conflicto, LIMA, validar_entero, validar_texto
from dominio.gestion_control.incidencia import TipoIncidencia, hay_danio_nuevo, hay_retraso
from dominio.gestion_recursos.bien_material import CondicionBien

if TYPE_CHECKING:
    from dominio.gestion_prestamos.prestamo import PlazoDetallePrestamo

GRAVEDADES = ('LEVE', 'GRAVE', 'MUY_GRAVE')
CAUSAS_GRAVES = ('DANIO', 'PERDIDA', 'SALIDA_NO_AUTORIZADA', 'CUSTODIA')


class EstadoSancion(Codigo):
    ACTIVA = 'ACTIVA'
    CUMPLIDA = 'CUMPLIDA'
    LEVANTADA = 'LEVANTADA'
    ANULADA = 'ANULADA'


ESTADOS_SANCION = tuple(EstadoSancion)


class VigenciaSancion(TypedDict, total=False):
    estado: str
    gravedad: str
    fecha_fin: datetime | None
    fecha_regularizacion: datetime | None


class SancionPorIncidencia(VigenciaSancion):
    tipo: str


@dataclass(frozen=True)
class FaltaAutomatica:
    causa: TipoIncidencia
    gravedad: Literal['LEVE', 'GRAVE']
    motivo: str
    inicio: datetime


def determinar_falta_por_retraso(detalle: PlazoDetallePrestamo, ahora: datetime) -> FaltaAutomatica | None:
    if detalle.get('fecha_regularizacion') or not hay_retraso(detalle, ahora):
        return None
    return FaltaAutomatica(TipoIncidencia.RETRASO, 'LEVE', 'Devolución fuera de plazo', detalle['fecha_limite_devolucion'])


def evaluar_danio_nuevo(
    sancion: SancionPorIncidencia | None, observacion: str, ahora: datetime,
) -> FaltaAutomatica | Literal['CONSERVAR_GRAVEDAD_Y_PLAZO'] | None:
    if sancion is not None:
        if sancion['estado'] == EstadoSancion.ANULADA:
            if sancion['tipo'] == TipoIncidencia.DANIO:
                return None
        elif sancion['gravedad'] != 'LEVE':
            return 'CONSERVAR_GRAVEDAD_Y_PLAZO'
    return FaltaAutomatica(TipoIncidencia.DANIO, 'GRAVE', observacion, ahora)


def determinar_regularizacion_por_devolucion(
    sancion: SancionPorIncidencia, condicion: str,
) -> Literal['DEVOLUCION', 'RECUPERACION'] | None:
    if (sancion['estado'] != EstadoSancion.ACTIVA or sancion_tiene_regularizacion(sancion)
            or condicion != CondicionBien.BUENO):
        return None
    if sancion['tipo'] == TipoIncidencia.RETRASO:
        return 'DEVOLUCION'
    if sancion['tipo'] == TipoIncidencia.PERDIDA:
        return 'RECUPERACION'
    return None


@dataclass(frozen=True, kw_only=True)
class ConfiguracionSanciones:
    dias_leve: int = 14
    dias_grave: int = 180
    dias_espera_perdida: int = 7

    def __post_init__(self):
        for campo, maximo, minimo in (
            ('dias_leve', 3650, 1), ('dias_grave', 3650, 1),
            ('dias_espera_perdida', 365, 1),
        ):
            object.__setattr__(self, campo, validar_entero(
                getattr(self, campo), campo.replace('_', ' ').capitalize(),
                minimo=minimo, maximo=maximo,
            ))

    @classmethod
    def desde_datos(cls, datos):
        return cls(**{k: datos[k] for k in cls.__dataclass_fields__ if k in datos})

    def como_diccionario(self):
        return asdict(self)

    def calcular_periodo_por_gravedad(self, gravedad, inicio):
        if gravedad not in GRAVEDADES:
            raise ValueError('Gravedad de sanción inválida.')
        dias = self.dias_leve if gravedad == 'LEVE' else self.dias_grave
        return dict(
            gravedad=gravedad, fecha_inicio_nivel=inicio,
            fecha_fin=None if gravedad == 'MUY_GRAVE' else inicio + timedelta(days=dias),
        )

    def calcular_fecha_revision_por_perdida(self, inicio):
        return inicio + timedelta(days=self.dias_leve + self.dias_espera_perdida)


def exigir_administrador(cuenta):
    if cuenta['rol'] != 'ADMINISTRADOR':
        raise PermissionError('Esta operación requiere un administrador.')


def sancion_tiene_regularizacion(sancion: VigenciaSancion) -> bool:
    return sancion.get('fecha_regularizacion') is not None


def puede_marcarse_sancion_cumplida(sancion: VigenciaSancion, ahora: datetime) -> bool:
    fecha_fin = sancion.get('fecha_fin')
    return (
        sancion['estado'] == EstadoSancion.ACTIVA
        and sancion['gravedad'] != 'MUY_GRAVE'
        and fecha_fin is not None
        and fecha_fin <= ahora
        and sancion_tiene_regularizacion(sancion)
    )


def validar_levantamiento_de_sancion(sancion, justificacion, ahora, cuenta):
    if sancion['estado'] != EstadoSancion.ACTIVA:
        raise Conflicto('La sanción ya no está activa.')
    nota = validar_texto(justificacion, 'Justificación', 255, True)
    if not sancion_tiene_regularizacion(sancion):
        raise Conflicto('Primero debe aceptarse la devolución, reparación o reposición.')
    if sancion['gravedad'] == 'MUY_GRAVE':
        exigir_administrador(cuenta)
    elif not puede_marcarse_sancion_cumplida(sancion, ahora):
        if sancion['gravedad'] != 'LEVE':
            raise Conflicto('La sanción grave debe cumplir su duración.')
    return nota


def validar_gravedad_y_motivo_de_sancion(sancion, gravedad, causa, motivo, cuenta):
    if gravedad not in ('GRAVE', 'MUY_GRAVE') or causa not in CAUSAS_GRAVES:
        raise ValueError('Selecciona una gravedad y una causa válidas.')
    if sancion and sancion['estado'] != EstadoSancion.ACTIVA:
        raise Conflicto('La sanción ya está cerrada y no puede volver a evaluarse.')
    if sancion and GRAVEDADES.index(gravedad) < GRAVEDADES.index(sancion['gravedad']):
        raise Conflicto('No se puede reducir la gravedad de una sanción.')
    if gravedad == 'MUY_GRAVE' or (sancion and sancion['gravedad'] == 'MUY_GRAVE'):
        exigir_administrador(cuenta)
    return validar_texto(motivo, 'Motivo de evaluación', 255, True)


def calcular_cambios_de_sancion(sancion, gravedad, causa, motivo, ahora):
    if sancion['gravedad'] == gravedad and sancion['tipo'] == causa:
        raise Conflicto('Este hecho ya está sancionado; no se reinicia su plazo.')
    cambios = dict(
        motivo=motivo, descripcion=motivo, estado=EstadoSancion.ACTIVA,
        fecha_levantamiento=None, dni_levantamiento=None, justificacion_levantamiento=None,
    )
    if sancion['tipo'] != causa:
        cambios.update(
            fecha_regularizacion=None, tipo_regularizacion=None, dni_regularizacion=None,
            observacion_regularizacion=None, id_bien_reposicion=None,
        )
    if sancion['gravedad'] != gravedad:
        cambios.update(ConfiguracionSanciones.desde_datos(sancion).calcular_periodo_por_gravedad(gravedad, ahora))
    return cambios


def validar_falta_en_bien_prestado(detalle, causa, sancion=None, politica=None):
    if causa == TipoIncidencia.DANIO and not hay_danio_nuevo(
        detalle.get('condicion_entrega'), detalle.get('condicion_devolucion'),
    ):
        raise Conflicto('Debe existir una recepción con daño nuevo; el daño preexistente no se sanciona.')
    if causa == 'PERDIDA' and not (sancion and sancion['tipo'] == 'PERDIDA'):
        if detalle.get('fecha_devolucion') or detalle.get('fecha_regularizacion'):
            raise Conflicto('No puede confirmarse la pérdida de un bien ya devuelto o repuesto.')
    if causa in ('SALIDA_NO_AUTORIZADA', 'CUSTODIA') and (politica is None or politica['permite_salida']):
        raise Conflicto('La política aplicada al bien permite su salida; revisa la causa.')


def validar_aceptacion_de_reparacion(detalle, bien):
    if not detalle['fecha_devolucion']:
        raise Conflicto('Registra primero la recepción física del bien.')
    if bien['estado'] not in ('DANADO', 'MANTENIMIENTO', 'DISPONIBLE'):
        raise Conflicto('El estado actual del bien impide aceptar su reparación.')


def validar_devolucion_para_verificacion(detalle):
    if not detalle['fecha_devolucion'] or detalle['condicion_devolucion'] != 'BUENO':
        raise Conflicto('Registra la devolución en buen estado antes de aceptar la verificación.')


def validar_regularizacion_sancion(sancion, tipo, observacion):
    if sancion['estado'] != EstadoSancion.ACTIVA or sancion_tiene_regularizacion(sancion):
        raise Conflicto('El incidente ya fue regularizado o la sanción ya no está activa.')
    permitidos = {
        'PERDIDA': ('RECUPERACION', 'REPOSICION'),
        'DANIO': ('REPARACION', 'REPOSICION'),
        'SALIDA_NO_AUTORIZADA': ('VERIFICACION',),
        'CUSTODIA': ('VERIFICACION',), 'RETRASO': (),
    }
    if tipo not in permitidos[sancion['tipo']]:
        raise ValueError('La forma de regularización no corresponde a la causa del incidente.')
    return validar_texto(observacion, 'Observación de regularización', 255, True)


def calcular_alertas_de_sancion(sancion, ahora):
    pendiente = not sancion.get('fecha_devolucion') and not sancion.get('fecha_cierre_regularizacion')
    fecha_revision = sancion.get('fecha_revision')
    fecha_fin = sancion.get('fecha_fin')
    limite_local = sancion['fecha_limite_devolucion'].replace(tzinfo=timezone.utc).astimezone(LIMA)
    recepcion_o_ahora = sancion.get('fecha_devolucion') or ahora
    revision_local = recepcion_o_ahora.replace(tzinfo=timezone.utc).astimezone(LIMA)
    return dict(
        posible_perdida=(sancion['estado'] == 'ACTIVA' and sancion['gravedad'] == 'LEVE'
                         and pendiente and fecha_revision is not None and fecha_revision <= ahora),
        revisar_custodia=(sancion['estado'] == 'ACTIVA' and not sancion.get('fecha_cierre_regularizacion')
                         and not sancion.get('permite_salida', True)
                         and sancion.get('tipo') not in ('CUSTODIA', 'SALIDA_NO_AUTORIZADA')
                         and limite_local.date() < revision_local.date()),
        revision_administrador=(sancion['estado'] == 'ACTIVA' and sancion['gravedad'] == 'GRAVE'
                               and not sancion_tiene_regularizacion(sancion)
                               and fecha_fin is not None and fecha_fin <= ahora),
    )
