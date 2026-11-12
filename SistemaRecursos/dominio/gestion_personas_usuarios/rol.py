from dataclasses import dataclass, field
from dominio.gestion_personas_usuarios.nombre_rol import NombreRol
from dominio.gestion_personas_usuarios.permiso import Permiso


PERMISOS_ADMINISTRACION = frozenset({"ROLES_CONSULTAR", "ROLES_GESTIONAR"})


@dataclass(kw_only=True)
class Rol:
    nombre: NombreRol
    permisos: list[Permiso] = field(default_factory=list)

    def __post_init__(self):
        self.nombre = NombreRol(self.nombre)

    def tiene_permiso(self, codigo):
        return any(permiso.codigo == codigo for permiso in self.permisos)


def validar_permisos_administrador(roles, permisos, matriz):
    administrador = NombreRol.ADMINISTRADOR.value
    if administrador not in matriz:
        raise ValueError("La matriz debe incluir el rol Administrador.")
    if not PERMISOS_ADMINISTRACION.issubset(matriz[administrador]):
        raise ValueError("El rol Administrador debe conservar los permisos para consultar y gestionar roles.")
