"""Una conexión por operación; el cursor nunca sale de persistencia."""

from contextlib import contextmanager
import os
import mysql.connector


class MySQLConnection:
    def __init__(self, config=None):
        self.config = config or dict(
            host=os.getenv('DB_HOST', '127.0.0.1'),
            port=int(os.getenv('DB_PORT', '3306')),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'prestamos_escuela_pruebas'),
            connection_timeout=5,
            use_pure=True,
        )

    @contextmanager
    def sesion(self, escritura=False):
        conexion = mysql.connector.connect(**self.config)
        cursor = conexion.cursor(dictionary=True, buffered=True)
        try:
            yield cursor
            if escritura:
                conexion.commit()
        except Exception:
            conexion.rollback()
            raise
        finally:
            cursor.close()
            conexion.close()
