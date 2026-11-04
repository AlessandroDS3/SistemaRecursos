from __future__ import annotations
from dominio.gestion_personas_usuarios.persona import Persona
from dominio.resultados_consulta import ResultadoPersonas
from typing import Any
from dominio.gestion_personas_usuarios.i_repositorio_persona import IRepositorioPersona
from dominio.gestion_personas_usuarios.fabrica_persona import FabricaPersona
from repositorio.conexion_mysql import MySQLConnection
from repositorio.proteccion_administradores_sql import bloquear_cuentas_y_roles, validar_baja_persona
from dominio.gestion_personas_usuarios.persona import EstadoPersona
from dominio.gestion_personas_usuarios.validacion_persona import ValidacionPersonaError
from dominio.gestion_personas_usuarios.estudiante import ESTADOS_MATRICULA_VIGENTE

BASE = ("dni", "nombres", "apellidos", "telefono", "correo", "estado")
SUBTIPOS = {
    "ESTUDIANTE": (
        "estudiante",
        ("cui", "ciclo", "semestre_academico", "estado_matricula"),
    ),
    "DOCENTE": (
        "docente",
        ("codigo_docente", "departamento_academico", "facultad", "escuela_profesional"),
    ),
    "ADMINISTRATIVO": ("administrativo", ("codigo_empleado", "area")),
}
CONSULTA = """SELECT p.*, e.cui, e.ciclo,
    e.semestre_academico, e.estado_matricula, d.codigo_docente,
    d.departamento_academico, d.facultad, d.escuela_profesional,
    a.codigo_empleado, a.area,
    CASE WHEN e.dni IS NOT NULL THEN 'ESTUDIANTE'
         WHEN d.dni IS NOT NULL THEN 'DOCENTE'
         WHEN a.dni IS NOT NULL THEN 'ADMINISTRATIVO' END AS tipo
    FROM persona p LEFT JOIN estudiante e ON e.dni=p.dni
    LEFT JOIN docente d ON d.dni=p.dni
    LEFT JOIN administrativo a ON a.dni=p.dni"""


COLUMNAS_BUSQUEDA = ("p.apellidos", "p.dni", "e.cui")
COLUMNA_POR_TIPO = {
    "ESTUDIANTE": "e.dni",
    "DOCENTE": "d.dni",
    "ADMINISTRATIVO": "a.dni",
}
EXISTE_CUENTA = """
    EXISTS (
        SELECT 1 FROM usuario_sistema us
        WHERE us.dni_persona = p.dni
    )
"""
ACCESO_ACTIVO = """
    EXISTS (
        SELECT 1
        FROM usuario_sistema us
        JOIN rol r ON r.id_rol = us.id_rol_ref
        WHERE us.dni_persona = p.dni
          AND us.activo = TRUE
          AND us.estado_cuenta = 'ACTIVA'
          AND r.activo = TRUE
          AND p.estado = 'ACTIVA'
    )
"""
CONDICIONES_CUENTA = {
    "CON_ACCESO": ACCESO_ACTIVO,
    "SIN_CUENTA": f"NOT {EXISTE_CUENTA}",
    "ACCESO_INACTIVO": f"{EXISTE_CUENTA} AND NOT {ACCESO_ACTIVO}",
}


