"""Los tres roles y sus permisos son fijos; las cuentas reciben uno de estos roles."""

from types import MappingProxyType

ROLES = ('USUARIO', 'ENCARGADO_PRESTAMOS', 'ADMINISTRADOR')
PERSONAS_CONSULTAR = 'PERSONAS_CONSULTAR'
ROLES_CONSULTAR = 'ROLES_CONSULTAR'
ROLES_GESTIONAR = 'ROLES_GESTIONAR'

PERMISOS = {
    'CATALOGO_CONSULTAR': 'Consultar catálogo',
    'RESERVAS_PROPIAS_GESTIONAR': 'Reservar y cancelar reservas propias',
    'PRESTAMOS_PROPIOS_CONSULTAR': 'Consultar préstamos propios',
    'PRESTAMOS_GESTIONAR': 'Gestionar préstamos, devoluciones y ampliaciones',
    PERSONAS_CONSULTAR: 'Consultar personas',
    'PERSONAS_GESTIONAR': 'Gestionar personas',
    'USUARIOS_GESTIONAR': 'Administrar cuentas',
    ROLES_CONSULTAR: 'Consultar roles',
    ROLES_GESTIONAR: 'Asignar roles a cuentas',
    'RECURSOS_GESTIONAR': 'Gestionar recursos y bienes',
    'POLITICAS_GESTIONAR': 'Administrar políticas',
    'REPORTES_CONSULTAR': 'Consultar reportes y descargar CSV',
}

_PERMISOS_USUARIO = frozenset({
    'CATALOGO_CONSULTAR',
    'RESERVAS_PROPIAS_GESTIONAR',
    'PRESTAMOS_PROPIOS_CONSULTAR',
})

PERMISOS_POR_ROL = MappingProxyType({
    'USUARIO': _PERMISOS_USUARIO,
    'ENCARGADO_PRESTAMOS': _PERMISOS_USUARIO | {
        'PRESTAMOS_GESTIONAR',
        PERSONAS_CONSULTAR,
        'PERSONAS_GESTIONAR',
        'REPORTES_CONSULTAR',
    },
    'ADMINISTRADOR': frozenset(PERMISOS),
})


def permisos_del_rol(rol: str) -> frozenset[str]:
    """Un rol desconocido no concede acceso a ninguna operación."""
    return PERMISOS_POR_ROL.get(rol, frozenset())
