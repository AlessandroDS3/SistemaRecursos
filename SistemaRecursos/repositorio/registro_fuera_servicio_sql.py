"""Persiste las reglas del dominio usando el cursor de la transacción llamante."""
from dominio.gestion_recursos.bien_material import EstadoBienMaterial, ESTADOS_FUERA_SERVICIO
from dominio.gestion_recursos.registro_fuera_servicio import EstadoFueraServicio
from dominio.gestion_recursos.registro_fuera_servicio import RegistroFueraServicio


def guardar_cambio_fuera_servicio(
    cursor, id_bien, estado_bien, motivo, fecha,
    fecha_fin_estimada=None, descripcion="",
):
    """Cierra los registros activos y abre uno nuevo si el bien sigue fuera de servicio.

    El llamante debe mantener bloqueado el bien y confirmar o revertir la operación
    junto con su estado, préstamo e historial. Esta función no abre otra conexión.
    """
    estado_bien = EstadoBienMaterial(estado_bien)
    nuevo = None
    if estado_bien in ESTADOS_FUERA_SERVICIO:
        nuevo = RegistroFueraServicio(
            id_bien_ref=id_bien, motivo=motivo, fecha_inicio=fecha,
            fecha_fin_estimada=fecha_fin_estimada, descripcion=descripcion,
        )
    cursor.execute(
        "SELECT * FROM registro_fuera_servicio "
        "WHERE id_bien_ref=%s AND estado=%s ORDER BY id_registro FOR UPDATE",
        (id_bien, EstadoFueraServicio.ACTIVO.value),
    )
    registros = [RegistroFueraServicio(**fila) for fila in cursor.fetchall()]
    # Validar todos los cierres antes de escribir el primero.
    for registro in registros:
        registro.cerrar_registro(fecha)
    for registro in registros:
        cursor.execute(
            "UPDATE registro_fuera_servicio SET estado=%s,fecha_fin_real=%s "
            "WHERE id_registro=%s",
            (registro.estado.value, registro.fecha_fin_real, registro.id_registro),
        )
    if nuevo is not None:
        cursor.execute(
            "INSERT INTO registro_fuera_servicio "
            "(id_bien_ref,motivo,fecha_inicio,fecha_fin_estimada,descripcion,estado) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (nuevo.id_bien_ref, nuevo.motivo, nuevo.fecha_inicio,
             nuevo.fecha_fin_estimada, nuevo.descripcion, nuevo.estado.value),
        )
        nuevo.id_registro = cursor.lastrowid
    return nuevo