class RepositorioPersonaSQL(IRepositorioPersona):
    def __init__(self, conexion=None):
        self.conexion = conexion or MySQLConnection()

    @staticmethod
    def _validar_identificadores(cursor, persona, dni_actual=None):
        cursor.execute("SELECT dni FROM persona WHERE dni=%s AND dni<>%s",
                       (persona.dni, dni_actual or ""))
        if cursor.fetchone():
            raise ValidacionPersonaError({"dni": "Este DNI ya está registrado."})
        if persona.tipo == "ESTUDIANTE":
            cursor.execute("SELECT dni FROM estudiante WHERE cui=%s AND dni<>%s",
                           (persona.cui, dni_actual or ""))
            if cursor.fetchone():
                raise ValidacionPersonaError({"cui": "Este CUI ya está registrado."})

    def registrar_persona(self, persona) -> Persona:
        tabla, columnas = SUBTIPOS[persona.tipo]
        with self.conexion.sesion(escritura=True) as cursor:
            self._validar_identificadores(cursor, persona)
            cursor.execute(
                f"INSERT INTO persona ({', '.join(BASE)}) VALUES ({', '.join(['%s'] * len(BASE))})",
                tuple(getattr(persona, campo) for campo in BASE),
            )
            cursor.execute(
                f"INSERT INTO {tabla} (dni, {', '.join(columnas)}) VALUES ({', '.join(['%s'] * (len(columnas)+1))})",
                (persona.dni, *(getattr(persona, campo) for campo in columnas)),
            )
        return persona

    def consultar_persona(self, dni) -> Persona | None:
        with self.conexion.sesion() as c:
            c.execute(CONSULTA + " WHERE p.dni=%s", (dni,))
            fila = c.fetchone()
            return FabricaPersona.construir(fila) if fila else None

    @staticmethod
    def _filtros_sql(filtros):
        condiciones = []
        parametros = []
        termino = filtros.get("q", "").strip().casefold()
        condicion_busqueda = "(" + " OR ".join(
            f"{columna} LIKE %s" for columna in COLUMNAS_BUSQUEDA
        ) + ")"
        for palabra in termino.split():
            if len(palabra) >= 2:
                condiciones.append(condicion_busqueda)
                parametros.extend([f"{palabra}%"] * len(COLUMNAS_BUSQUEDA))

        tipo = filtros.get("tipo")
        if tipo:
            condiciones.append(f"{COLUMNA_POR_TIPO[tipo]} IS NOT NULL")
        if filtros.get("estado"):
            condiciones.append("p.estado = %s")
            parametros.append(filtros["estado"])

        condicion_cuenta = CONDICIONES_CUENTA.get(filtros.get("cuenta"))
        if condicion_cuenta:
            condiciones.append(f"({condicion_cuenta})")
        return condiciones, parametros

    def consultar_personas(self, filtros) -> ResultadoPersonas:
        condiciones, valores = self._filtros_sql(filtros)
        where = " WHERE " + " AND ".join(condiciones) if condiciones else ""
        with self.conexion.sesion() as c:
            c.execute(
                "SELECT COUNT(*) AS total, "
                "SUM(p.estado = 'ACTIVA') AS activas, "
                "SUM(p.estado = 'INACTIVA') AS inactivas "
                "FROM persona p "
                "LEFT JOIN estudiante e ON e.dni = p.dni "
                "LEFT JOIN docente d ON d.dni = p.dni "
                "LEFT JOIN administrativo a ON a.dni = p.dni"
                + where,
                tuple(valores),
            )
            resumen = c.fetchone()
            total = int(resumen["total"] or 0)
            c.execute(
                CONSULTA + where
                + " ORDER BY p.apellidos, p.nombres",
                tuple(valores),
            )
            personas = [FabricaPersona.construir(fila) for fila in c.fetchall()]
        return {
            "personas": personas,
            "resumen": {
                "total": total,
                "activas": int(resumen["activas"] or 0),
                "inactivas": int(resumen["inactivas"] or 0),
            },
        }

    def consultar_solicitantes(self, texto, limite=20) -> list[dict[str, Any]]:
        palabras = [palabra for palabra in texto.casefold().split() if len(palabra) >= 2]
        if not palabras:
            return []
        condiciones = []
        valores = []
        for palabra in palabras:
            condiciones.append("""(
                p.apellidos LIKE %s
                OR p.dni LIKE %s
                OR COALESCE(e.cui, '') LIKE %s
            )""")
            valores.extend([f"{palabra}%"] * 3)
        limite = max(1, min(int(limite), 20))
        termino = texto.casefold().strip()
        sql = """
            SELECT p.dni, p.nombres, p.apellidos,
                   p.dni AS documento_identidad, e.cui,
                   p.estado AS estado_persona,
                   e.estado_matricula,
                   CASE WHEN p.estado='ACTIVA'
                         AND (e.dni IS NULL OR UPPER(TRIM(e.estado_matricula)) IN ({estados_matricula}))
                        THEN 1 ELSE 0 END AS elegible,
                   CASE WHEN e.dni IS NOT NULL THEN 'ESTUDIANTE'
                        WHEN d.dni IS NOT NULL THEN 'DOCENTE'
                        ELSE 'ADMINISTRATIVO' END AS tipo
            FROM persona p
            LEFT JOIN estudiante e ON e.dni=p.dni
            LEFT JOIN docente d ON d.dni=p.dni
            LEFT JOIN administrativo a ON a.dni=p.dni
            WHERE {condiciones}
            ORDER BY CASE WHEN COALESCE(e.cui,'') = %s
                            OR p.dni = %s THEN 0
                          ELSE 1 END,
                elegible DESC,
                p.apellidos, p.nombres
            LIMIT %s
        """.format(
            condiciones=" AND ".join(condiciones),
            estados_matricula=", ".join(["%s"] * len(ESTADOS_MATRICULA_VIGENTE)),
        )
        valores = [*ESTADOS_MATRICULA_VIGENTE, *valores, termino, termino, limite]
        with self.conexion.sesion() as c:
            c.execute(sql, tuple(valores))
            return c.fetchall()
    @staticmethod
    def _bloquear_persona_para_cambio(cursor, dni, estado_nuevo, id_usuario_actor):
        roles, cuentas = {}, []
        if estado_nuevo == EstadoPersona.INACTIVA:
            roles, cuentas = bloquear_cuentas_y_roles(cursor)
        cursor.execute(
            "SELECT dni,estado FROM persona WHERE dni=%s FOR UPDATE",
            (dni,),
        )
        if cursor.fetchone() is None:
            raise LookupError("No se encontró la persona.")
        if estado_nuevo == EstadoPersona.INACTIVA:
            validar_baja_persona(dni, id_usuario_actor, cuentas, roles)

    def actualizar_persona(self, persona, dni_actual, id_usuario_actor=None) -> Persona:
        tabla, columnas = SUBTIPOS[persona.tipo]
        with self.conexion.sesion(escritura=True) as cursor:
            self._bloquear_persona_para_cambio(cursor, dni_actual, persona.estado, id_usuario_actor)
            self._validar_identificadores(cursor, persona, dni_actual)
            cursor.execute(f"SELECT dni FROM {tabla} WHERE dni=%s FOR UPDATE", (dni_actual,))
            if cursor.fetchone() is None:
                raise LookupError("No se encontró el registro del tipo de persona.")
            cursor.execute(
                f"UPDATE persona SET {', '.join(campo+'=%s' for campo in BASE)} WHERE dni=%s",
                (*(getattr(persona, campo) for campo in BASE), dni_actual),
            )
            cursor.execute(
                f"UPDATE {tabla} SET {', '.join(campo+'=%s' for campo in columnas)} WHERE dni=%s",
                (*(getattr(persona, campo) for campo in columnas), persona.dni),
            )
        return persona

    def desactivar_persona(self, dni, id_usuario_actor=None) -> None:
        # Baja lógica: conserva las referencias para préstamos e historial.
        with self.conexion.sesion(escritura=True) as cursor:
            self._bloquear_persona_para_cambio(
                cursor, dni, EstadoPersona.INACTIVA, id_usuario_actor,
            )
            cursor.execute("UPDATE persona SET estado='INACTIVA' WHERE dni=%s", (dni,))
