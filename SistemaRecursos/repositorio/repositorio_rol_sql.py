from __future__ import annotations

from dominio.gestion_personas_usuarios.i_repositorio_rol import IRepositorioRol
from dominio.gestion_personas_usuarios.rol import Rol, validar_permisos_administrador
from dominio.gestion_personas_usuarios.permiso import Permiso
from repositorio.conexion_mysql import MySQLConnection


class RepositorioRolSQL(IRepositorioRol):
    def __init__(self, conexion=None):
        self.conexion = conexion or MySQLConnection()

    def consultar_rol(self, id_rol) -> Rol | None:
        with self.conexion.sesion() as cursor:
            cursor.execute(
                "SELECT id_rol, nombre, descripcion, activo FROM rol WHERE id_rol=%s",
                (id_rol,),
            )
            fila_rol = cursor.fetchone()
            if fila_rol is None:
                return None
            rol = Rol(**fila_rol)
            cargar_permisos_roles(cursor, [rol])
            return rol

    def consultar_roles(self) -> list[Rol]:
        with self.conexion.sesion() as cursor:
            cursor.execute("SELECT id_rol, nombre, descripcion, activo FROM rol ORDER BY id_rol")
            roles = [Rol(**fila_rol) for fila_rol in cursor.fetchall()]
            cargar_permisos_roles(cursor, roles)
            return roles

    def registrar_rol(self, rol) -> Rol:
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute(
                "INSERT INTO rol (nombre, descripcion, activo) VALUES (%s,%s,%s)",
                (rol.nombre.value, rol.descripcion, rol.activo),
            )
            nuevo_id = cursor.lastrowid
        rol.id_rol = nuevo_id
        return rol

    def actualizar_rol(self, rol) -> Rol:
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute(
                "UPDATE rol SET nombre=%s, descripcion=%s, activo=%s WHERE id_rol=%s",
                (rol.nombre.value, rol.descripcion, rol.activo, rol.id_rol),
            )
        return rol

    def desactivar_rol(self, id_rol) -> None:
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute("UPDATE rol SET activo=FALSE WHERE id_rol=%s", (id_rol,))

    def consultar_permisos(self) -> list[Permiso]:
        with self.conexion.sesion() as cursor:
            cursor.execute("SELECT id_permiso, codigo, descripcion FROM permiso ORDER BY codigo")
            return [Permiso(**fila_permiso) for fila_permiso in cursor.fetchall()]

    def actualizar_matriz_permisos(self, permisos_por_rol) -> None:
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute("SELECT id_rol,nombre,descripcion,activo FROM rol ORDER BY id_rol FOR UPDATE")
            roles = [Rol(**fila_rol) for fila_rol in cursor.fetchall()]
            cursor.execute("SELECT id_permiso,codigo,descripcion FROM permiso ORDER BY id_permiso FOR UPDATE")
            permisos = [Permiso(**fila_permiso) for fila_permiso in cursor.fetchall()]
            validar_permisos_administrador(roles, permisos, permisos_por_rol)
            for id_rol, id_permisos in permisos_por_rol.items():
                cursor.execute("DELETE FROM rol_permiso WHERE id_rol=%s", (id_rol,))
                if id_permisos:
                    cursor.executemany(
                        "INSERT INTO rol_permiso (id_rol, id_permiso) VALUES (%s, %s)",
                        [(id_rol, id_permiso) for id_permiso in id_permisos],
                    )


def cargar_permisos_roles(cursor, roles):
    roles_por_id = {rol.id_rol: rol for rol in roles}
    if not roles_por_id:
        return
    marcadores = ", ".join(["%s"] * len(roles_por_id))
    cursor.execute(
        f"""
        SELECT relacion.id_rol, permiso.id_permiso, permiso.codigo, permiso.descripcion
        FROM permiso
        JOIN rol_permiso relacion ON relacion.id_permiso = permiso.id_permiso
        WHERE relacion.id_rol IN ({marcadores})
        ORDER BY relacion.id_rol, permiso.codigo
        """,
        tuple(roles_por_id),
    )
    for fila_permiso in cursor.fetchall():
        roles_por_id[fila_permiso["id_rol"]].permisos.append(
            Permiso(
                id_permiso=fila_permiso["id_permiso"],
                codigo=fila_permiso["codigo"],
                descripcion=fila_permiso["descripcion"],
            )
        )
