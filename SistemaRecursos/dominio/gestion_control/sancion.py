"""Reglas de sanciones; no conocen HTTP, SQL ni el reloj del sistema."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import timedelta, timezone

from dominio.compartido.validacion import Conflicto, LIMA, entero, texto

GRAVEDADES = ('LEVE', 'GRAVE', 'MUY_GRAVE')
CAUSAS_GRAVES = ('DANIO', 'PERDIDA', 'SALIDA_NO_AUTORIZADA', 'CUSTODIA')
ESTADOS_SANCION = ('ACTIVA', 'CUMPLIDA', 'LEVANTADA', 'ANULADA')


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
            object.__setattr__(self, campo, entero(
                getattr(self, campo), campo.replace('_', ' ').capitalize(),
                minimo=minimo, maximo=maximo,
            ))

    @classmethod
    def desde_datos(cls, datos):
        return cls(**{k: datos[k] for k in cls.__dataclass_fields__ if k in datos})

    def datos(self):
        return asdict(self)

    def medida(self, gravedad, inicio):
        if gravedad not in GRAVEDADES:
            raise ValueError('Gravedad de sanción inválida.')
        dias = self.dias_leve if gravedad == 'LEVE' else self.dias_grave
        return dict(
            gravedad=gravedad, fecha_inicio_nivel=inicio,
            fecha_fin=None if gravedad == 'MUY_GRAVE' else inicio + timedelta(days=dias),
        )

    def fecha_revision_perdida(self, inicio):
        return inicio + timedelta(days=self.dias_leve + self.dias_espera_perdida)


def exigir_administrador(cuenta):
    if cuenta['rol'] != 'ADMINISTRADOR':
        raise PermissionError('Esta operación requiere un administrador.')


def esta_regularizado(sancion):
    return sancion.get('fecha_regularizacion') is not None


def puede_cumplirse(sancion, ahora):
    return (
        sancion['estado'] == 'ACTIVA'
        and sancion['gravedad'] != 'MUY_GRAVE'
        and sancion.get('fecha_fin') is not None
        and sancion['fecha_fin'] <= ahora
        and esta_regularizado(sancion)
    )


def validar_levantamiento(sancion, justificacion, ahora, cuenta):
    if sancion['estado'] != 'ACTIVA':
        raise Conflicto('La sanción ya no está activa.')
    nota = texto(justificacion, 'Justificación', 255, True)
    if not esta_regularizado(sancion):
        raise Conflicto('Primero debe aceptarse la devolución, reparación o reposición.')
    if sancion['gravedad'] == 'MUY_GRAVE':
        exigir_administrador(cuenta)
    elif not puede_cumplirse(sancion, ahora):
        if sancion['gravedad'] != 'LEVE':
            raise Conflicto('La sanción grave debe cumplir su duración.')
    return nota


def validar_evaluacion(sancion, gravedad, causa, motivo, cuenta):
    if gravedad not in ('GRAVE', 'MUY_GRAVE') or causa not in CAUSAS_GRAVES:
        raise ValueError('Selecciona una gravedad y una causa válidas.')
    if sancion and sancion['estado'] != 'ACTIVA':
        raise Conflicto('La sanción ya está cerrada y no puede volver a evaluarse.')
    if sancion and GRAVEDADES.index(gravedad) < GRAVEDADES.index(sancion['gravedad']):
        raise Conflicto('No se puede reducir la gravedad de una sanción.')
    if gravedad == 'MUY_GRAVE' or (sancion and sancion['gravedad'] == 'MUY_GRAVE'):
        exigir_administrador(cuenta)
    return texto(motivo, 'Motivo de evaluación', 255, True)


def cambios_por_evaluacion(sancion, gravedad, causa, motivo, ahora):
    if sancion['gravedad'] == gravedad and sancion['tipo'] == causa:
        raise Conflicto('Este hecho ya está sancionado; no se reinicia su plazo.')
    cambios = dict(
        motivo=motivo, descripcion=motivo, estado='ACTIVA',
        fecha_levantamiento=None, dni_levantamiento=None, justificacion_levantamiento=None,
    )
    if sancion['tipo'] != causa:
        cambios.update(
            fecha_regularizacion=None, tipo_regularizacion=None, dni_regularizacion=None,
            observacion_regularizacion=None, id_bien_reposicion=None,
        )
    if sancion['gravedad'] != gravedad:
        cambios.update(ConfiguracionSanciones.desde_datos(sancion).medida(gravedad, ahora))
    return cambios


def validar_contexto_evaluacion(detalle, causa, sancion=None, politica=None):
    if causa == 'DANIO' and (
        detalle.get('condicion_devolucion') != 'DANADO' or detalle.get('condicion_entrega') != 'BUENO'
    ):
        raise Conflicto('Debe existir una recepción con daño nuevo; el daño preexistente no se sanciona.')
    if causa == 'PERDIDA' and not (sancion and sancion['tipo'] == 'PERDIDA'):
        if detalle.get('fecha_devolucion') or detalle.get('fecha_regularizacion'):
            raise Conflicto('No puede confirmarse la pérdida de un bien ya devuelto o repuesto.')
    if causa in ('SALIDA_NO_AUTORIZADA', 'CUSTODIA') and (politica is None or politica['permite_salida']):
        raise Conflicto('La política aplicada al bien permite su salida; revisa la causa.')


def validar_reparacion(detalle, bien):
    if not detalle['fecha_devolucion']:
        raise Conflicto('Registra primero la recepción física del bien.')
    if bien['estado'] not in ('DANADO', 'MANTENIMIENTO', 'DISPONIBLE'):
        raise Conflicto('El estado actual del bien impide aceptar su reparación.')


def validar_verificacion(detalle):
    if not detalle['fecha_devolucion'] or detalle['condicion_devolucion'] != 'BUENO':
        raise Conflicto('Registra la devolución en buen estado antes de aceptar la verificación.')


def validar_regularizacion(sancion, tipo, observacion):
    if sancion['estado'] != 'ACTIVA' or esta_regularizado(sancion):
        raise Conflicto('El incidente ya fue regularizado o la sanción ya no está activa.')
    permitidos = {
        'PERDIDA': ('RECUPERACION', 'REPOSICION'),
        'DANIO': ('REPARACION', 'REPOSICION'),
        'SALIDA_NO_AUTORIZADA': ('VERIFICACION',),
        'CUSTODIA': ('VERIFICACION',), 'RETRASO': (),
    }
    if tipo not in permitidos[sancion['tipo']]:
        raise ValueError('La forma de regularización no corresponde a la causa del incidente.')
    return texto(observacion, 'Observación de regularización', 255, True)


def alertas_revision(sancion, ahora):
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
                               and not esta_regularizado(sancion)
                               and fecha_fin is not None and fecha_fin <= ahora),
    )
