from unittest.mock import patch

from dominio.gestion_personas_usuarios.acceso import CuentaAcceso
from dominio.gestion_personas_usuarios.rol import permisos_del_rol


def crear_cliente_con_sesion_simulada(prueba, app, acceso, identificador=None):
    """Cliente de Flask con sesión válida: cuenta activa y sesión vigente en el servidor."""
    servicio = app.extensions['servicios']['acceso']
    prueba.enterContext(patch.object(servicio, 'consultar_cuenta_activa', return_value=acceso))
    prueba.enterContext(patch.object(servicio, 'validar_sesion', return_value=True))
    cliente = app.test_client()
    with cliente.session_transaction() as sesion:
        sesion.update(
            id_usuario=identificador or acceso.id_usuario,
            credenciales=acceso.version_credenciales,
            sid='sesion-de-prueba',
            csrf='token',
        )
    return cliente


def crear_cuenta_de_prueba(rol):
    return CuentaAcceso(
        id_usuario=1, dni='20000001', nombre_usuario='prueba',
        nombres='Ana', apellidos='Prueba', rol=rol,
        estado_cuenta='ACTIVA', estado_persona='ACTIVA',
        contrasena_hash='pruebas', permisos=permisos_del_rol(rol),
    )
