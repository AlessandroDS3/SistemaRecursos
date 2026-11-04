from dataclasses import dataclass, field
from dominio.gestion_personas_usuarios.nombre_rol import NombreRol
from dominio.gestion_personas_usuarios.permiso import Permiso


PERMISOS_ADMINISTRACION = frozenset({"ROLES_CONSULTAR", "ROLES_GESTIONAR"})


@dataclass(kw_only=True)
class Rol:
    nombre: NombreRol
    descripcion: str = ""
    activo: bool = True
    id_rol: int | None = None
    permisos: list[Permiso] = field(default_factory=list)

    def __post_init__(self):
        self.nombre = NombreRol(self.nombre)
        if self.descripcion is None:
            self.descripcion = ""
        if not isinstance(self.descripcion, str) or len(self.descripcion) > 255:
            raise ValueError("Descripción de rol: máximo 255 caracteres.")

    def tiene_permiso(self, codigo):
        return self.activo and any(p.codigo == codigo for p in self.permisos)


def validar_permisos_administrador(roles, permisos, matriz):
    administrador = None
    for rol in roles:
        if rol.activo and rol.nombre == NombreRol.ADMINISTRADOR:
            administrador = rol
            break
    if administrador is None or administrador.id_rol not in matriz:
        return

    permisos_por_codigo = {}
    for permiso in permisos:
        permisos_por_codigo[permiso.codigo] = permiso.id_permiso

    for codigo in PERMISOS_ADMINISTRACION:
        if codigo not in permisos_por_codigo:
            raise ValueError("Faltan permisos de consulta o gestión de roles en el catálogo.")

    permisos_seleccionados = set(matriz[administrador.id_rol])
    for codigo in PERMISOS_ADMINISTRACION:
        id_permiso = permisos_por_codigo[codigo]
        if id_permiso not in permisos_seleccionados:
            raise ValueError("El rol Administrador debe conservar los permisos para consultar y gestionar roles.")
