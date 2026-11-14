from __future__ import annotations
from dominio.recursos import (
    CategoriaRecurso,
    IRepositorioRecurso,
    Recurso,
    RecursoListado,
    crear_bien_material,
    crear_recurso,
)
from repositorio.conexion_mysql import MySQLConnection
from repositorio.repositorio_bien_material_sql import insertar_bien_material


# Columnas que se reutilizan en las consultas de recursos y categorías.
CAMPOS_RECURSO = (
    "id_recurso", "id_categoria", "nombre", "marca", "modelo", "descripcion",
)
COLUMNAS_RECURSO = ", ".join(CAMPOS_RECURSO)
COLUMNAS_RECURSO_LISTADO = ", ".join(f"r.{campo}" for campo in CAMPOS_RECURSO)
COLUMNAS_CATEGORIA = "id_categoria, nombre, descripcion"


class RepositorioRecursoSQL(IRepositorioRecurso):
    """Consulta y guarda recursos, su primer bien y categorías en MySQL."""

    # 1. Preparar la conexión a MySQL.
    def __init__(self, conexion=None):
        self.conexion = conexion or MySQLConnection()

    #Consultar y el detalle de los recursos.
    def consultar_recursos(self, filtros=None) -> list[RecursoListado]:
        sql, parametros = self._consulta_todos(filtros)
        with self.conexion.sesion() as cursor:
            cursor.execute(sql + " ORDER BY r.nombre, r.id_recurso", parametros)
            return cursor.fetchall()

    def consultar_recurso(self, id_recurso) -> Recurso | None:
        """Busca un recurso por su ID"""
        with self.conexion.sesion() as cursor:
            cursor.execute(
                f"SELECT {COLUMNAS_RECURSO} FROM recurso WHERE id_recurso = %s", (id_recurso,)
            )
            fila_recurso = cursor.fetchone()
            return crear_recurso(fila_recurso) if fila_recurso else None

    # Registrar, actualizar y eliminar recursos.
    def registrar_recurso(self, recurso) -> Recurso:
        """Guarda el recurso y le asigna el ID generado por MySQL."""
        with self.conexion.sesion(escritura=True) as cursor:
            nuevo_id = self._insertar_recurso(cursor, recurso)
        recurso.id_recurso = nuevo_id
        return recurso

    def registrar_recurso_con_bien(self, recurso, datos_bien) -> Recurso:
        with self.conexion.sesion(escritura=True) as cursor:
            nuevo_id = self._insertar_recurso(cursor, recurso)
            bien = crear_bien_material(
                dict(datos_bien, id_recurso=nuevo_id, estado="DISPONIBLE", id_bien=None)
            )
            insertar_bien_material(cursor, bien)
        recurso.id_recurso = nuevo_id
        return recurso

    def actualizar_recurso(self, recurso) -> Recurso:
        with self.conexion.sesion(escritura=True) as cursor:
            # FOR UPDATE bloquea el registro hasta que termine la transacción.
            cursor.execute(
                "SELECT id_recurso FROM recurso WHERE id_recurso=%s FOR UPDATE",
                (recurso.id_recurso,),
            )
            if cursor.fetchone() is None:
                raise LookupError("No se encontró el recurso.")
            cursor.execute(
                """
                UPDATE recurso
                SET nombre = %s, id_categoria = %s,
                    marca = %s, modelo = %s, descripcion = %s
                WHERE id_recurso = %s
                """,
                (
                    recurso.nombre,
                    recurso.id_categoria,
                    recurso.marca,
                    recurso.modelo,
                    recurso.descripcion,
                    recurso.id_recurso,
                ),
            )
        return recurso

    def eliminar_recurso(self, id_recurso) -> None:
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute("DELETE FROM recurso WHERE id_recurso=%s", (id_recurso,))

    # 4. Consultar y administrar las categorías.
    def consultar_categorias(self) -> list[CategoriaRecurso]:
        with self.conexion.sesion() as cursor:
            cursor.execute(f"SELECT {COLUMNAS_CATEGORIA} FROM categoria_recurso ORDER BY nombre")
            return [CategoriaRecurso(**fila_categoria) for fila_categoria in cursor.fetchall()]

    def consultar_categoria(self, id_categoria) -> CategoriaRecurso | None:
        with self.conexion.sesion() as cursor:
            cursor.execute(
                f"SELECT {COLUMNAS_CATEGORIA} FROM categoria_recurso WHERE id_categoria = %s",
                (id_categoria,),
            )
            fila_categoria = cursor.fetchone()
            return CategoriaRecurso(**fila_categoria) if fila_categoria else None

    def registrar_categoria(self, categoria) -> CategoriaRecurso:
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute(
                "INSERT INTO categoria_recurso (nombre,descripcion) VALUES (%s,%s)",
                (categoria.nombre, categoria.descripcion),
            )
            nuevo_id = cursor.lastrowid
        categoria.id_categoria = nuevo_id
        return categoria

    def actualizar_categoria(self, categoria) -> CategoriaRecurso:
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute(
                "SELECT id_categoria FROM categoria_recurso WHERE id_categoria=%s FOR UPDATE",
                (categoria.id_categoria,),
            )
            if cursor.fetchone() is None:
                raise LookupError("No se encontró la categoría.")
            cursor.execute(
                """
                UPDATE categoria_recurso
                SET nombre = %s, descripcion = %s
                WHERE id_categoria = %s
                """,
                (categoria.nombre, categoria.descripcion, categoria.id_categoria),
            )
        return categoria

    def eliminar_categoria(self, id_categoria) -> None:
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute("DELETE FROM categoria_recurso WHERE id_categoria=%s", (id_categoria,))

    # 5. Preparar las consultas y la inserción de recursos.
    @staticmethod
    def _consulta_todos(filtros=None):
        filtros = filtros or {}
        # Las condiciones forman el WHERE; los valores se envían por separado.
        condiciones, parametros = [], []
        if filtros.get("q"):
            estado_codigo = " AND buscado.estado=%s" if filtros.get("estado") else ""
            condiciones.append(
                "(r.nombre LIKE %s OR r.marca LIKE %s OR r.modelo LIKE %s "
                "OR EXISTS (SELECT 1 FROM bien_material buscado "
                "WHERE buscado.id_recurso=r.id_recurso AND buscado.codigo_inventario LIKE %s"
                + estado_codigo + "))"
            )
            parametros.extend([filtros["q"] + "%"] * 4)
            if filtros.get("estado"):
                parametros.append(filtros["estado"])
        if filtros.get("estado"):
            condiciones.append("EXISTS (SELECT 1 FROM bien_material filtrado WHERE filtrado.id_recurso=r.id_recurso AND filtrado.estado=%s)")
            parametros.append(filtros["estado"])
        if filtros.get("id_categoria"):
            condiciones.append("r.id_categoria=%s")
            parametros.append(filtros["id_categoria"])
        if filtros.get('id_recurso'):
            condiciones.append('r.id_recurso=%s')
            parametros.append(filtros['id_recurso'])
        if filtros.get('id_bien'):
            condiciones.append('EXISTS (SELECT 1 FROM bien_material elegido WHERE elegido.id_recurso=r.id_recurso AND elegido.id_bien=%s)')
            parametros.append(filtros['id_bien'])
        # Incluye los recursos sin bienes y cuenta los bienes de cada recurso.
        sql = f"""
            SELECT {COLUMNAS_RECURSO_LISTADO}, cat.nombre AS categoria_nombre,
                COUNT(b.id_bien) AS total_bienes,
                SUM(CASE WHEN b.estado='DISPONIBLE' THEN 1 ELSE 0 END) AS disponibles
            FROM recurso r JOIN categoria_recurso cat ON cat.id_categoria=r.id_categoria
            LEFT JOIN bien_material b ON b.id_recurso=r.id_recurso
        """
        if condiciones:
            sql += " WHERE " + " AND ".join(condiciones)
        sql += " GROUP BY r.id_recurso, cat.id_categoria"
        # HAVING filtra el resultado después de contar los bienes disponibles.
        if filtros.get("solo_disponibles"):
            sql += " HAVING disponibles > 0"
        return sql, tuple(parametros)

    @staticmethod
    def _insertar_recurso(cursor, recurso):
        """Inserta el recurso con el cursor recibido y devuelve su ID."""
        # Los marcadores %s reciben los valores enviados en la tupla.
        cursor.execute(
            """
            INSERT INTO recurso (
                nombre, id_categoria, marca, modelo, descripcion
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                recurso.nombre,
                recurso.id_categoria,
                recurso.marca,
                recurso.modelo,
                recurso.descripcion,
            ),
        )
        return cursor.lastrowid
