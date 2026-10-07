from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import mysql.connector
from app.config import load_config
from app.domain import BienMaterial, Recurso
from app.errors import ConflictError
from app.repository import RecursoMySQLRepository


class MySQLUnitTest(unittest.TestCase):
    def setUp(self):
        self.repo = RecursoMySQLRepository({'database': 'test'})
        self.conn = MagicMock()
        self.cursor = self.conn.cursor.return_value.__enter__.return_value
        self.bien = BienMaterial.desde_datos({'codigoInventario': 'CC-001', 'ubicacion': 'Lab'})
        self.recurso = Recurso.desde_datos({'nombre': 'Laptop', 'tipo': 'LAPTOP', 'idCategoriaRef': 1})

    def test_commit_and_close(self):
        with patch('app.repository.mysql.connector.connect', return_value=self.conn):
            with self.repo.connection():
                pass
        self.conn.commit.assert_called_once()
        self.conn.rollback.assert_not_called()
        self.conn.close.assert_called_once()

    def test_rollback_and_close(self):
        with patch('app.repository.mysql.connector.connect', return_value=self.conn):
            with self.assertRaises(ValueError):
                with self.repo.connection():
                    raise ValueError('fallo')
        self.conn.rollback.assert_called_once()
        self.conn.commit.assert_not_called()
        self.conn.close.assert_called_once()

    def test_duplicate_rolls_back_entire_resource(self):
        self.cursor.execute.side_effect = [None, mysql.connector.IntegrityError(errno=1062)]
        with patch('app.repository.mysql.connector.connect', return_value=self.conn):
            with self.assertRaises(ConflictError):
                self.repo.crear(self.recurso, self.bien)
        self.conn.rollback.assert_called_once()
        self.conn.commit.assert_not_called()

    def test_foreign_key_error_is_not_duplicate(self):
        self.cursor.execute.side_effect = mysql.connector.IntegrityError(errno=1452)
        with self.assertRaises(mysql.connector.IntegrityError):
            self.repo.insert_bien(self.cursor, 999, self.bien)

    def test_date_serialization_and_availability(self):
        self.cursor.fetchall.side_effect = [
            [{'idRecurso': 1, 'nombre': 'Laptop'}],
            [{'idRecursoRef': 1, 'fechaAdquisicion': date(2026, 9, 23), 'estado': 'DISPONIBLE'},
             {'idRecursoRef': 1, 'fechaAdquisicion': date(2026, 9, 23), 'estado': 'PRESTADO'}]]
        with patch('app.repository.mysql.connector.connect', return_value=self.conn):
            result = self.repo.listar()[0]
        self.assertEqual(result['total'], 2)
        self.assertEqual(result['disponibles'], 1)
        self.assertEqual(result['bienes'][0]['fechaAdquisicion'], '2026-09-23')

    def test_configuration_and_literal_password(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'config.ini'
            path.write_text('[mysql]\npassword=example%with#characters\ndatabase=catalogo\n', encoding='utf-8')
            self.assertEqual(load_config(path)['password'], 'example%with#characters')
            path.write_text('[mysql]\ndatabase=bad`name\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                load_config(path)

    def test_automatic_values_ignore_client(self):
        data = {'codigoInventario': 'CC-001', 'ubicacion': 'Lab', 'fechaAdquisicion': '1900-01-01', 'numeroSerie': 'manual'}
        first = BienMaterial.desde_datos(data)
        second = BienMaterial.desde_datos(data)
        self.assertEqual(first.fechaAdquisicion, date.today().isoformat())
        self.assertRegex(first.numeroSerie, r'^SR-[A-F0-9]{32}$')
        self.assertNotEqual(first.numeroSerie, second.numeroSerie)

    def test_missing_resource_does_not_insert(self):
        self.cursor.fetchone.return_value = None
        with patch('app.repository.mysql.connector.connect', return_value=self.conn):
            with self.assertRaises(LookupError):
                self.repo.agregar_bien(99, self.bien)
        self.assertEqual(self.cursor.execute.call_count, 1)
        self.conn.rollback.assert_called_once()


if __name__ == '__main__':
    unittest.main()
