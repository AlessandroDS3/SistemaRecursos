from __future__ import annotations
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
           p.dni, p.nombres, p.apellidos, p.dni AS documento_identidad,
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
    def _construir_cuentas(cursor, filas_usuario):
        roles_por_id = {}
        for fila_usuario in filas_usuario:
            id_rol = fila_usuario["id_rol"]
            if id_rol not in roles_por_id:
                roles_por_id[id_rol] = Rol(
                    id_rol=id_rol, nombre=fila_usuario["nombre_rol"],
                    descripcion=fila_usuario["descripcion_rol"], activo=fila_usuario["rol_activo"],
                )
        cargar_permisos_roles(cursor, roles_por_id.values())
        cuentas = []
        for fila_usuario in filas_usuario:
            estado = EstadoCuenta(fila_usuario["estado_cuenta"])
            # Los registros heredados conservan la restricción más segura.
            if not fila_usuario["activo"] and estado == EstadoCuenta.ACTIVA:
                estado = EstadoCuenta.INACTIVA
            cuentas.append(UsuarioSistema(
                id_usuario=fila_usuario["id_usuario"],
                persona=FabricaPersona.construir(fila_usuario),
                rol=roles_por_id[fila_usuario["id_rol"]],
                credenciales=Credenciales(
                    fila_usuario["nombre_usuario"], fila_usuario["contrasena_hash"],
                ),
                ultimo_acceso=fila_usuario["ultimo_acceso"], estado_cuenta=estado,
            ))
        return cuentas

    def _consultar(self, campo, valor):
        columna = COLUMNAS_BUSQUEDA_CUENTA[campo]
        with self.conexion.sesion() as cursor:
            cursor.execute(CONSULTA_CUENTAS + f" WHERE {columna}=%s", (valor,))
            fila_usuario = cursor.fetchone()
            if fila_usuario is None:
                return None
            return self._construir_cuentas(cursor, [fila_usuario])[0]

    def consultar_por_nombre_usuario(self, nombre_usuario) -> UsuarioSistema | None:
        return self._consultar("nombre_usuario", nombre_usuario)

    def consultar_cuenta_persona(self, dni) -> UsuarioSistema | None:
        return self._consultar("dni_persona", dni)

    def consultar_cuenta_por_id(self, id_usuario) -> UsuarioSistema | None:
        return self._consultar("id_usuario", id_usuario)

    def consultar_cuentas(self) -> list[UsuarioSistema]:
        with self.conexion.sesion() as cursor:
            cursor.execute(CONSULTA_CUENTAS + " ORDER BY u.nombre_usuario, u.id_usuario")
            return self._construir_cuentas(cursor, cursor.fetchall())

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
            cuenta_nueva = self._validar_cambio_acceso(
                cuenta_actual, cuentas, roles, id_rol, activar, id_usuario_actor,
            )
            self._persistir_cambio_acceso(
                cursor, cuenta_nueva, nombre_usuario, id_rol, contrasena_hash, activar,
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
