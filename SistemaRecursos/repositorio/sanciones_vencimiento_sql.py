"""Operación común de vencimiento: el llamante bloquea primero préstamo y detalle."""


def aplicar_sancion_vencimiento(cursor, detalle, ahora):
    limite = detalle['fecha_limite_devolucion']
    fecha_recepcion = detalle.get('fecha_devolucion')
    if limite >= ahora or (fecha_recepcion is not None and fecha_recepcion <= limite):
        return None
    cursor.execute('''SELECT i.id_incidencia AS id_incidencia_ref,s.id_sancion,s.estado
        FROM incidencia i LEFT JOIN sancion s ON s.id_incidencia_ref=i.id_incidencia
        WHERE i.id_detalle=%s AND i.tipo='RETRASO' FOR UPDATE''',
                   (detalle['id_detalle'],))
    existente = cursor.fetchone()
    if existente and existente['id_sancion'] is not None:
        # Una sanción retirada no se reactiva en cada ejecución del procesador.
        return dict(existente, creada=False)
    if existente:
        id_incidencia = existente['id_incidencia_ref']
    else:
        cursor.execute('''INSERT INTO incidencia(id_detalle,tipo,dni_registrador,descripcion,fecha,estado)
            VALUES(%s,'RETRASO',NULL,%s,%s,'REGISTRADA')''',
            (detalle['id_detalle'], 'Vencimiento del plazo de devolución.', limite))
        id_incidencia = cursor.lastrowid
    cursor.execute('''INSERT INTO sancion
        (id_incidencia_ref,motivo,fecha,descripcion,estado)
        VALUES(%s,%s,%s,%s,'ACTIVA')''',
        (id_incidencia, 'Devolución fuera de plazo', limite,
         'Sanción automática por vencimiento. Bloquea nuevos préstamos hasta su retiro.'))
    id_sancion = cursor.lastrowid
    cursor.execute('''INSERT INTO historial_estado
        (entidad,id_entidad,estado_anterior,estado_nuevo,fecha,observacion,dni_responsable)
        VALUES('SANCION',%s,NULL,'ACTIVA',%s,%s,NULL)''',
        (id_sancion, ahora, 'Aplicación automática por vencimiento.'))
    return {'id_sancion': id_sancion, 'id_incidencia_ref': id_incidencia, 'estado': 'ACTIVA', 'creada': True}
