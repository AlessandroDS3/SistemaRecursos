"""Construye una cronología a partir de hechos guardados, sin inferir responsables."""

import re
from datetime import datetime, timezone

from dominio.compartido.validacion import LIMA
from dominio.gestion_control.catalogo_reportes import COLUMNAS_HISTORIAL


def organizar_historial(datos):
    filas = []
    por_prestamo = {}
    for detalle in datos['prestamos']:
        por_prestamo.setdefault(detalle['id_prestamo'], []).append(detalle)

    def agregar(origen, fecha, evento, referencia, **valores):
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
        agregar(
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
            agregar(
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
            agregar(d, d['fecha_regularizacion'], 'Regularización por reposición', ref,
                    estado_nuevo='REGULARIZADO',
                    observacion='El pendiente se cerró por reposición; el bien original no fue devuelto.')

    for h in datos['historial_prestamos']:
        detalles = por_prestamo[h['id_prestamo']]
        observacion = h.get('observacion') or ''
        ampliacion = re.match(r'^Detalle #(\d+):', observacion)
        if ampliacion:
            afectados = [d for d in detalles if d['id_detalle'] == int(ampliacion[1])]
            # Una ampliación de otro bien del mismo préstamo no altera este objeto.
            if not afectados:
                continue
            evento = 'Ampliación de plazo'
        else:
            afectados = detalles
            evento = (
                'Estado del préstamo'
                if h['estado_anterior'] != h['estado_nuevo']
                else 'Seguimiento del préstamo'
            )
        agregar(
            h,
            h['fecha'],
            evento,
            f'Préstamo #{h["id_prestamo"]}',
            codigo_inventario=', '.join(d['codigo_inventario'] for d in afectados),
            recurso=', '.join(dict.fromkeys(d['recurso'] for d in afectados)),
            dni_registrador=h.get('dni_responsable'),
        )

    for h in datos['historial_bienes']:
        agregar(
            h,
            h['fecha'],
            'Estado del bien',
            f'Bien {h["codigo_inventario"]}',
            dni_registrador=h.get('dni_responsable'),
        )
    for i in datos['incidencias']:
        agregar(
            i,
            i['fecha'],
            'Incidencia: ' + i['tipo'],
            f'Incidencia #{i["id_incidencia"]}',
            dni_registrador=i.get('dni_registrador'),
            estado_nuevo='REGISTRADA',
            observacion=f'{i.get("descripcion") or ""} Estado actual: {i["estado"]}.',
        )
    for s in datos['sanciones']:
        agregar(
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
        # Conserva levantamientos antiguos aunque no tengan una entrada de auditoría.
        auditada = any(
            h['id_sancion'] == s['id_sancion'] and h['estado_nuevo'] in ('LEVANTADA', 'CUMPLIDA')
            for h in datos['historial_sanciones']
        )
        if s.get('fecha_levantamiento') and not auditada:
            agregar(
                s,
                s['fecha_levantamiento'],
                'Cumplimiento de sanción' if s['estado'] == 'CUMPLIDA' else 'Levantamiento de sanción',
                f'Sanción #{s["id_sancion"]}',
                registrador=s.get('levantada_por'),
                dni_registrador=s.get('dni_levantamiento'),
                estado_nuevo='CUMPLIDA' if s['estado'] == 'CUMPLIDA' else 'LEVANTADA',
                observacion=s.get('justificacion_levantamiento'),
            )
    for h in datos['historial_sanciones']:
        agregar(
            h,
            h['fecha'],
            'Estado de sanción',
            f'Sanción #{h["id_sancion"]}',
            dni_registrador=h.get('dni_responsable'),
        )
    for r in datos['reservas']:
        agregar(
            r,
            r['fecha_solicitud'],
            'Solicitud registrada',
            f'Solicitud #{r["id_reserva"]}',
            estado_nuevo='EN_ESPERA',
            registrador=None,
            observacion=f'{r.get("observaciones") or ""} Estado actual: {r["estado"]}.',
        )
    for h in datos['historial_reservas']:
        agregar(
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
