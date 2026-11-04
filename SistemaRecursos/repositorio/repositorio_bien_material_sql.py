from __future__ import annotations
from dominio.gestion_recursos.bien_material import BienMaterial
from dominio.resultados_consulta import BienDisponible, BienListado, ResultadoBienes
from typing import Any
from dominio.gestion_recursos.i_repositorio_bien_material import IRepositorioBienMaterial
from dominio.gestion_recursos.fabrica_bien_material import FabricaBienMaterial
from dominio.gestion_recursos.registro_fuera_servicio import RegistroFueraServicio
from dominio.gestion_recursos.validacion_recurso import ConflictoRecursoError
from repositorio.conexion_mysql import MySQLConnection
from repositorio.registro_fuera_servicio_sql import guardar_cambio_fuera_servicio
from dominio.gestion_recursos.bien_material import (
    ESTADOS_CAMBIO_MANUAL, ESTADOS_GESTION_PRESTAMOS,
)


CAMPOS_BIEN = (
    "id_bien", "id_recurso_ref", "codigo_inventario", "numero_serie",
    "fecha_adquisicion", "estado", "ubicacion", "descripcion_bien",
)
COLUMNAS_BIEN = ", ".join(CAMPOS_BIEN)
COLUMNAS_BIEN_LISTADO = ", ".join(f"bien.{campo}" for campo in CAMPOS_BIEN)
ORIGEN_LISTADO = """
    FROM bien_material bien
    JOIN recurso ON recurso.id_recurso=bien.id_recurso_ref
"""


