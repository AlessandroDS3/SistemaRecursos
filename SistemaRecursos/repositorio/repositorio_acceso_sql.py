from __future__ import annotations
from dominio.gestion_personas_usuarios.nombre_rol import NombreRol
from dominio.resultados_consulta import CuentaParaRol

from dominio.gestion_personas_usuarios.validacion_persona import validar_dni
from dominio.gestion_personas_usuarios.i_repositorio_acceso import IRepositorioAcceso
from dominio.gestion_personas_usuarios.usuario_sistema import UsuarioSistema
from dominio.gestion_personas_usuarios.credenciales import Credenciales
from dominio.gestion_personas_usuarios.usuario_sistema import EstadoCuenta
from dominio.gestion_personas_usuarios.usuario_sistema import IdentidadAcceso
from dominio.gestion_personas_usuarios.rol import Rol
from repositorio.conexion_mysql import MySQLConnection
from dominio.gestion_personas_usuarios.usuario_sistema import es_administrador_activo, validar_conservacion_administrador
from repositorio.repositorio_rol_sql import cargar_permisos_roles


CONSULTA_CUENTAS = """
    SELECT u.id_usuario, u.nombre_usuario, u.contrasena_hash,
           u.ultimo_acceso, u.estado_cuenta,
           p.dni, p.nombres, p.apellidos,
           p.estado AS estado_persona,
           u.rol AS nombre_rol
    FROM usuario_sistema u
    JOIN persona p ON p.dni = u.dni_persona
"""
COLUMNAS_BUSQUEDA_CUENTA = {
    "nombre_usuario": "u.nombre_usuario",
    "dni_persona": "u.dni_persona",
    "id_usuario": "u.id_usuario",
}
ACCESO_EFECTIVO_SQL = """
    (u.estado_cuenta = 'ACTIVA' AND p.estado = 'ACTIVA')
"""


