"""La base de demostracion debe utilizar la estructura definida en schema.sql."""

from pathlib import Path
import os
import re
import unittest
from uuid import uuid4


class EstructuraSQLTest(unittest.TestCase):
    def test_datos_prueba_conserva_las_tablas_y_restricciones_de_schema(self):
        carpeta = Path(__file__).resolve().parents[1] / 'sql'
        patron = r'CREATE TABLE IF NOT EXISTS (\w+)\s*\((.*?)\) ENGINE=InnoDB;'

        def definiciones(nombre):
            contenido = (carpeta / nombre).read_text(encoding='utf-8-sig')
            tablas = re.findall(patron, contenido, re.DOTALL)
            self.assertTrue(tablas, f'{nombre} no contiene definiciones de tablas.')
            self.assertEqual(len(tablas), len(dict(tablas)), f'{nombre} repite tablas.')
            return tablas

        self.assertEqual(definiciones('schema.sql'), definiciones('datos_prueba.sql'))

    @unittest.skipUnless(os.environ.get('TEST_MYSQL_PORT'), 'Configura MySQL de pruebas.')
    def test_ambos_sql_se_importan_en_bases_vacias(self):
        import mysql.connector

        conexion = mysql.connector.connect(
            host='127.0.0.1',
            port=int(os.environ['TEST_MYSQL_PORT']),
            user=os.environ.get('TEST_MYSQL_USER', 'root'),
            password=os.environ.get('TEST_MYSQL_PASSWORD', ''),
            connection_timeout=5,
            use_pure=True,
        )
        self.addCleanup(conexion.close)
        cursor = conexion.cursor(buffered=True)
        self.addCleanup(cursor.close)
        carpeta = Path(__file__).resolve().parents[1] / 'sql'
        tablas_esperadas = set(
            re.findall(
                r'CREATE TABLE IF NOT EXISTS (\w+)',
                (carpeta / 'schema.sql').read_text(encoding='utf-8-sig'),
            )
        )
        for archivo, base_original in (
            ('schema.sql', 'prestamos_escuela'),
            ('datos_prueba.sql', 'prestamos_escuela_pruebas'),
        ):
            with self.subTest(archivo=archivo):
                nombre = 'test_estructura_sql_' + uuid4().hex
                try:
                    contenido = (carpeta / archivo).read_text(encoding='utf-8-sig')
                    cursor.execute(contenido.replace(base_original, nombre))
                    # El SQL de demostracion incluye consultas de control al final.
                    while cursor.nextset():
                        pass
                    conexion.commit()
                    cursor.execute('SHOW TABLES')
                    self.assertEqual({fila[0] for fila in cursor.fetchall()}, tablas_esperadas)
                    cursor.execute('SELECT COUNT(*) FROM persona')
                    personas = cursor.fetchone()[0]
                    if archivo == 'schema.sql':
                        self.assertEqual(personas, 0)
                    else:
                        self.assertGreater(personas, 0)
                        cursor.execute('SELECT COUNT(*) FROM usuario_sistema')
                        self.assertGreater(cursor.fetchone()[0], 0)
                finally:
                    cursor.execute(f'DROP DATABASE IF EXISTS {nombre}')
