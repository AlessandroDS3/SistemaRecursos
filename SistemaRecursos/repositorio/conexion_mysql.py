import os
from contextlib import contextmanager
import mysql.connector


class MySQLConnection:
    def __init__(self, config=None):
        self.config = (
            config
            if config is not None
            else {
                "host": os.environ.get("DB_HOST", "127.0.0.1"),
                "port": int(os.environ.get("DB_PORT", "3306")),
                "user": os.environ.get("DB_USER", "root"),
                "password": os.environ.get("DB_PASSWORD", ""),
                "database": os.environ.get("DB_NAME", "prestamos_escuela"),
                "connection_timeout": 5,
            }
        )

    def abrir_conexion(self):
        return mysql.connector.connect(**self.config)

    def cerrar_conexion(self, conexion):
        conexion.close()

    @contextmanager
    def sesion(self, escritura=False):
        conexion = self.abrir_conexion()
        cursor = None
        try:
            cursor = conexion.cursor(dictionary=True)
            yield cursor
            if escritura:
                conexion.commit()
        except Exception:
            if escritura:
                conexion.rollback()
            raise
        finally:
            if cursor is not None:
                cursor.close()
            self.cerrar_conexion(conexion)
