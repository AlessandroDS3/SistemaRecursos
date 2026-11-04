from __future__ import annotations
from hashlib import sha256
from secrets import randbelow
from dominio.gestion_personas_usuarios.nombre_rol import NombreRol
from dominio.resultados_consulta import CuentaParaRol

from dominio.gestion_personas_usuarios.validacion_persona import validar_dni
from dominio.gestion_personas_usuarios.i_repositorio_acceso import IRepositorioAcceso
from dominio.gestion_personas_usuarios.usuario_sistema import UsuarioSistema
from dominio.gestion_personas_usuarios.credenciales import Credenciales
from dominio.gestion_personas_usuarios.usuario_sistema import EstadoCuenta
from dominio.gestion_personas_usuarios.fabrica_persona import FabricaPersona
from dominio.gestion_personas_usuarios.rol import Rol
from repositorio.conexion_mysql import MySQLConnection
from repositorio.proteccion_administradores_sql import bloquear_cuentas_y_roles, es_administrador_activo
from repositorio.repositorio_rol_sql import cargar_permisos_roles


CONSULTA_CUENTAS = """
    SELECT u.id_usuario, u.nombre_usuario, u.contrasena_hash,
           u.ultimo_acceso, u.activo, u.estado_cuenta,
           p.dni, p.nombres, p.apellidos,
           p.telefono, p.correo, p.estado,
           e.cui, e.ciclo,
           e.semestre_academico, e.estado_matricula,
           d.codigo_docente, d.departamento_academico, d.facultad, d.escuela_profesional,
           a.codigo_empleado, a.area,
           CASE WHEN e.dni IS NOT NULL THEN 'ESTUDIANTE'
                WHEN d.dni IS NOT NULL THEN 'DOCENTE'
                WHEN a.dni IS NOT NULL THEN 'ADMINISTRATIVO' END AS tipo,
           r.id_rol, r.nombre AS nombre_rol,
           r.descripcion AS descripcion_rol, r.activo AS rol_activo
    FROM usuario_sistema u
    JOIN persona p ON p.dni = u.dni_persona
    JOIN rol r ON r.id_rol = u.id_rol_ref
    LEFT JOIN estudiante e ON e.dni = p.dni
    LEFT JOIN docente d ON d.dni = p.dni
    LEFT JOIN administrativo a ON a.dni = p.dni
"""
COLUMNAS_BUSQUEDA_CUENTA = {
    "nombre_usuario": "u.nombre_usuario",
    "dni_persona": "u.dni_persona",
    "id_usuario": "u.id_usuario",
}
ACCESO_EFECTIVO_SQL = """
    (u.activo = TRUE AND u.estado_cuenta = 'ACTIVA'
     AND p.estado = 'ACTIVA' AND r.activo = TRUE)
"""