class RepositorioAccesoSQL(IRepositorioAcceso):
    def __init__(self, conexion=None):
        self.conexion = conexion or MySQLConnection()

    @staticmethod
    def _bloquear_cuentas(cursor):
        """Bloquea las cuentas en el mismo orden para proteger al ultimo administrador."""
        cursor.execute(
            "SELECT u.id_usuario,u.dni_persona,u.rol,u.estado_cuenta,p.estado AS estado_persona "
            "FROM usuario_sistema u JOIN persona p ON p.dni=u.dni_persona "
            "ORDER BY u.id_usuario FOR UPDATE")
        return cursor.fetchall()

    @staticmethod
    def _construir_cuenta(cursor, fila):
        rol = Rol(nombre=fila["nombre_rol"])
        cargar_permisos_roles(cursor, [rol])
        return UsuarioSistema(
            id_usuario=fila["id_usuario"],
            persona=IdentidadAcceso(dni=fila['dni'], nombres=fila['nombres'],
                                   apellidos=fila['apellidos'], estado=fila['estado_persona']),
            rol=rol, credenciales=Credenciales(fila["nombre_usuario"], fila["contrasena_hash"]),
            ultimo_acceso=fila["ultimo_acceso"], estado_cuenta=fila["estado_cuenta"],
        )

    def _consultar(self, campo, valor):
        columna = COLUMNAS_BUSQUEDA_CUENTA[campo]
        with self.conexion.sesion() as cursor:
            cursor.execute(CONSULTA_CUENTAS + f" WHERE {columna}=%s", (valor,))
            fila_usuario = cursor.fetchone()
            if fila_usuario is None:
                return None
            return self._construir_cuenta(cursor, fila_usuario)

    def consultar_por_nombre_usuario(self, nombre_usuario) -> UsuarioSistema | None:
        return self._consultar("nombre_usuario", nombre_usuario)

    def consultar_cuenta_persona(self, dni) -> UsuarioSistema | None:
        return self._consultar("dni_persona", dni)

    def consultar_cuenta_por_id(self, id_usuario) -> UsuarioSistema | None:
        return self._consultar("id_usuario", id_usuario)

    def consultar_resumen_cuentas(self, dnis_persona) -> dict[str, dict[str, bool]]:
        dnis_persona = tuple(sorted({validar_dni(dni) for dni in dnis_persona}))
        if not dnis_persona:
            return {}
        marcadores = ",".join(["%s"] * len(dnis_persona))
        consulta = f"""
            SELECT u.dni_persona, {ACCESO_EFECTIVO_SQL} AS puede_acceder
            FROM usuario_sistema u
            JOIN persona p ON p.dni = u.dni_persona
            WHERE u.dni_persona IN ({marcadores})
        """
        with self.conexion.sesion() as cursor:
            cursor.execute(consulta, dnis_persona)
            return {
                fila_usuario["dni_persona"]: {"puede_acceder": bool(fila_usuario["puede_acceder"])}
                for fila_usuario in cursor.fetchall()
            }

    def registrar_cuenta(self, usuario) -> UsuarioSistema:
        if usuario.id_usuario is not None:
            raise ValueError("Para modificar una cuenta registrada, usa actualizar_cuenta.")
        if usuario.rol.nombre != NombreRol.USUARIO:
            raise ValueError("Las cuentas nuevas deben tener el rol Usuario.")
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute("SELECT estado FROM persona WHERE dni=%s FOR UPDATE", (usuario.persona.dni,))
            persona = cursor.fetchone()
            if not persona or persona["estado"] != "ACTIVA":
                raise ValueError("La persona debe estar activa para crear su cuenta.")
            cursor.execute(
                "INSERT INTO usuario_sistema (dni_persona,rol,nombre_usuario,contrasena_hash,estado_cuenta) "
                "VALUES (%s,%s,%s,%s,%s)",
                (usuario.persona.dni, usuario.rol.nombre.value, usuario.credenciales.nombre_usuario,
                 usuario.credenciales.contrasena_hash, usuario.estado_cuenta.value))
            usuario.id_usuario = cursor.lastrowid
        return usuario

    @staticmethod
    def _validar_cambio_acceso(cuenta_actual, cuentas, rol, activar, id_usuario_actor):
        nombre_rol = cuenta_actual["rol"] if rol is None else NombreRol(rol).value
        if activar is True and cuenta_actual["estado_persona"] != "ACTIVA":
            raise ValueError("Para activar la cuenta, la persona debe estar activa.")
        if activar is False and id_usuario_actor == cuenta_actual["id_usuario"]:
            raise ValueError("No puedes desactivar la cuenta con la que estás trabajando.")
        cuenta_nueva = dict(cuenta_actual, rol=nombre_rol)
        if activar is not None:
            cuenta_nueva["estado_cuenta"] = EstadoCuenta.ACTIVA.value if activar else EstadoCuenta.INACTIVA.value
        validar_conservacion_administrador(cuenta_actual, cuenta_nueva, cuentas)
        return cuenta_nueva

    @staticmethod
    def _persistir_cambio_acceso(
        cursor, cuenta_nueva, nombre_usuario, rol, contrasena_hash, activar,
    ):
        columnas, valores = [], []
        for campo, valor in (
            ("nombre_usuario", nombre_usuario), ("rol", NombreRol(rol).value if rol is not None else None),
            ("contrasena_hash", contrasena_hash),
        ):
            if valor is not None:
                columnas.append(campo + "=%s")
                valores.append(valor)
        if activar is not None:
            columnas.append("estado_cuenta=%s")
            valores.append(cuenta_nueva["estado_cuenta"])
        if columnas:
            cursor.execute(
                "UPDATE usuario_sistema SET " + ",".join(columnas) + " WHERE id_usuario=%s",
                (*valores, cuenta_nueva["id_usuario"]),
            )

    def actualizar_cuenta(
        self, id_usuario, nombre_usuario=None, rol=None, contrasena_hash=None,
        activar=None, id_usuario_actor=None,
    ) -> UsuarioSistema:
        if activar is not None and not isinstance(activar, bool):
            raise ValueError("El estado de activación no es válido.")
        with self.conexion.sesion(escritura=True) as cursor:
            cuentas = self._bloquear_cuentas(cursor)
            cuenta_actual = None
            for cuenta in cuentas:
                if cuenta["id_usuario"] == id_usuario:
                    cuenta_actual = cuenta
                    break
            if cuenta_actual is None:
                raise LookupError("No se encontró la cuenta de usuario.")
            edita_cuenta = any(valor is not None for valor in (nombre_usuario, contrasena_hash, activar))
            if (edita_cuenta and id_usuario_actor != id_usuario
                    and cuenta_actual["rol"] == NombreRol.ADMINISTRADOR):
                actor = next((c for c in cuentas if c["id_usuario"] == id_usuario_actor), None)
                if not actor or not es_administrador_activo(actor):
                    raise PermissionError("Solo un administrador puede modificar esta cuenta.")
            cuenta_nueva = self._validar_cambio_acceso(
                cuenta_actual, cuentas, rol, activar, id_usuario_actor,
            )
            self._persistir_cambio_acceso(
                cursor, cuenta_nueva, nombre_usuario, rol, contrasena_hash, activar,
            )
        return self.consultar_cuenta_por_id(id_usuario)

    def registrar_acceso(self, id_usuario) -> None:
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute(
                "UPDATE usuario_sistema SET ultimo_acceso=UTC_TIMESTAMP() WHERE id_usuario=%s",
                (id_usuario,),
            )

    def consultar_cuentas_para_roles(self, termino: str, limite: int = 20) -> list[CuentaParaRol]:
        palabras = termino.strip().split()
        if not palabras:
            return []
        condiciones = []
        valores = []
        for palabra in palabras:
            condiciones.append("(p.apellidos LIKE %s OR p.dni LIKE %s OR e.cui LIKE %s)")
            valores.extend(("%" + palabra + "%", palabra + "%", palabra + "%"))
        limite = max(1, min(int(limite), 20))
        consulta = """
            SELECT u.id_usuario, u.dni_persona, p.nombres, p.apellidos, e.cui,
                   u.nombre_usuario, u.rol AS nombre_rol, u.estado_cuenta
            FROM usuario_sistema u
            JOIN persona p ON p.dni=u.dni_persona
            LEFT JOIN estudiante e ON e.dni=p.dni
            WHERE """ + " AND ".join(condiciones) + " ORDER BY p.apellidos,p.nombres,u.id_usuario LIMIT %s"
        with self.conexion.sesion() as cursor:
            cursor.execute(consulta, (*valores, limite))
            return cursor.fetchall()

    def actualizar_rol_cuenta(self, id_usuario: int, rol: int, id_usuario_actor: int) -> UsuarioSistema:
        # Reutiliza la misma validación bajo bloqueo que protege los cambios de acceso.
        return self.actualizar_cuenta(id_usuario, rol=rol, id_usuario_actor=id_usuario_actor)
