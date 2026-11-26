"""Construye una cronología a partir de hechos guardados, sin inferir responsables."""

import json
import re
from datetime import datetime, timezone

from dominio.compartido.validacion import LIMA
from dominio.gestion_prestamos.ampliacion_prestamo import EVENTO_AMPLIACION_PLAZO
from servicios.reportes.catalogo_reportes import COLUMNAS_HISTORIAL

AMPLIACION_HISTORICA = re.compile(r'^(?:Solicitud #[0-9]+ aprobada\.\s+)?Detalle #([0-9]+):')
CIERRES_SANCION = {
    'LEVANTADA': 'Levantamiento de sanción',
    'CUMPLIDA': 'Cumplimiento de sanción',
    'ANULADA': 'Anulación de sanción',
}


def _identificar_detalle_de_ampliacion(movimiento: dict) -> tuple[bool, int | None]:
    datos = movimiento.get('datos')
    if isinstance(datos, str):
        datos = json.loads(datos)
    if isinstance(datos, dict) and datos.get('evento') == EVENTO_AMPLIACION_PLAZO:
        detalle_id = datos.get('id_detalle')
        return True, detalle_id if type(detalle_id) is int else None
    antigua = AMPLIACION_HISTORICA.match(movimiento.get('observacion') or '')
    return (True, int(antigua[1])) if antigua else (False, None)


def _etiquetar_cierre_de_sancion(movimiento: dict) -> str | None:
    if movimiento['estado_anterior'] != movimiento['estado_nuevo']:
        return CIERRES_SANCION.get(movimiento['estado_nuevo'])
    return None


