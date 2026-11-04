"""Pruebas con MySQL 8. Definir TEST_MYSQL_PORT para usar una instancia de pruebas."""
import os
import re
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import mysql.connector
from app import create_app
from dominio.gestion_personas_usuarios.fabrica_persona import FabricaPersona
from dominio.gestion_personas_usuarios.version_edicion import version_persona
from repositorio.conexion_mysql import MySQLConnection
from repositorio.repositorio_acceso_sql import RepositorioAccesoSQL
from repositorio.repositorio_persona_sql import RepositorioPersonaSQL


@unittest.skipUnless(os.environ.get("TEST_MYSQL_PORT"), "Configura la instancia MySQL de pruebas.")
class PersonasAccesoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database = "test_personas_" + uuid4().hex
        cfg = dict(host="127.0.0.1", port=int(os.environ["TEST_MYSQL_PORT"]),
                   user=os.environ.get("TEST_MYSQL_USER", "root"),
                   password=os.environ.get("TEST_MYSQL_PASSWORD", ""), use_pure=True)
        cn = mysql.connector.connect(**cfg)
        cls.addClassCleanup(cn.close)
        cursor = cn.cursor()
        cls.addClassCleanup(cursor.close)
        cursor.execute(f"CREATE DATABASE {cls.database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cls.addClassCleanup(cursor.execute, f"DROP DATABASE {cls.database}")
        seed = Path(__file__).resolve().parents[1] / "sql" / "datos_prueba.sql"
        cursor.execute(seed.read_text(encoding="utf-8").replace("prestamos_escuela_pruebas", cls.database))
        while cursor.nextset():
            pass
        cn.commit()
        cfg["database"] = cls.database
        cls.db = MySQLConnection(cfg)
        cls.app = create_app({"TESTING": True, "MYSQL_CONFIG": cfg})

    def login(self, user="admin", password="AdminPrueba2026!"):
        client = self.app.test_client()
        client.get("/login")
        with client.session_transaction() as s:
            token = s["csrf_token"]
        response = client.post("/login", data=dict(usuario=user, clave=password, csrf_token=token))
        self.assertEqual(response.status_code, 302)
        return client

    def post(self, client, path, data=None):
        client.get("/")
        with client.session_transaction() as s:
            token = s["csrf_token"]
        return client.post(path, data=dict(data or {}, csrf_token=token))

    def test_logout_independiente_y_cookie_copiada(self):
        uno, dos = self.login(), self.login()
        copia = uno.get_cookie("session").value
        self.assertEqual(self.post(uno, "/logout").status_code, 302)
        replay = self.app.test_client()
        replay.set_cookie("session", copia)
        self.assertEqual(replay.get("/personas").status_code, 302)
        self.assertEqual(dos.get("/personas").status_code, 200)

    def test_gestor_de_cuentas_sin_consulta_ni_acceso_a_admin(self):
        # Este rol de prueba puede administrar cuentas, pero no consultar fichas.
        with self.db.sesion(escritura=True) as c:
            c.execute("DELETE FROM rol_permiso WHERE id_rol=2 AND id_permiso=1")
            c.execute("INSERT INTO rol_permiso VALUES (2,3)")
        try:
            client = self.login("encargado1", "EncargadoPrueba2026!")
            self.assertEqual(client.get("/personas/98000001").status_code, 403)
            error = self.post(client, "/personas/98000001/cuenta", {"nombre_usuario": ""})
            self.assertEqual(error.status_code, 400)
            self.assertNotIn(b"admin@ejemplo.gmail", error.data)
            self.assertIn(b"Crear cuenta de acceso", error.data)
            editar = self.post(client, "/personas/98000001/cuenta/editar",
                               {"nombre_usuario": "admin", "clave": "otra-clave-test"})
            self.assertEqual(editar.status_code, 403)
            self.login()
        finally:
            with self.db.sesion(escritura=True) as c:
                c.execute("DELETE FROM rol_permiso WHERE id_rol=2 AND id_permiso=3")
                c.execute("INSERT INTO rol_permiso VALUES (2,1)")

    def test_limites_simultaneos_por_usuario_y_origen(self):
        repo = RepositorioAccesoSQL(self.db)
        with ThreadPoolExecutor(max_workers=12) as pool:
            reservas = list(pool.map(lambda i: repo.reservar_intento("cuenta-prueba", f"origen-{i}"), range(12)))
        self.assertEqual(sum(x is not None for x in reservas), 8)
        for i in range(50):
            self.assertIsNotNone(repo.reservar_intento(f"user-{i}", "origen-compartido"))
        self.assertIsNone(repo.reservar_intento("otra-cuenta", "origen-compartido"))

    def test_login_limitado_y_sesiones_revocadas_al_desactivar(self):
        acceso = self.app.extensions["acceso"]
        for _ in range(8):
            self.assertIsNone(acceso.autenticar("usuario1", "incorrecta", "origen-login"))
        self.assertIsNone(acceso.autenticar("usuario1", "UsuarioPrueba2026!", "otro-origen"))
        with self.db.sesion(escritura=True) as c:
            c.execute("UPDATE intento_acceso SET ventana=ventana-1 WHERE clave='usuario1'")
        client = self.login("usuario1", "UsuarioPrueba2026!")
        acceso.cambiar_estado_cuenta("02167885", False, 1)
        acceso.cambiar_estado_cuenta("02167885", True, 1)
        self.assertEqual(client.get("/").status_code, 302)
        self.login("usuario1", "UsuarioPrueba2026!")

    def test_directorio_y_campos_opcionales(self):
        repo = RepositorioPersonaSQL(self.db)
        for i in range(10):
            repo.registrar_persona(FabricaPersona.construir(dict(
                tipo="ESTUDIANTE", dni=str(70000000+i), cui=str(71000000+i),
                nombres="Prueba", apellidos="Directorio", correo="prueba@example.com",
                estado_matricula="vigente",
            )))
        with self.db.sesion(escritura=True) as c:
            c.execute("UPDATE persona SET telefono=NULL WHERE dni='98000001'")
            c.execute("UPDATE rol SET descripcion=NULL WHERE id_rol=3")
            c.execute("UPDATE permiso SET descripcion=NULL WHERE id_permiso=1")
        client = self.login()
        self.assertEqual(repo.consultar_persona("98000001").telefono, "")
        self.assertIn(b"Siguiente", client.get("/personas").data)
        self.assertIn(b"Anterior", client.get("/personas?pagina=2").data)
        self.assertIn(b"dos caracteres", client.get("/personas?q=a").data)
        self.assertEqual(client.get("/roles").status_code, 200)
        primera, segunda = [repo.consultar_personas({"pagina": n})["personas"] for n in (1, 2)]
        self.assertEqual(len(primera), 25)
        self.assertTrue(segunda)
        self.assertTrue({p.dni for p in primera}.isdisjoint(p.dni for p in segunda))

    def test_edicion_antigua_no_reactiva_persona(self):
        client = self.login()
        dni = "99000012"
        path = f"/personas/{dni}/editar"
        version = re.search(rb'name="version" value="([^"]+)"', client.get(path).data)[1].decode()
        with self.db.sesion(escritura=True) as c:
            c.execute("UPDATE persona SET estado='INACTIVA' WHERE dni=%s", (dni,))
        repo = RepositorioPersonaSQL(self.db)
        datos = dict(vars(repo.consultar_persona(dni)), tipo="ESTUDIANTE", version=version,
                     estado="ACTIVA", telefono="123", ciclo="5")
        datos["semestre_academico"] = datos["semestre_academico"] or ""
        self.assertEqual(self.post(client, path, datos).status_code, 409)
        actual = repo.consultar_persona(dni)
        self.assertFalse(actual.esta_activa())
        datos["version"] = version_persona(actual)
        self.assertEqual(self.post(client, path, datos).status_code, 302)

    def test_matriz_antigua_no_restaura_permiso(self):
        client = self.login()
        html = client.get("/roles").data
        version = re.search(rb'name="version" value="([^"]+)"', html)[1].decode()
        with self.db.sesion() as c:
            c.execute("SELECT id_rol,id_permiso FROM rol_permiso")
            datos = {}
            for fila in c.fetchall():
                datos.setdefault("permisos_" + str(fila["id_rol"]), []).append(str(fila["id_permiso"]))
        original = dict(datos, version=version)
        cambio = dict(original, permisos_1=[p for p in datos["permisos_1"] if p != "6"])
        self.assertEqual(self.post(client, "/roles/permisos", cambio).status_code, 302)
        self.assertEqual(self.post(client, "/roles/permisos", original).status_code, 409)
        with self.db.sesion() as c:
            c.execute("SELECT 1 FROM rol_permiso WHERE id_rol=1 AND id_permiso=6")
            self.assertIsNone(c.fetchone())

    def test_alta_revalida_persona_y_rol_en_la_escritura(self):
        acceso = self.app.extensions["acceso"]
        repo = acceso.usuarios
        real = repo.registrar_cuenta
        def desactivar_y_guardar(usuario):
            with self.db.sesion(escritura=True) as c:
                c.execute("UPDATE persona SET estado='INACTIVA' WHERE dni=%s", (usuario.persona.dni,))
            return real(usuario)
        with patch.object(repo, "registrar_cuenta", desactivar_y_guardar):
            with self.assertRaisesRegex(ValueError, "persona debe estar activa"):
                acceso.registrar_cuenta("99000011", "alta-prueba", "ClaveTemporal123")
        self.assertIsNone(repo.consultar_cuenta_persona("99000011"))
        with self.db.sesion(escritura=True) as c:
            c.execute("UPDATE persona SET estado='ACTIVA' WHERE dni='99000011'")
        def desactivar_rol_y_guardar(usuario):
            with self.db.sesion(escritura=True) as c:
                c.execute("UPDATE rol SET activo=FALSE WHERE id_rol=%s", (usuario.rol.id_rol,))
            return real(usuario)
        try:
            with patch.object(repo, "registrar_cuenta", desactivar_rol_y_guardar):
                with self.assertRaisesRegex(ValueError, "rol Usuario"):
                    acceso.registrar_cuenta("99000011", "alta-prueba", "ClaveTemporal123")
        finally:
            with self.db.sesion(escritura=True) as c:
                c.execute("UPDATE rol SET activo=TRUE WHERE nombre='USUARIO'")
        cuenta = acceso.registrar_cuenta("99000011", "alta-prueba", "ClaveTemporal123")
        self.assertIsNotNone(cuenta.id_usuario)
