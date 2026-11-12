from dataclasses import dataclass


@dataclass(frozen=True)
class Permiso:
    codigo: str
    descripcion: str = ""


# Catalogo fijo; las asignaciones a roles se guardan en rol_permiso.
CATALOGO_PERMISOS = {'PERSONAS_CONSULTAR': 'Consultar el directorio de personas',
 'PERSONAS_GESTIONAR': 'Registrar, editar y desactivar personas',
 'USUARIOS_GESTIONAR': 'Crear cuentas y asignar roles',
 'ROLES_CONSULTAR': 'Consultar los roles y sus permisos',
 'ROLES_GESTIONAR': 'Asignar y revocar permisos de los roles',
 'CATALOGO_CONSULTAR': 'Consultar el catálogo de recursos',
 'PRESTAMOS_PROPIOS_CONSULTAR': 'Consultar préstamos propios',
 'AMPLIACIONES_SOLICITAR': 'Solicitar ampliaciones de préstamos propios',
 'RESERVAS_PROPIAS_GESTIONAR': 'Solicitar préstamos y gestionar reservas propias',
 'PRESTAMOS_GESTIONAR': 'Registrar entregas y devoluciones',
 'RECURSOS_GESTIONAR': 'Gestionar recursos y bienes',
 'POLITICAS_GESTIONAR': 'Gestionar políticas de préstamo',
 'REPORTES_CONSULTAR': 'Consultar y descargar reportes de préstamos y devoluciones'}


def consultar_catalogo_permisos():
    return [Permiso(codigo=codigo, descripcion=descripcion)
            for codigo, descripcion in sorted(CATALOGO_PERMISOS.items())]
