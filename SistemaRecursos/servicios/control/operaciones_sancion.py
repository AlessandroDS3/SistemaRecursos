"""Registro y cierre de sanciones en una transacción iniciada por el caso de uso."""

from dominio.gestion_control.contratos_control import IOperacionesSancion
from dominio.gestion_control.incidencia import TipoIncidencia
from dominio.gestion_control.sancion import (
    ConfiguracionSanciones, EstadoSancion, FaltaAutomatica,
    calcular_cambios_de_sancion,
    evaluar_danio_nuevo,
    determinar_falta_por_retraso,
    puede_marcarse_sancion_cumplida,
    determinar_regularizacion_por_devolucion,
    validar_falta_en_bien_prestado,
    validar_gravedad_y_motivo_de_sancion,
)


def _crear_sancion_vinculada_a_incidencia(op: IOperacionesSancion, detalle, tipo, gravedad, motivo, inicio, documento=None):
    config = ConfiguracionSanciones.desde_datos(op.consultar_configuracion_sanciones() or {})
    anterior = op.consultar_incidencia_sin_sancion(detalle['id_detalle'], tipo)
    incidencia = anterior['id_incidencia'] if anterior else op.registrar_incidencia(
        detalle['id_detalle'], tipo, motivo, inicio,
    )
    datos = dict(
        id_incidencia_ref=incidencia, motivo=motivo, descripcion=motivo, fecha=inicio,
        estado=EstadoSancion.ACTIVA, fecha_revision=config.calcular_fecha_revision_por_perdida(inicio),
        **config.como_diccionario(), **config.calcular_periodo_por_gravedad(gravedad, inicio),
    )
    identificador = op.registrar_sancion(datos)
    op.registrar_historial_estado(
        'SANCION', identificador, None, EstadoSancion.ACTIVA, documento,
        f'Aplicación de sanción {gravedad}: {motivo}'[:255],
    )
    return op.consultar_sancion(identificador, bloquear=True)


def registrar_sancion_por_retraso(op: IOperacionesSancion, detalle, ahora):
    falta = determinar_falta_por_retraso(detalle, ahora)
    if falta is None or op.consultar_sancion_por_detalle_prestamo(detalle['id_detalle']):
        return False
    _crear_sancion_vinculada_a_incidencia(
        op, detalle, falta.causa, falta.gravedad, falta.motivo, falta.inicio,
    )
    return True


def aplicar_o_reevaluar_sancion(op: IOperacionesSancion, detalle, causa, gravedad, motivo, cuenta, ahora, *, politica=None):
    actual = op.consultar_sancion_por_detalle_prestamo(detalle['id_detalle'])
    if actual and actual['estado'] == EstadoSancion.ANULADA and actual['tipo'] != causa:
        actual = None
    nota = validar_gravedad_y_motivo_de_sancion(actual, gravedad, causa, motivo, cuenta)
    validar_falta_en_bien_prestado(detalle, causa, actual, politica)
    documento = cuenta['dni_persona']
    if actual is None:
        actual = _crear_sancion_vinculada_a_incidencia(op, detalle, causa, gravedad, nota, ahora, documento)
        op.actualizar_incidencia(actual['id_incidencia_ref'], dict(dni_registrador=documento))
    else:
        cambios = calcular_cambios_de_sancion(actual, gravedad, causa, nota, ahora)
        op.actualizar_sancion(actual['id_sancion'], cambios)
        op.actualizar_incidencia(actual['id_incidencia_ref'], dict(
            tipo=causa, descripcion=nota, estado='EN_REVISION', dni_registrador=documento,
        ))
        op.registrar_historial_estado(
            'SANCION', actual['id_sancion'], actual['gravedad'], gravedad, documento, nota,
        )
        actual = op.consultar_sancion(actual['id_sancion'], bloquear=True)
    if causa in ('CUSTODIA', 'SALIDA_NO_AUTORIZADA') and detalle.get('condicion_devolucion') == 'BUENO':
        registrar_regularizacion_sancion(op, actual, 'VERIFICACION', nota, documento, ahora)
    return actual


def registrar_cierre_sancion(op: IOperacionesSancion, sancion, estado: EstadoSancion, nota, documento, ahora):
    op.actualizar_sancion(sancion['id_sancion'], dict(
        estado=estado, fecha_levantamiento=ahora, dni_levantamiento=documento,
        justificacion_levantamiento=nota,
    ))
    op.actualizar_incidencia(sancion['id_incidencia_ref'], dict(estado='RESUELTA'))
    op.registrar_historial_estado('SANCION', sancion['id_sancion'], sancion['estado'], estado, documento, nota)


def marcar_sancion_cumplida_si_corresponde(op: IOperacionesSancion, sancion, ahora):
    if puede_marcarse_sancion_cumplida(sancion, ahora):
        registrar_cierre_sancion(op, sancion, EstadoSancion.CUMPLIDA, 'Plazo cumplido y regularización aceptada.', None, ahora)


def registrar_regularizacion_sancion(op: IOperacionesSancion, sancion, tipo, nota, documento, ahora, reposicion=None):
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
    marcar_sancion_cumplida_si_corresponde(op, sancion, ahora)


def regularizar_sancion_tras_devolucion(op: IOperacionesSancion, detalle, condicion, documento, ahora):
    sancion = op.consultar_sancion_por_detalle_prestamo(detalle['id_detalle'])
    if sancion is None:
        return
    tipo = determinar_regularizacion_por_devolucion(sancion, condicion)
    if tipo is not None:
        registrar_regularizacion_sancion(op, sancion, tipo, 'Recepción física en buen estado.', documento, ahora)


def registrar_sancion_por_danio_en_devolucion(op: IOperacionesSancion, detalle, observacion, cuenta, ahora):
    actual = op.consultar_sancion_por_detalle_prestamo(detalle['id_detalle'])
    decision = evaluar_danio_nuevo(actual, observacion, ahora)
    if isinstance(decision, FaltaAutomatica):
        aplicar_o_reevaluar_sancion(op, detalle, decision.causa, decision.gravedad, decision.motivo, cuenta, decision.inicio)
        return
    if decision is None or actual is None:
        return
    # La recepción del bien conserva la gravedad y el plazo de la sanción.
    documento = cuenta['dni_persona']
    op.actualizar_incidencia(actual['id_incidencia_ref'], dict(
        tipo=TipoIncidencia.DANIO, estado='EN_REVISION', descripcion=observacion, dni_registrador=documento,
    ))
    op.actualizar_sancion(actual['id_sancion'], dict(
        motivo=observacion, descripcion=observacion, fecha_regularizacion=None,
        tipo_regularizacion=None, dni_regularizacion=None, observacion_regularizacion=None,
    ))
    op.registrar_historial_estado(
        'SANCION', actual['id_sancion'], actual['gravedad'], actual['gravedad'], documento,
        ('Recepción dañada; se conserva gravedad y plazo. ' + observacion)[:255],
    )
