from dominio.gestion_control.politica_vencimiento_reserva import PoliticaVencimientoReserva


def consultar_politica_vencimiento_reserva(cursor, bloquear=False):
    cursor.execute(
        "SELECT plazo_espera,unidad_espera,plazo_retiro,unidad_retiro "
        "FROM politica_vencimiento_reserva WHERE id_politica=1"
        + (" FOR UPDATE" if bloquear else "")
    )
    fila = cursor.fetchone()
    if fila is None:
        raise ValueError("Configura los vencimientos generales de solicitudes y reservas.")
    return PoliticaVencimientoReserva(**fila)
