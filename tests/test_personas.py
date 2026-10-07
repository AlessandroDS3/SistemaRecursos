import unittest
from unittest.mock import MagicMock, patch
import mysql.connector
from app.personas import Persona, GestionPersonasService
from app.persona_repository import PersonaMySQLRepository
from app.domain import ValidationError
from app.errors import ConflictError

class PersonasTest(unittest.TestCase):
    def data(self, tipo='ESTUDIANTE'):
        return dict(nombres='Ana',apellidos='Pérez',documentoIdentidad='12345678',correo='ana@example.com',
                    tipo=tipo,codigoEstudiante='e001',ciclo=3,codigoDocente='d001',codigoEmpleado='a001')

    def test_three_types_and_only_matching_fields(self):
        for tipo,code in [('ESTUDIANTE','codigoEstudiante'),('DOCENTE','codigoDocente'),('ADMINISTRATIVO','codigoEmpleado')]:
            persona=Persona.desde_datos(self.data(tipo))
            self.assertIn(code,persona.detalles)
            self.assertEqual(persona.estado,'ACTIVA')
            self.assertNotIn('fechaRegistro',persona.detalles)

    def test_invalid_data(self):
        for key,value in [('nombres',' '),('correo','bad'),('tipo','EXTERNO'),('documentoIdentidad','!'),('ciclo',True),('ciclo',0),('ciclo',21),('codigoEstudiante','')]:
            with self.subTest(key=key,value=value), self.assertRaises(ValidationError):
                Persona.desde_datos({**self.data(),key:value})

    def test_duplicate_subtype_rolls_back_person(self):
        conn=MagicMock();cursor=conn.cursor.return_value.__enter__.return_value
        cursor.execute.side_effect=[None,mysql.connector.IntegrityError(errno=1062)]
        repo=PersonaMySQLRepository({})
        with patch('app.repository.mysql.connector.connect',return_value=conn),self.assertRaises(ConflictError):
            repo.crear_persona(Persona.desde_datos(self.data()))
        conn.rollback.assert_called_once();conn.commit.assert_not_called();conn.close.assert_called_once()

    def test_success_uses_single_transaction(self):
        conn=MagicMock();cursor=conn.cursor.return_value.__enter__.return_value;cursor.lastrowid=12
        with patch('app.repository.mysql.connector.connect',return_value=conn):
            self.assertEqual(GestionPersonasService(PersonaMySQLRepository({})).registrar(self.data()),12)
        self.assertEqual(cursor.execute.call_count,2);conn.commit.assert_called_once()

    def test_list_serializes_timestamp_and_details(self):
        from datetime import datetime
        conn=MagicMock();cursor=conn.cursor.return_value.__enter__.return_value
        cursor.fetchall.side_effect=[[dict(idPersona=1,fechaRegistro=datetime(2026,10,6,10,0))],[dict(idPersona=1,codigoEstudiante='E001')],[],[]]
        with patch('app.repository.mysql.connector.connect',return_value=conn):
            result=PersonaMySQLRepository({}).listar_personas()[0]
        self.assertEqual(result['detalles']['codigoEstudiante'],'E001')
        self.assertEqual(result['fechaRegistro'],'2026-10-06T10:00:00')