class RepositorioBienMaterialSQL(IRepositorioBienMaterial):
    def __init__(self, conexion=None):
        self.conexion = conexion or MySQLConnection()

    def registrar_bien_material(self, bien_material) -> BienMaterial:
        with self.conexion.sesion(escritura=True) as cursor:
            nuevo_id = insertar_bien_material(cursor, bien_material)
        bien_material.id_bien = nuevo_id
        return bien_material

    def existen_por_recurso(self, id_recurso) -> bool:
        with self.conexion.sesion() as cursor:
            cursor.execute(
                "SELECT 1 AS existe FROM bien_material WHERE id_recurso_ref=%s LIMIT 1",
                (id_recurso,),
            )
            return cursor.fetchone() is not None

    def consultar_bien_material(self, id_bien) -> BienMaterial | None:
        with self.conexion.sesion() as cursor:
            cursor.execute(f"SELECT {COLUMNAS_BIEN} FROM bien_material WHERE id_bien=%s", (id_bien,))
            fila_bien = cursor.fetchone()
            return FabricaBienMaterial.construir(fila_bien) if fila_bien else None

    def contar_disponibles(self) -> int:
        with self.conexion.sesion() as cursor:
            cursor.execute("SELECT COUNT(*) AS cantidad FROM bien_material WHERE estado='DISPONIBLE'")
            fila_resumen = cursor.fetchone()
            return int(fila_resumen["cantidad"] or 0)

    def consultar_bienes_por_recurso(self, id_recurso=None) -> list[BienListado]:
        sql = f"""SELECT {COLUMNAS_BIEN_LISTADO}, recurso.nombre AS recurso_nombre
            {ORIGEN_LISTADO}
        """
        valores = ()
        if id_recurso is not None:
            sql += " WHERE bien.id_recurso_ref=%s"
            valores = (id_recurso,)
        with self.conexion.sesion() as cursor:
            cursor.execute(sql + " ORDER BY recurso.nombre,bien.codigo_inventario", valores)
            return cursor.fetchall()

    @staticmethod
    def _filtros_sql(filtros):
        condiciones, parametros = [], []
        if filtros.get("q"):
            condiciones.append("""(
                bien.codigo_inventario LIKE %s OR recurso.nombre LIKE %s
                OR COALESCE(bien.numero_serie, '') LIKE %s
                OR COALESCE(bien.ubicacion, '') LIKE %s
            )""")
            parametros.extend([f"{filtros['q']}%"] * 4)
        if filtros.get("estado"):
            condiciones.append("bien.estado=%s")
            parametros.append(filtros["estado"])
        if filtros.get("id_recurso"):
            condiciones.append("bien.id_recurso_ref=%s")
            parametros.append(filtros["id_recurso"])
        clausula_where = " WHERE " + " AND ".join(condiciones) if condiciones else ""
        return clausula_where, tuple(parametros)



    def consultar_bienes_materiales(self, filtros) -> ResultadoBienes:
        clausula_where, parametros = self._filtros_sql(filtros or {})
        with self.conexion.sesion() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS total, "
                "SUM(bien.estado='DISPONIBLE') AS disponibles, "
                "SUM(bien.estado='PRESTADO') AS prestados, "
                "SUM(bien.estado='MANTENIMIENTO') AS mantenimiento "
                + ORIGEN_LISTADO + clausula_where,
                parametros,
            )
            resumen = cursor.fetchone()
            cursor.execute(
                f"SELECT {COLUMNAS_BIEN_LISTADO}, recurso.nombre AS recurso_nombre "
                + ORIGEN_LISTADO + clausula_where
                + " ORDER BY recurso.nombre,bien.codigo_inventario",
                parametros,
            )
            bienes = cursor.fetchall()
        return {
            "bienes": bienes,
            "resumen": {campo: int(resumen[campo] or 0) for campo in (
                "total", "disponibles", "prestados", "mantenimiento",
            )},
        }

    def consultar_bienes_disponibles(self, texto="", id_recurso=None) -> list[BienDisponible]:
        condiciones = ["bien.estado='DISPONIBLE'"]
        valores = []
        if texto:
            condiciones.append("""(
                bien.codigo_inventario LIKE %s
                OR recurso.nombre LIKE %s
                OR COALESCE(recurso.marca, '') LIKE %s
                OR COALESCE(recurso.modelo, '') LIKE %s
            )""")
            patron = f"{texto.strip()}%"
            valores.extend([patron] * 4)
        if id_recurso is not None:
            condiciones.append("recurso.id_recurso=%s")
            valores.append(id_recurso)
        sql = """
            SELECT bien.id_bien, bien.id_recurso_ref, bien.codigo_inventario,
                   bien.ubicacion, recurso.nombre AS recurso_nombre, recurso.id_categoria_ref
            FROM bien_material bien
            JOIN recurso ON recurso.id_recurso=bien.id_recurso_ref
            WHERE {}
            ORDER BY recurso.nombre, bien.codigo_inventario

        """.format(" AND ".join(condiciones))
        with self.conexion.sesion() as cursor:
            cursor.execute(sql, tuple(valores))
            return cursor.fetchall()

    def actualizar_bien_material(self, bien_material) -> BienMaterial:
        bien = bien_material
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute(
                "SELECT id_recurso_ref FROM bien_material WHERE id_bien=%s FOR UPDATE", (bien.id_bien,)
            )
            fila_bien = cursor.fetchone()
            if not fila_bien:
                raise LookupError("No se encontró el bien.")
            if fila_bien["id_recurso_ref"] != bien.id_recurso_ref:
                raise ValueError("Un bien registrado no se puede trasladar a otro recurso.")
            # La edición de datos no altera el estado ni el recurso del bien.
            cursor.execute(
                """UPDATE bien_material SET codigo_inventario=%s,numero_serie=%s,fecha_adquisicion=%s,ubicacion=%s,descripcion_bien=%s
                WHERE id_bien=%s""",
                (bien.codigo_inventario, bien.numero_serie, bien.fecha_adquisicion, bien.ubicacion, bien.descripcion_bien, bien.id_bien),
            )
        return self.consultar_bien_material(bien.id_bien)

    def eliminar_bien_material(self, id_bien) -> None:
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute("SELECT estado FROM bien_material WHERE id_bien=%s FOR UPDATE", (id_bien,))
            fila_bien = cursor.fetchone()
            if not fila_bien:
                raise LookupError("No se encontró el bien.")
            if fila_bien["estado"] != "DISPONIBLE":
                raise ConflictoRecursoError(
                    "Solo se pueden eliminar bienes disponibles sin historial."
                )
            cursor.execute(
                "SELECT COUNT(*) AS n FROM historial_estado WHERE entidad='BIEN_MATERIAL' AND id_entidad=%s",
                (id_bien,),
            )
            if cursor.fetchone()["n"]:
                raise ConflictoRecursoError("El bien tiene historial y debe conservarse.")
            cursor.execute(
                "SELECT COUNT(*) AS n FROM registro_fuera_servicio WHERE id_bien_ref=%s", (id_bien,)
            )
            if cursor.fetchone()["n"]:
                raise ConflictoRecursoError(
                    "El bien tiene registros fuera de servicio y debe conservarse."
                )
            # Las FK protegen los bienes vinculados a préstamos o notificaciones.
            cursor.execute("DELETE FROM bien_material WHERE id_bien=%s", (id_bien,))

    def cambiar_estado_bien_material(
        self,
        id_bien,
        estado,
        motivo,
        dni_responsable,
        estado_esperado,
        fecha_fin_estimada=None,
        descripcion="",
    ) -> BienMaterial:
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute(f"SELECT {COLUMNAS_BIEN} FROM bien_material WHERE id_bien=%s FOR UPDATE", (id_bien,))
            fila_bien = cursor.fetchone()
            if not fila_bien:
                raise LookupError("No se encontró el bien.")
            bien = FabricaBienMaterial.construir(fila_bien)
            cursor.execute(
                """SELECT id_detalle
                FROM detalle_prestamo
                WHERE id_bien_ref=%s AND estado_devolucion IS NULL LIMIT 1 FOR UPDATE""",
                (id_bien,),
            )
            if cursor.fetchone():
                raise ConflictoRecursoError(
                    "El bien tiene una entrega pendiente. Su recepción debe registrarse desde el préstamo, incluso si fue reportado como perdido."
                )
            anterior = bien.estado.value
            if anterior != estado_esperado:
                raise ConflictoRecursoError(
                    "El estado cambió mientras completabas el formulario. Recarga el bien."
                )
            if bien.estado in ESTADOS_GESTION_PRESTAMOS or estado not in ESTADOS_CAMBIO_MANUAL:
                raise ConflictoRecursoError(
                    "Los bienes prestados o reservados se gestionan desde su flujo de préstamos."
                )
            bien.cambiar_estado(estado)
            cursor.execute("SELECT UTC_TIMESTAMP() AS ahora")
            ahora = cursor.fetchone()["ahora"]
            guardar_cambio_fuera_servicio(
                cursor, id_bien, estado, motivo, ahora,
                fecha_fin_estimada=fecha_fin_estimada, descripcion=descripcion,
            )
            cursor.execute("UPDATE bien_material SET estado=%s WHERE id_bien=%s", (estado, id_bien))
            cursor.execute(
                """INSERT INTO historial_estado (entidad,id_entidad,estado_anterior,estado_nuevo,fecha,observacion,dni_responsable)
                VALUES ('BIEN_MATERIAL',%s,%s,%s,UTC_TIMESTAMP(),%s,%s)""",
                (id_bien, anterior, estado, motivo, dni_responsable),
            )
        return self.consultar_bien_material(id_bien)

    def consultar_prestamo_pendiente(self, id_bien) -> int | None:
        with self.conexion.sesion() as cursor:
            cursor.execute(
                """SELECT id_prestamo
                FROM detalle_prestamo
                WHERE id_bien_ref=%s AND estado_devolucion IS NULL ORDER BY id_detalle DESC LIMIT 1""",
                (id_bien,),
            )
            fila_prestamo = cursor.fetchone()
            return fila_prestamo["id_prestamo"] if fila_prestamo else None

    def _consultar_registros(self, consulta, id_bien):
        with self.conexion.sesion() as cursor:
            cursor.execute(consulta, (id_bien,))
            return cursor.fetchall()

    def consultar_historial_bien_material(self, id_bien) -> list[dict[str, Any]]:
        return self._consultar_registros(
            """SELECT historial.id_historial_estado, historial.entidad, historial.id_entidad,
                      historial.estado_anterior, historial.estado_nuevo, historial.fecha,
                      historial.observacion, historial.dni_responsable,
                      CONCAT(persona.nombres,' ',persona.apellidos) AS responsable
               FROM historial_estado historial
               LEFT JOIN persona ON persona.dni=historial.dni_responsable
               WHERE historial.entidad='BIEN_MATERIAL' AND historial.id_entidad=%s
               ORDER BY historial.fecha DESC,historial.id_historial_estado DESC""",
            id_bien,
        )

    def consultar_registros_fuera_servicio(self, id_bien) -> list[RegistroFueraServicio]:
        filas = self._consultar_registros(
            """SELECT id_registro, id_bien_ref, motivo, fecha_inicio, fecha_fin_estimada,
                      fecha_fin_real, descripcion, estado
               FROM registro_fuera_servicio WHERE id_bien_ref=%s
               ORDER BY fecha_inicio DESC,id_registro DESC""",
            id_bien,
        )
        return [RegistroFueraServicio(**fila) for fila in filas]


def insertar_bien_material(cursor, bien):
    """Inserta con el cursor del llamante, sin abrir ni confirmar otra transacción."""
    cursor.execute(
        """
        INSERT INTO bien_material (
            id_recurso_ref, codigo_inventario, numero_serie,
            fecha_adquisicion, estado, ubicacion, descripcion_bien
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            bien.id_recurso_ref, bien.codigo_inventario, bien.numero_serie,
            bien.fecha_adquisicion, bien.estado.value, bien.ubicacion, bien.descripcion_bien,
        ),
    )
    return cursor.lastrowid


def registrar_historial_bien(
    cursor, id_bien, estado_anterior, estado_nuevo, motivo, dni_responsable,
):
    """Usa la transacción del llamante para conservar el cambio y su historial."""
    cursor.execute(
        """
        INSERT INTO historial_estado (
            entidad, id_entidad, estado_anterior, estado_nuevo,
            fecha, observacion, dni_responsable
        )
        VALUES ('BIEN_MATERIAL', %s, %s, %s, UTC_TIMESTAMP(), %s, %s)
        """,
        (id_bien, estado_anterior, estado_nuevo, motivo, dni_responsable),
    )
