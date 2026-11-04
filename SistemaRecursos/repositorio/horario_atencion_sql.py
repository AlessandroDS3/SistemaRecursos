from dominio.gestion_control.horario_atencion import HorarioAtencion


def consultar_horario_atencion(cursor, bloquear=False):
    cursor.execute('SELECT hora_apertura,hora_cierre FROM horario_atencion WHERE id_horario=1' +
                   (' FOR UPDATE' if bloquear else ''))
    fila = cursor.fetchone()
    if fila is None:
        raise ValueError('Configura el horario general de atención en Políticas antes de registrar entregas.')
    return HorarioAtencion(**fila)