def construir_cronologia_historial(datos):
    filas = []
    por_prestamo = {}
    for detalle in datos['prestamos']:
        por_prestamo.setdefault(detalle['id_prestamo'], []).append(detalle)

    def agregar_evento_a_cronologia(origen, fecha, evento, referencia, **valores):
        fila = {c.nombre: None for c in COLUMNAS_HISTORIAL}
        fila.update({k: v for k, v in origen.items() if k in fila})
        fila.update(fecha=fecha, evento=evento, referencia=referencia)
        fila.update(valores)
        if fila['id_prestamo'] in por_prestamo:
            detalles = por_prestamo[fila['id_prestamo']]
            fila['integrantes'] = detalles[0].get('integrantes', '')
            fila['estado_prestamo'] = detalles[0]['estado_prestamo']
        anterior, nuevo = fila['estado_anterior'], fila['estado_nuevo']
        fila['transicion'] = f'{anterior or "—"} -> {nuevo}' if nuevo else ''
        fila['registrador'] = fila['registrador'] or 'No registrado'
        filas.append(fila)

    for d in datos['prestamos']:
        ref = f'Préstamo #{d["id_prestamo"]} / detalle #{d["id_detalle"]}'
        plazo = (
            d['fecha_limite_devolucion'].replace(tzinfo=timezone.utc).astimezone(LIMA)
        )
        observacion = ' '.join(
            filter(
                None,
                (
                    f'Condición de entrega: {d["condicion_entrega"]}.',
                    f'Plazo vigente: {plazo:%d/%m/%Y %H:%M} (Lima).',
                    d.get('observaciones_entrega'),
                    d.get('observaciones_prestamo'),
                ),
            )
        )
        agregar_evento_a_cronologia(
            d,
            d['fecha_entrega'],
            'Entrega del bien',
            ref,
            registrador=d.get('entregado_por'),
            dni_registrador=d.get('dni_encargado'),
            estado_nuevo='PRESTADO',
            observacion=observacion,
        )
        if d['fecha_devolucion']:
            agregar_evento_a_cronologia(
                d,
                d['fecha_devolucion'],
                'Devolución del bien',
                ref,
                registrador=d.get('recibido_por'),
                dni_registrador=d.get('dni_encargado_devolucion'),
                estado_nuevo=d['condicion_devolucion'],
                observacion=d.get('observaciones_devolucion'),
            )
        if d.get('fecha_regularizacion'):
            agregar_evento_a_cronologia(d, d['fecha_regularizacion'], 'Regularización por reposición', ref,
                    estado_nuevo='REGULARIZADO',
                    observacion='El pendiente se cerró por reposición; el bien original no fue devuelto.')

    for h in datos['historial_prestamos']:
        prestamo_id = h['id_prestamo']
        detalles = por_prestamo[prestamo_id]
        ampliacion, detalle_id = _identificar_detalle_de_ampliacion(h)
        referencia = f'Préstamo #{prestamo_id}'
        if ampliacion:
            afectados = [d for d in detalles if d['id_detalle'] == detalle_id]
            # Una ampliación de otro bien del mismo préstamo no altera este objeto.
            if not afectados:
                continue
            evento = 'Ampliación de plazo'
            referencia += f' / detalle #{detalle_id}'
        else:
            afectados = detalles
            evento = (
                'Estado del préstamo'
                if h['estado_anterior'] != h['estado_nuevo']
                else 'Seguimiento del préstamo'
            )
        agregar_evento_a_cronologia(
            h,
            h['fecha'],
            evento,
            referencia,
            codigo_inventario=', '.join(d['codigo_inventario'] for d in afectados),
            recurso=', '.join(dict.fromkeys(d['recurso'] for d in afectados)),
            dni_registrador=h.get('dni_responsable'),
        )

    for h in datos['historial_bienes']:
        agregar_evento_a_cronologia(
            h,
            h['fecha'],
            'Estado del bien',
            f'Bien {h["codigo_inventario"]}',
            dni_registrador=h.get('dni_responsable'),
        )
    for i in datos['incidencias']:
        agregar_evento_a_cronologia(
            i,
            i['fecha'],
            'Incidencia: ' + i['tipo'],
            f'Incidencia #{i["id_incidencia"]}',
            dni_registrador=i.get('dni_registrador'),
            estado_nuevo='REGISTRADA',
            observacion=f'{i.get("descripcion") or ""} Estado actual: {i["estado"]}.',
        )
    cierres_auditados = {
        (h['id_sancion'], h['estado_nuevo']) for h in datos['historial_sanciones'] if _etiquetar_cierre_de_sancion(h)
    }
    for s in datos['sanciones']:
        agregar_evento_a_cronologia(
            s,
            s['fecha'],
            'Sanción aplicada',
            f'Sanción #{s["id_sancion"]}',
            registrador=None,
            estado_nuevo='ACTIVA',
            observacion=' '.join(
                filter(
                    None,
                    (
                        s.get('motivo'),
                        s.get('descripcion'),
                        f'Estado actual: {s["estado"]}.',
                    ),
                )
            ),
        )
        # El último cierre de datos antiguos puede existir solo en la fila de la sanción.
        estado = s['estado']
        cierre = CIERRES_SANCION.get(estado)
        if cierre and s.get('fecha_levantamiento') and (s['id_sancion'], estado) not in cierres_auditados:
            agregar_evento_a_cronologia(
                s,
                s['fecha_levantamiento'],
                cierre,
                f'Sanción #{s["id_sancion"]}',
                registrador=s.get('levantada_por'),
                dni_registrador=s.get('dni_levantamiento'),
                estado_nuevo=estado,
                observacion=s.get('justificacion_levantamiento'),
            )
    for h in datos['historial_sanciones']:
        agregar_evento_a_cronologia(
            h,
            h['fecha'],
            _etiquetar_cierre_de_sancion(h) or 'Estado de sanción',
            f'Sanción #{h["id_sancion"]}',
            dni_registrador=h.get('dni_responsable'),
        )
    for r in datos['reservas']:
        agregar_evento_a_cronologia(
            r,
            r['fecha_solicitud'],
            'Solicitud registrada',
            f'Solicitud #{r["id_reserva"]}',
            estado_nuevo='EN_ESPERA',
            registrador=None,
            observacion=f'{r.get("observaciones") or ""} Estado actual: {r["estado"]}.',
        )
    for h in datos['historial_reservas']:
        agregar_evento_a_cronologia(
            h,
            h['fecha'],
            'Estado de solicitud',
            f'Solicitud #{h["id_reserva"]}',
            dni_registrador=h.get('dni_responsable'),
        )

    filas.sort(key=lambda fila: fila['fecha'] or datetime.min, reverse=True)
    prestamos = [
        dict(detalles[0], detalles=detalles) for detalles in por_prestamo.values()
    ]
    return dict(
        datos,
        filas=filas,
        prestamos_agrupados=prestamos,
        resumen=dict(
            prestamos=len(prestamos),
            pendientes=sum(d['fecha_devolucion'] is None and not d.get('fecha_regularizacion')
                           for d in datos['prestamos']),
            eventos=len(filas),
        ),
    )
