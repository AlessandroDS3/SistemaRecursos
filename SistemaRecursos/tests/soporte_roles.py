from dominio.gestion_personas_usuarios.acceso import CuentaAcceso
from dominio.gestion_personas_usuarios.rol import permisos_del_rol


def cuenta(rol):
    return CuentaAcceso(
        id_usuario=1, dni='20000001', nombre_usuario='prueba',
        nombres='Ana', apellidos='Prueba', rol=rol,
        estado_cuenta='ACTIVA', estado_persona='ACTIVA',
        contrasena_hash='pruebas', permisos=permisos_del_rol(rol),
    )
