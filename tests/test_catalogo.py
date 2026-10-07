import copy
from datetime import date
import json
from pathlib import Path
import os
from uuid import uuid4
import mysql.connector
from app.config import load_config
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from server import make_server
from app.auth import UsuarioRepository
from app.repository import RecursoMySQLRepository


@unittest.skipUnless(os.environ.get('MYSQL_TEST_CONFIG'), 'Define MYSQL_TEST_CONFIG para probar MySQL real.')
class CatalogoTest(unittest.TestCase):
    def setUp(self):
        self.db = load_config(os.environ['MYSQL_TEST_CONFIG'])
        self.db['database'] = 'test_prestamos_' + uuid4().hex
        self.admin = {k:v for k,v in self.db.items() if k != 'database'}
        with mysql.connector.connect(**self.admin) as conn, conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE `{self.db['database']}` CHARACTER SET utf8mb4")
        self.addCleanup(self.drop_database)
        self.server = make_server(self.db, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.cookie = ''
        UsuarioRepository(self.db).crear_usuario('prueba', 'ClaveTemporal-123')
        self.call('/api/login', {'usuario':'prueba','contrasena':'ClaveTemporal-123'})
        self.payload = {"recurso": {"nombre": "Laptop académica", "tipo": "LAPTOP", "marca": "",
            "modelo": "", "descripcion": "", "idCategoriaRef": 1}, "bien": {
            "codigoInventario": "CC-001", "ubicacion": "Lab 1"}}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def drop_database(self):
        # Solo elimina la base aleatoria creada por esta prueba, nunca la configurada.
        with mysql.connector.connect(**self.admin) as conn, conn.cursor() as cursor:
            cursor.execute(f"DROP DATABASE `{self.db['database']}`")

    def call(self, path="/api/catalogo", data=None, headers=None):
        request = Request(self.base + path, data=None if data is None else json.dumps(data).encode(),
                          headers={"Cookie": self.cookie, **(headers or {"Content-Type": "application/json"})})
        try:
            with urlopen(request, timeout=5) as response:
                if response.headers.get('Set-Cookie'):
                    self.cookie=response.headers['Set-Cookie'].split(';')[0]
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)

    def test_empty_and_persistence(self):
        self.assertEqual(self.call()[1]["recursos"], [])
        self.assertEqual(self.call("/api/recursos", self.payload)[0], 201)
        # Una conexión nueva lee la misma base, sin depender de memoria del servidor.
        stored = RecursoMySQLRepository(self.db).listar()
        self.assertEqual(stored[0]["nombre"], "Laptop académica")
        self.assertEqual(stored[0]["disponibles"], 1)
        self.assertEqual(stored[0]["bienes"][0]["estado"], "DISPONIBLE")

    def test_multiple_items_same_resource(self):
        _, result = self.call("/api/recursos", self.payload)
        bien = {**self.payload["bien"], "codigoInventario": "CC-002"}
        self.assertEqual(self.call(f'/api/recursos/{result["idRecurso"]}/bienes', bien)[0], 201)
        resources = self.call()[1]["recursos"]
        self.assertEqual(len(resources), 1)
        self.assertEqual(resources[0]["total"], 2)

    def test_duplicate_rolls_back_resource_and_is_case_insensitive(self):
        self.call("/api/recursos", self.payload)
        self.payload["bien"]["codigoInventario"] = "cc-001"
        self.assertEqual(self.call("/api/recursos", self.payload)[0], 409)
        self.assertEqual(len(self.call()[1]["recursos"]), 1)

    def test_invalid_values_do_not_write(self):
        for section, key, value in [("recurso", "tipo", "PC"), ("recurso", "nombre", " "),
                ("recurso", "idCategoriaRef", 999), ("recurso", "idCategoriaRef", True),
                ("bien", "codigoInventario", "INV 01"), ("bien", "ubicacion", ""),
                ("bien", "estado", "PRESTADO")]:
            with self.subTest(key=key, value=value):
                data = copy.deepcopy(self.payload)
                data[section][key] = value
                self.assertEqual(self.call("/api/recursos", data)[0], 400)
        self.assertEqual(self.call()[1]["recursos"], [])

    def test_missing_resource_and_malformed_objects(self):
        self.assertEqual(self.call("/api/recursos/999/bienes", self.payload["bien"])[0], 404)
        for data in [[], {}, {"recurso": [], "bien": {}}]:
            self.assertEqual(self.call("/api/recursos", data)[0], 400)

    def test_date_and_serial_are_generated_by_server(self):
        self.payload["bien"].update(numeroSerie="MANUAL", fechaAdquisicion="1900-01-01")
        status, result = self.call("/api/recursos", self.payload)
        self.assertEqual(status, 201)
        self.assertEqual(self.call(f'/api/recursos/{result["idRecurso"]}/bienes',
            {"codigoInventario": "CC-002", "ubicacion": "Lab 2"})[0], 201)
        bienes = self.call()[1]["recursos"][0]["bienes"]
        for bien in bienes:
            self.assertEqual(bien["fechaAdquisicion"], date.today().isoformat())
            self.assertRegex(bien["numeroSerie"], r"^SR-[A-F0-9]{32}$")
        self.assertNotEqual(bienes[0]["numeroSerie"], bienes[1]["numeroSerie"])
        self.assertEqual(RecursoMySQLRepository(self.db).listar()[0]["bienes"], bienes)

    def test_cross_origin_and_wrong_content_type_rejected(self):
        self.assertEqual(self.call("/api/recursos", self.payload,
            {"Content-Type": "application/json", "Origin": "https://other.example"})[0], 403)
        self.assertEqual(self.call("/api/recursos", self.payload, {"Content-Type": "text/plain"})[0], 415)

    def test_static_and_unknown_routes(self):
        with urlopen(Request(self.base + "/", headers={"Cookie":self.cookie})) as response:
            self.assertIn("Catálogo de recursos", response.read().decode())
        self.assertEqual(self.call("/server.py")[0], 404)

    def test_personas_mysql_registration_and_duplicate(self):
        data = dict(nombres='Ana',apellidos='Pérez',documentoIdentidad='12345678',correo='ana@example.com',
                    tipo='ESTUDIANTE',codigoEstudiante='E001',ciclo=3)
        self.assertEqual(self.call('/api/personas',data)[0],201)
        self.assertEqual(self.call('/api/personas',data)[0],409)
        result = self.call('/api/personas')[1]['personas']
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['detalles']['ciclo'],3)
        self.assertIn('fechaRegistro',result[0])

    def test_login_guards_logout_and_replay(self):
        saved = self.cookie
        self.cookie = ''
        self.assertEqual(self.call('/api/catalogo')[0],401)
        self.assertEqual(self.call('/api/personas',{})[0],401)
        self.assertEqual(self.call('/api/login',{'usuario':'prueba','contrasena':'incorrecta'})[0],401)
        self.cookie = saved
        self.assertEqual(self.call('/api/sesion')[0],200)
        self.assertEqual(self.call('/api/logout',{})[0],200)
        self.cookie = saved
        self.assertEqual(self.call('/api/catalogo')[0],401)

    def test_login_rate_limit(self):
        self.cookie = ''
        for _ in range(5):
            self.assertEqual(self.call('/api/login',{'usuario':'nadie','contrasena':'incorrecta'})[0],401)
        self.assertEqual(self.call('/api/login',{'usuario':'nadie','contrasena':'incorrecta'})[0],429)


if __name__ == "__main__":
    unittest.main()