class RepositorioAccesoSQL(IRepositorioAcceso):
    def __init__(self, conexion=None):
        self.conexion = conexion or MySQLConnection()

    @staticmethod
    def _construir_cuenta(cursor, fila):
        rol = Rol(
            id_rol=fila["id_rol"], nombre=fila["nombre_rol"],
            descripcion=fila["descripcion_rol"], activo=fila["rol_activo"],
        )
        cargar_permisos_roles(cursor, [rol])
        estado = EstadoCuenta(fila["estado_cuenta"])
        # Los registros heredados conservan la restricción más segura.
        if not fila["activo"] and estado == EstadoCuenta.ACTIVA:
            estado = EstadoCuenta.INACTIVA
        return UsuarioSistema(
            id_usuario=fila["id_usuario"], persona=FabricaPersona.construir(fila),
            rol=rol, credenciales=Credenciales(fila["nombre_usuario"], fila["contrasena_hash"]),
            ultimo_acceso=fila["ultimo_acceso"], estado_cuenta=estado,
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
            JOIN rol r ON r.id_rol = u.id_rol_ref
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
        valores = (
            usuario.persona.dni, usuario.rol.id_rol,
            usuario.credenciales.nombre_usuario, usuario.credenciales.contrasena_hash,
            usuario.activo, usuario.estado_cuenta.value,
        )
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute("SELECT nombre,activo FROM rol WHERE id_rol=%s FOR UPDATE", (usuario.rol.id_rol,))
            rol = cursor.fetchone()
            if not rol or not rol["activo"] or rol["nombre"] != NombreRol.USUARIO:
                raise ValueError("El rol Usuario debe estar activo para crear cuentas.")
            cursor.execute("SELECT estado FROM persona WHERE dni=%s FOR UPDATE", (usuario.persona.dni,))
            persona = cursor.fetchone()
            if not persona or persona["estado"] != "ACTIVA":
                raise ValueError("La persona debe estar activa para crear su cuenta.")
            cursor.execute(
                "INSERT INTO usuario_sistema "
                "(dni_persona,id_rol_ref,nombre_usuario,contrasena_hash,activo,estado_cuenta) "
                "VALUES (%s,%s,%s,%s,%s,%s)", valores,
            )
            nuevo_id = cursor.lastrowid
        usuario.id_usuario = nuevo_id
        return usuario

    @staticmethod
    def _validar_cambio_acceso(cuenta_actual, cuentas, roles, id_rol, activar, id_usuario_actor):
        id_rol_nuevo = cuenta_actual["id_rol_ref"]
        if id_rol is not None:
            id_rol_nuevo = id_rol

        if id_rol_nuevo not in roles:
            raise ValueError("Selecciona un rol activo.")

        rol_activo = roles[id_rol_nuevo]["activo"]
        cambia_rol = id_rol_nuevo != cuenta_actual["id_rol_ref"]
        if cambia_rol and not rol_activo:
            raise ValueError("Selecciona un rol activo.")

        persona_activa = cuenta_actual["estado_persona"] == "ACTIVA"
        if activar is True and (not persona_activa or not rol_activo):
            raise ValueError("Para activar la cuenta, la persona y su rol deben estar activos.")

        es_cuenta_propia = id_usuario_actor == cuenta_actual["id_usuario"]
        if activar is False and es_cuenta_propia:
            raise ValueError("No puedes desactivar la cuenta con la que estás trabajando.")

        cuenta_nueva = dict(cuenta_actual)
        cuenta_nueva["id_rol_ref"] = id_rol_nuevo
        if activar is not None:
            cuenta_nueva["activo"] = activar
            if activar:
                cuenta_nueva["estado_cuenta"] = EstadoCuenta.ACTIVA.value
            else:
                cuenta_nueva["estado_cuenta"] = EstadoCuenta.INACTIVA.value

        era_administrador = es_administrador_activo(cuenta_actual, roles)
        seguira_siendo_administrador = es_administrador_activo(cuenta_nueva, roles)
        if era_administrador and not seguira_siendo_administrador:
            hay_otro_administrador = False
            for cuenta in cuentas:
                if cuenta["id_usuario"] == cuenta_actual["id_usuario"]:
                    continue
                if es_administrador_activo(cuenta, roles):
                    hay_otro_administrador = True
                    break
            if not hay_otro_administrador:
                raise ValueError("Debe conservarse al menos una cuenta administradora activa.")

        return cuenta_nueva

    @staticmethod
    def _persistir_cambio_acceso(
        cursor, cuenta_nueva, nombre_usuario, id_rol, contrasena_hash, activar,
    ):
        columnas, valores = [], []
        for campo, valor in (
            ("nombre_usuario", nombre_usuario), ("id_rol_ref", id_rol),
            ("contrasena_hash", contrasena_hash),
        ):
            if valor is not None:
                columnas.append(campo + "=%s")
                valores.append(valor)
        if activar is not None:
            columnas.extend(["activo=%s", "estado_cuenta=%s"])
            valores.extend([activar, cuenta_nueva["estado_cuenta"]])
        if columnas:
            cursor.execute(
                "UPDATE usuario_sistema SET " + ",".join(columnas) + " WHERE id_usuario=%s",
                (*valores, cuenta_nueva["id_usuario"]),
            )

    def actualizar_cuenta(
        self, id_usuario, nombre_usuario=None, id_rol=None, contrasena_hash=None,
        activar=None, id_usuario_actor=None,
    ) -> UsuarioSistema:
        if activar is not None and not isinstance(activar, bool):
            raise ValueError("El estado de activación no es válido.")
        with self.conexion.sesion(escritura=True) as cursor:
            roles, cuentas = bloquear_cuentas_y_roles(cursor)
            cuenta_actual = None
            for cuenta in cuentas:
                if cuenta["id_usuario"] == id_usuario:
                    cuenta_actual = cuenta
                    break
            if cuenta_actual is None:
                raise LookupError("No se encontró la cuenta de usuario.")
            edita_cuenta = any(valor is not None for valor in (nombre_usuario, contrasena_hash, activar))
            if (edita_cuenta and id_usuario_actor != id_usuario
                    and roles[cuenta_actual["id_rol_ref"]]["nombre"] == NombreRol.ADMINISTRADOR):
                actor = next((c for c in cuentas if c["id_usuario"] == id_usuario_actor), None)
                if not actor or not es_administrador_activo(actor, roles):
                    raise PermissionError("Solo un administrador puede modificar esta cuenta.")
            cuenta_nueva = self._validar_cambio_acceso(
                cuenta_actual, cuentas, roles, id_rol, activar, id_usuario_actor,
            )
            self._persistir_cambio_acceso(
                cursor, cuenta_nueva, nombre_usuario, id_rol, contrasena_hash, activar,
            )
            if activar is False or contrasena_hash is not None:
                cursor.execute("DELETE FROM sesion_acceso WHERE id_usuario=%s", (id_usuario,))
        return self.consultar_cuenta_por_id(id_usuario)

    def registrar_acceso(self, id_usuario) -> None:
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute(
                "UPDATE usuario_sistema SET ultimo_acceso=UTC_TIMESTAMP() WHERE id_usuario=%s",
                (id_usuario,),
            )

    def abrir_sesion(self, id_usuario, token, segundos):
        if randbelow(100) == 0:
            with self.conexion.sesion(escritura=True) as c:
                c.execute("DELETE FROM sesion_acceso WHERE vence <= UTC_TIMESTAMP() LIMIT 100")
        with self.conexion.sesion(escritura=True) as c:
            c.execute(
                "INSERT INTO sesion_acceso (token_hash,id_usuario,vence) "
                "VALUES (%s,%s,DATE_ADD(UTC_TIMESTAMP(), INTERVAL %s SECOND))",
                (sha256(token.encode()).digest(), id_usuario, segundos),
            )

    def sesion_vigente(self, id_usuario, token):
        with self.conexion.sesion() as c:
            c.execute(
                "SELECT 1 FROM sesion_acceso WHERE token_hash=%s AND id_usuario=%s AND vence>UTC_TIMESTAMP()",
                (sha256(token.encode()).digest(), id_usuario),
            )
            return c.fetchone() is not None

    def cerrar_sesion(self, token):
        with self.conexion.sesion(escritura=True) as c:
            c.execute("DELETE FROM sesion_acceso WHERE token_hash=%s", (sha256(token.encode()).digest(),))

    def reservar_intento(self, usuario, origen):
        # Reservar antes de verificar la clave limita también solicitudes simultáneas.
        with self.conexion.sesion(escritura=True) as c:
            c.execute("SELECT FLOOR(UNIX_TIMESTAMP()/600) AS ventana")
            ventana = int(c.fetchone()["ventana"])
            for tipo, clave, limite in (("ORIGEN", origen, 50), ("USUARIO", usuario, 8)):
                c.execute(
                    "INSERT INTO intento_acceso (tipo,clave,ventana,intentos) VALUES (%s,%s,%s,1) "
                    "ON DUPLICATE KEY UPDATE intentos=IF(ventana=%s,LEAST(intentos+1,%s),1),ventana=%s",
                    (tipo, clave, ventana, ventana, limite + 1, ventana),
                )
                c.execute(
                    "SELECT intentos FROM intento_acceso WHERE tipo=%s AND clave=%s FOR UPDATE",
                    (tipo, clave),
                )
                if c.fetchone()["intentos"] > limite:
                    return None
        if randbelow(100) == 0:
            with self.conexion.sesion(escritura=True) as c:
                c.execute("DELETE FROM intento_acceso WHERE ventana<%s LIMIT 100", (ventana - 1,))
        return ventana

    def descontar_intento_exitoso(self, usuario, origen, ventana):
        with self.conexion.sesion(escritura=True) as c:
            for tipo, clave in (("ORIGEN", origen), ("USUARIO", usuario)):
                c.execute(
                    "UPDATE intento_acceso SET intentos=intentos-1 "
                    "WHERE tipo=%s AND clave=%s AND ventana=%s AND intentos>0",
                    (tipo, clave, ventana),
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
                   u.nombre_usuario, r.id_rol, r.nombre AS nombre_rol, u.estado_cuenta
            FROM usuario_sistema u
            JOIN persona p ON p.dni=u.dni_persona
            JOIN rol r ON r.id_rol=u.id_rol_ref
            LEFT JOIN estudiante e ON e.dni=p.dni
            WHERE """ + " AND ".join(condiciones) + " ORDER BY p.apellidos,p.nombres,u.id_usuario LIMIT %s"
        with self.conexion.sesion() as cursor:
            cursor.execute(consulta, (*valores, limite))
            return cursor.fetchall()

    def actualizar_rol_cuenta(self, id_usuario: int, id_rol: int, id_usuario_actor: int) -> UsuarioSistema:
        # Reutiliza la misma validación bajo bloqueo que protege los cambios de acceso.
        return self.actualizar_cuenta(id_usuario, id_rol=id_rol, id_usuario_actor=id_usuario_actor)
