from dominio.cuentas import (
    CATALOGO_PERMISOS,
    IRepositorioRol,
    NombreRol,
    Permiso,
    Rol,
    consultar_catalogo_permisos,
    validar_permisos_administrador,
)
from dominio.validaciones import exigir_version, version_matriz
from repositorio.conexion_mysql import MySQLConnection


class RepositorioRolSQL(IRepositorioRol):
    def __init__(self, conexion=None):
        self.conexion = conexion or MySQLConnection()

    def consultar_rol(self, nombre) -> Rol | None:
        try:
            rol = Rol(nombre=NombreRol(nombre))
        except (ValueError, TypeError):
            return None
        with self.conexion.sesion() as cursor:
            cargar_permisos_roles(cursor, [rol])
        return rol

    def consultar_roles(self) -> list[Rol]:
        roles = [Rol(nombre=nombre) for nombre in NombreRol]
        with self.conexion.sesion() as cursor:
            cargar_permisos_roles(cursor, roles)
        return roles

    def consultar_permisos(self) -> list[Permiso]:
        return consultar_catalogo_permisos()

    def actualizar_matriz_permisos(self, permisos_por_rol, *, version) -> None:
        roles = [Rol(nombre=nombre) for nombre in NombreRol]
        permisos = consultar_catalogo_permisos()
        if set(permisos_por_rol) != {nombre.value for nombre in NombreRol}:
            raise ValueError("La matriz debe incluir los tres roles del sistema.")
        for seleccionados in permisos_por_rol.values():
            if not set(seleccionados).issubset(CATALOGO_PERMISOS):
                raise ValueError("Uno de los permisos seleccionados no existe.")
        with self.conexion.sesion(escritura=True) as cursor:
            # Bloquea las asignaciones antes de comprobar la version y guardarlas.
            cursor.execute("SELECT rol,permiso FROM rol_permiso ORDER BY rol,permiso FOR UPDATE")
            filas = cursor.fetchall()
            cargar_permisos_roles(cursor, roles, filas=filas)
            exigir_version(version, version_matriz(roles, permisos))
            validar_permisos_administrador(roles, permisos, permisos_por_rol)
            cursor.execute("DELETE FROM rol_permiso")
            pares = [(rol, codigo) for rol, codigos in permisos_por_rol.items() for codigo in codigos]
            if pares:
                cursor.executemany("INSERT INTO rol_permiso (rol,permiso) VALUES (%s,%s)", pares)


def cargar_permisos_roles(cursor, roles, *, filas=None):
    por_nombre = {rol.nombre.value: rol for rol in roles}
    if not por_nombre:
        return
    if filas is None:
        marcadores = ','.join(['%s'] * len(por_nombre))
        cursor.execute("SELECT rol,permiso FROM rol_permiso WHERE rol IN (" + marcadores + ") ORDER BY rol,permiso",
                       tuple(por_nombre))
        filas = cursor.fetchall()
    for fila in filas:
        if fila['rol'] in por_nombre:
            codigo = fila['permiso']
            if codigo not in CATALOGO_PERMISOS:
                raise ValueError("La base contiene un permiso desconocido: " + codigo)
            por_nombre[fila['rol']].permisos.append(Permiso(codigo, CATALOGO_PERMISOS[codigo]))
