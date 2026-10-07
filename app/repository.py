"""Persistencia MySQL del contexto Recursos Materiales."""
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
import mysql.connector
from .errors import ConflictError


class RecursoMySQLRepository:
    def __init__(self, config):
        self.config = dict(config)

    @contextmanager
    def connection(self):
        conn = mysql.connector.connect(**self.config)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self):
        schema = (Path(__file__).resolve().parent.parent / 'sql' / 'schema.sql').read_text(encoding='utf-8')
        with self.connection() as conn, conn.cursor() as cursor:
            for statement in schema.split(';'):
                if statement.strip():
                    cursor.execute(statement)
            cursor.executemany('''INSERT INTO categoria_recurso (idCategoria,nombre,descripcion)
                VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE idCategoria=idCategoria''', [
                (1, 'Equipos de cómputo', 'Equipos para actividades académicas.'),
                (2, 'Audiovisuales', 'Recursos para presentaciones y clases.'),
                (3, 'Bibliografía', 'Material de consulta y estudio.'),
                (4, 'Accesorios', 'Periféricos y complementos.'),
            ])

    def categorias(self):
        with self.connection() as conn, conn.cursor(dictionary=True) as cursor:
            cursor.execute('SELECT * FROM categoria_recurso ORDER BY idCategoria')
            return cursor.fetchall()

    @staticmethod
    def insert_bien(cursor, recurso_id, bien):
        try:
            cursor.execute('''INSERT INTO bien_material
                (idRecursoRef,codigoInventario,numeroSerie,fechaAdquisicion,estado,ubicacion)
                VALUES (%(idRecursoRef)s,%(codigoInventario)s,%(numeroSerie)s,
                        %(fechaAdquisicion)s,%(estado)s,%(ubicacion)s)''',
                {**asdict(bien), 'idRecursoRef': recurso_id})
        except mysql.connector.IntegrityError as exc:
            if exc.errno == 1062:
                raise ConflictError('El código de inventario ya está registrado.') from None
            raise
        return cursor.lastrowid

    def crear(self, recurso, bien):
        with self.connection() as conn, conn.cursor() as cursor:
            cursor.execute('''INSERT INTO recurso (nombre,tipo,marca,modelo,descripcion,idCategoriaRef)
                VALUES (%(nombre)s,%(tipo)s,%(marca)s,%(modelo)s,%(descripcion)s,%(idCategoriaRef)s)''',
                asdict(recurso))
            recurso_id = cursor.lastrowid
            self.insert_bien(cursor, recurso_id, bien)
            return recurso_id

    def agregar_bien(self, recurso_id, bien):
        with self.connection() as conn, conn.cursor(buffered=True) as cursor:
            cursor.execute('SELECT 1 FROM recurso WHERE idRecurso=%s', (recurso_id,))
            if not cursor.fetchone():
                raise LookupError('El recurso no existe.')
            return self.insert_bien(cursor, recurso_id, bien)

    def listar(self):
        with self.connection() as conn, conn.cursor(dictionary=True) as cursor:
            cursor.execute('''SELECT r.*, c.nombre AS categoria FROM recurso r
                JOIN categoria_recurso c ON c.idCategoria=r.idCategoriaRef ORDER BY r.idRecurso DESC''')
            recursos = cursor.fetchall()
            cursor.execute('SELECT * FROM bien_material ORDER BY codigoInventario')
            bienes = cursor.fetchall()
        agrupados = {}
        for bien in bienes:
            bien['fechaAdquisicion'] = bien['fechaAdquisicion'].isoformat()
            agrupados.setdefault(bien['idRecursoRef'], []).append(bien)
        for recurso in recursos:
            recurso['bienes'] = agrupados.get(recurso['idRecurso'], [])
            recurso['total'] = len(recurso['bienes'])
            recurso['disponibles'] = sum(b['estado'] == 'DISPONIBLE' for b in recurso['bienes'])
        return recursos
