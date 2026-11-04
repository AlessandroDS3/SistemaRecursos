from dominio.gestion_personas_usuarios.usuario_sistema import EstadoCuenta
from dominio.gestion_personas_usuarios.nombre_rol import NombreRol


def bloquear_cuentas_y_roles(cursor):
    """Todos los cambios que pueden quitar acceso toman los bloqueos en este orden."""
    cursor.execute("SELECT id_rol,nombre,activo FROM rol ORDER BY id_rol FOR UPDATE")
    roles = {fila_rol["id_rol"]: fila_rol for fila_rol in cursor.fetchall()}
    cursor.execute(
        "SELECT u.id_usuario,u.dni_persona,u.id_rol_ref,u.activo,u.estado_cuenta,"
        "p.estado AS estado_persona "
        "FROM usuario_sistema u JOIN persona p ON p.dni=u.dni_persona "
        "ORDER BY u.id_usuario FOR UPDATE"
    )
    return roles, cursor.fetchall()


def es_administrador_activo(cuenta, roles):
    rol = roles.get(cuenta["id_rol_ref"])
    if not rol or rol["nombre"] != NombreRol.ADMINISTRADOR or not rol["activo"]:
        return False
    if not cuenta["activo"] or cuenta["estado_cuenta"] != EstadoCuenta.ACTIVA:
        return False
    return cuenta["estado_persona"] == "ACTIVA"


def validar_baja_persona(dni, id_usuario_actor, cuentas, roles):
    cuentas_persona = []
    for cuenta in cuentas:
        if cuenta["dni_persona"] == dni:
            cuentas_persona.append(cuenta)

    for cuenta in cuentas_persona:
        if cuenta["id_usuario"] == id_usuario_actor:
            raise ValueError("No puedes desactivar la persona de la cuenta con la que estás trabajando.")

    tiene_cuenta_administradora = False
    for cuenta in cuentas_persona:
        if es_administrador_activo(cuenta, roles):
            tiene_cuenta_administradora = True
            break
    if not tiene_cuenta_administradora:
        return

    for cuenta in cuentas:
        if cuenta["dni_persona"] != dni and es_administrador_activo(cuenta, roles):
            return
    raise ValueError("Debe conservarse al menos una cuenta administradora activa.")
