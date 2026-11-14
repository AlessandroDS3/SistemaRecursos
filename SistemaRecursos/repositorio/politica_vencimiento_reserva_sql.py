from dominio.control import PoliticaVencimientoReserva


def consultar_politica_vencimiento_reserva(cursor, bloquear=False):
    cursor.execute(
        "SELECT plazo_espera,unidad_espera,plazo_retiro,unidad_retiro "
        "FROM configuracion_general WHERE id_configuracion=1"
        + (" FOR UPDATE" if bloquear else "")
    )
    fila = cursor.fetchone()
    if fila is None:
        raise ValueError("Configura los vencimientos generales de solicitudes y reservas.")
    return PoliticaVencimientoReserva(**fila)
