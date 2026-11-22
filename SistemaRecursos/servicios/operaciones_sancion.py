"""Registro y cierre de sanciones en una transacción iniciada por el caso de uso."""

from dominio.gestion_control.incidencia import hay_retraso
from dominio.gestion_control.sancion import (
    ConfiguracionSanciones,
    IOperacionesSancion,
    cambios_por_evaluacion,
    puede_cumplirse,
    validar_contexto_evaluacion,
    validar_evaluacion,
)


def _crear_sancion(op: IOperacionesSancion, detalle, tipo, gravedad, motivo, inicio, documento=None):
    config = ConfiguracionSanciones.desde_datos(op.consultar_configuracion() or {})
    incidencia = op.registrar_incidencia(detalle['id_detalle'], tipo, motivo, inicio)
    datos = dict(
        id_incidencia_ref=incidencia, motivo=motivo, descripcion=motivo, fecha=inicio,
        estado='ACTIVA', fecha_revision=config.fecha_revision_perdida(inicio),
        **config.datos(), **config.medida(gravedad, inicio),
    )
    identificador = op.registrar_sancion(datos)
    op.registrar_historial_estado(
        'SANCION', identificador, None, 'ACTIVA', documento,
        f'Aplicación de sanción {gravedad}: {motivo}'[:255],
    )
    return op.consultar_sancion(identificador, bloquear=True)


def registrar_sancion_por_retraso(op: IOperacionesSancion, detalle, ahora):
    if detalle.get('fecha_regularizacion') or not hay_retraso(detalle, ahora):
        return False
    if op.consultar_sancion_detalle(detalle['id_detalle']):
        return False
    _crear_sancion(
        op, detalle, 'RETRASO', 'LEVE', 'Devolución fuera de plazo', detalle['fecha_limite_devolucion'],
    )
    return True


def registrar_falta(op: IOperacionesSancion, detalle, causa, gravedad, motivo, cuenta, ahora, *, politica=None):
    actual = op.consultar_sancion_detalle(detalle['id_detalle'])
    nota = validar_evaluacion(actual, gravedad, causa, motivo, cuenta)
    validar_contexto_evaluacion(detalle, causa, actual, politica)
    documento = cuenta['dni_persona']
    if actual is None:
        actual = _crear_sancion(op, detalle, causa, gravedad, nota, ahora, documento)
        op.actualizar_incidencia(actual['id_incidencia_ref'], dict(dni_registrador=documento))
    else:
        cambios = cambios_por_evaluacion(actual, gravedad, causa, nota, ahora)
        op.actualizar_sancion(actual['id_sancion'], cambios)
        op.actualizar_incidencia(actual['id_incidencia_ref'], dict(
            tipo=causa, descripcion=nota, estado='EN_REVISION', dni_registrador=documento,
        ))
        op.registrar_historial_estado(
            'SANCION', actual['id_sancion'], actual['gravedad'], gravedad, documento, nota,
        )
        actual = op.consultar_sancion(actual['id_sancion'], bloquear=True)
    if causa in ('CUSTODIA', 'SALIDA_NO_AUTORIZADA') and detalle.get('condicion_devolucion') == 'BUENO':
        aceptar_regularizacion(op, actual, 'VERIFICACION', nota, documento, ahora)
    return actual


def cerrar_sancion(op: IOperacionesSancion, sancion, estado, nota, documento, ahora):
    op.actualizar_sancion(sancion['id_sancion'], dict(
        estado=estado, fecha_levantamiento=ahora, dni_levantamiento=documento,
        justificacion_levantamiento=nota,
    ))
    op.actualizar_incidencia(sancion['id_incidencia_ref'], dict(estado='RESUELTA'))
    op.registrar_historial_estado('SANCION', sancion['id_sancion'], 'ACTIVA', estado, documento, nota)


def cumplir_sancion(op: IOperacionesSancion, sancion, ahora):
    if puede_cumplirse(sancion, ahora):
        cerrar_sancion(op, sancion, 'CUMPLIDA', 'Plazo cumplido y regularización aceptada.', None, ahora)


def aceptar_regularizacion(op: IOperacionesSancion, sancion, tipo, nota, documento, ahora, reposicion=None):
    cambios = dict(
        fecha_regularizacion=ahora, tipo_regularizacion=tipo, observacion_regularizacion=nota,
        dni_regularizacion=documento, id_bien_reposicion=reposicion,
    )
    op.actualizar_sancion(sancion['id_sancion'], cambios)
    op.registrar_historial_estado(
        'SANCION', sancion['id_sancion'], sancion['estado'], sancion['estado'],
        documento, f'Regularización {tipo}: {nota}'[:255],
    )
    sancion.update(cambios)
    cumplir_sancion(op, sancion, ahora)


def regularizar_devolucion(op: IOperacionesSancion, detalle, condicion, documento, ahora):
    sancion = op.consultar_sancion_detalle(detalle['id_detalle'])
    if (sancion and sancion['estado'] == 'ACTIVA' and not sancion['fecha_regularizacion']
            and condicion == 'BUENO' and sancion['tipo'] in ('RETRASO', 'PERDIDA')):
        tipo = 'RECUPERACION' if sancion['tipo'] == 'PERDIDA' else 'DEVOLUCION'
        aceptar_regularizacion(op, sancion, tipo, 'Recepción física en buen estado.', documento, ahora)


def registrar_danio_devolucion(op: IOperacionesSancion, detalle, observacion, cuenta, ahora):
    actual = op.consultar_sancion_detalle(detalle['id_detalle'])
    if not actual or actual['gravedad'] == 'LEVE':
        registrar_falta(op, detalle, 'DANIO', 'GRAVE', observacion, cuenta, ahora)
        return
    # La recepción del bien conserva la gravedad y el plazo de la sanción.
    documento = cuenta['dni_persona']
    op.actualizar_incidencia(actual['id_incidencia_ref'], dict(
        tipo='DANIO', estado='EN_REVISION', descripcion=observacion, dni_registrador=documento,
    ))
    op.actualizar_sancion(actual['id_sancion'], dict(
        motivo=observacion, descripcion=observacion, fecha_regularizacion=None,
        tipo_regularizacion=None, dni_regularizacion=None, observacion_regularizacion=None,
    ))
    op.registrar_historial_estado(
        'SANCION', actual['id_sancion'], actual['gravedad'], actual['gravedad'], documento,
        ('Recepción dañada; se conserva gravedad y plazo. ' + observacion)[:255],
    )
