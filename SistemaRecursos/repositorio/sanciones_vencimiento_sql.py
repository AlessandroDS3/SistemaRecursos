"""Operación común de vencimiento: el llamante bloquea primero préstamo y detalle."""


def aplicar_sancion_vencimiento(cursor, detalle, dni_persona, ahora):
    limite = detalle['fecha_limite_devolucion']
    fecha_recepcion = detalle.get('fecha_devolucion')
    if limite >= ahora or (fecha_recepcion is not None and fecha_recepcion <= limite):
        return None
    cursor.execute('SELECT id_sancion,estado FROM sancion WHERE id_detalle_vencido_ref=%s FOR UPDATE',
                   (detalle['id_detalle'],))
    existente = cursor.fetchone()
    if existente:
        # Una sanción retirada no se reactiva en cada ejecución del procesador.
        return dict(existente, creada=False)
    cursor.execute('''INSERT INTO incidencia(id_detalle_ref,descripcion,fecha,estado)
        VALUES(%s,%s,%s,'REGISTRADA')''',
        (detalle['id_detalle'], 'Vencimiento del plazo de devolución.', limite))
    id_incidencia = cursor.lastrowid
    cursor.execute('''INSERT INTO sancion
        (dni_persona,id_incidencia_ref,id_detalle_vencido_ref,motivo,fecha,descripcion,estado)
        VALUES(%s,%s,%s,%s,%s,%s,'ACTIVA')''',
        (dni_persona, id_incidencia, detalle['id_detalle'], 'Devolución fuera de plazo', limite,
         'Sanción automática por vencimiento. Bloquea nuevos préstamos hasta su retiro.'))
    id_sancion = cursor.lastrowid
    cursor.execute('''INSERT INTO historial_estado
        (entidad,id_entidad,estado_anterior,estado_nuevo,fecha,observacion,dni_responsable)
        VALUES('SANCION',%s,NULL,'ACTIVA',%s,%s,NULL)''',
        (id_sancion, ahora, 'Aplicación automática por vencimiento.'))
    return {'id_sancion': id_sancion, 'estado': 'ACTIVA', 'creada': True}
