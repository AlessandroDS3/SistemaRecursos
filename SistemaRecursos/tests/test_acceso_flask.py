"""Pruebas del acceso con cuentas en memoria, sin conexión a MySQL."""
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from flask import g
from werkzeug.security import generate_password_hash

from app import create_app, obtener_clave_sesion
from mysql.connector import DatabaseError
from dominio.gestion_personas_usuarios.cuentas import Credenciales, IRepositorioAcceso
from dominio.gestion_personas_usuarios.cuentas import Rol
from dominio.gestion_personas_usuarios.cuentas import EstadoCuenta, UsuarioSistema, IdentidadAcceso
from presentacion.seguridad import requiere_permiso, token_csrf


class CuentasEnMemoria(IRepositorioAcceso):
    """Solo implementa las consultas y el registro del último acceso."""

    def __init__(self, cuenta):
        self.cuenta = cuenta
        self.accesos = []

    def consultar_por_nombre_usuario(self, nombre):
        return self.cuenta if nombre == self.cuenta.credenciales.nombre_usuario else None

    def consultar_cuenta_por_id(self, identificador):
        return self.cuenta if identificador == self.cuenta.id_usuario else None

    def registrar_acceso(self, identificador):
        self.accesos.append(identificador)


class AccesoFlaskTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clave = "ClavePrueba2026!"
        cls.hash_clave = generate_password_hash(cls.clave)

    def setUp(self):
        persona = IdentidadAcceso(dni='12345678', nombres='Ana', apellidos='Prueba')
        self.cuenta = UsuarioSistema(
            id_usuario=1, persona=persona, rol=Rol(nombre="USUARIO"),
            credenciales=Credenciales("ana", self.hash_clave),
        )
        self.repo = CuentasEnMemoria(self.cuenta)
        self.app = create_app(
            {"TESTING": True, "SECRET_KEY": "clave-solo-para-pruebas"},
            repositorios=(object(), object(), self.repo),
        )

        @self.app.get("/privado")
        @requiere_permiso()
        def privado():
            token_csrf()
            return g.usuario.credenciales.nombre_usuario

        @self.app.get("/administracion-prueba")
        @requiere_permiso("RECURSOS_GESTIONAR")
        def administracion():
            return "administracion"

        self.client = self.app.test_client()

    def login(self, client=None, usuario="ana", clave=None):
        client = client or self.client
        client.get("/login")
        with client.session_transaction() as sesion:
            token = sesion["csrf_token"]
        return client.post("/login", data=dict(
            usuario=usuario, clave=self.clave if clave is None else clave, csrf_token=token,
        ))

    def test_fallo_de_mysql_se_registra_y_devuelve_500(self):
        @self.app.get('/fallo-mysql')
        def fallo_mysql():
            raise DatabaseError('Detalle técnico simulado')

        with self.assertLogs(self.app.logger, level='ERROR') as registro:
            respuesta = self.client.get('/fallo-mysql')
        self.assertEqual(respuesta.status_code, 500)
        self.assertNotIn(b'Detalle t', respuesta.data)
        self.assertTrue(any('MySQL' in linea for linea in registro.output))

    def test_validacion_y_ausencia_no_devuelven_exito(self):
        @self.app.get('/dato-invalido')
        def dato_invalido():
            raise ValueError('Dato inválido')

        @self.app.get('/registro-ausente')
        def registro_ausente():
            raise LookupError('Registro inexistente')

        self.assertEqual(self.client.get('/dato-invalido').status_code, 400)
        self.assertEqual(self.client.get('/registro-ausente').status_code, 404)

    def test_clave_local_se_conserva_y_el_entorno_tiene_prioridad(self):
        with TemporaryDirectory() as carpeta:
            with patch('app.__file__', str(Path(carpeta) / 'app.py')):
                with patch.dict('os.environ', {'FLASK_SECRET_KEY': ''}):
                    primera = obtener_clave_sesion()
                    self.assertEqual(primera, obtener_clave_sesion())
                    self.assertEqual(len(primera), 64)
                with patch.dict('os.environ', {'FLASK_SECRET_KEY': 'clave-definida-en-entorno'}):
                    self.assertEqual(obtener_clave_sesion(), 'clave-definida-en-entorno')

    def test_login_y_navegacion_sin_repositorio_de_sesiones(self):
        self.assertEqual(self.login().status_code, 302)
        self.assertEqual(self.client.get("/privado").data, b"ana")
        self.assertEqual(self.repo.accesos, [1])
        with self.client.session_transaction() as sesion:
            self.assertEqual(sesion["id_usuario"], 1)
            self.assertNotIn("token_acceso", sesion)
            self.assertNotIn(self.clave, sesion.values())
            self.assertNotIn(self.hash_clave, sesion.values())

    def test_intentos_fallidos_no_bloquean_una_clave_correcta(self):
        for _ in range(10):
            self.assertEqual(self.login(clave="incorrecta").status_code, 200)
        self.assertEqual(self.repo.accesos, [])
        self.assertEqual(self.login().status_code, 302)

    def test_usuario_inexistente_no_inicia_sesion(self):
        self.assertEqual(self.login(usuario="no-existe").status_code, 200)
        self.assertEqual(self.client.get("/privado").status_code, 302)

    def test_login_y_logout_requieren_csrf(self):
        self.client.get("/login")
        self.assertEqual(self.client.post("/login", data=dict(
            usuario="ana", clave=self.clave,
        )).status_code, 400)
        self.login()
        self.assertEqual(self.client.post("/logout").status_code, 400)
        self.assertEqual(self.client.get("/privado").status_code, 200)

    def test_logout_no_cierra_otro_navegador(self):
        otro = self.app.test_client()
        self.login()
        self.login(client=otro)
        self.client.get("/privado")
        with self.client.session_transaction() as sesion:
            token = sesion["csrf_token"]
        self.assertEqual(self.client.post("/logout", data=dict(csrf_token=token)).status_code, 302)
        self.assertEqual(self.client.get("/privado").status_code, 302)
        self.assertEqual(otro.get("/privado").status_code, 200)

    def test_cuenta_y_persona_inactivas_impiden_el_acceso(self):
        for elemento, atributo, valor in (
            (self.cuenta, "estado_cuenta", EstadoCuenta.INACTIVA),
            (self.cuenta.persona, "estado", "INACTIVA"),
        ):
            with self.subTest(atributo=atributo):
                self.login()
                anterior = getattr(elemento, atributo)
                setattr(elemento, atributo, valor)
                try:
                    self.assertEqual(self.client.get("/privado").status_code, 302)
                    self.assertEqual(self.login().status_code, 200)
                finally:
                    setattr(elemento, atributo, anterior)

    def test_cambio_de_clave_descarta_cookie_anterior(self):
        self.login()
        self.cuenta.credenciales.contrasena_hash = generate_password_hash("OtraClave2026!")
        self.assertEqual(self.client.get("/privado").status_code, 302)
        self.assertEqual(self.login(clave="OtraClave2026!").status_code, 302)

    def test_cookie_alterada_no_permite_acceso(self):
        self.login()
        cookie = self.client.get_cookie("session").value
        self.client.set_cookie("session", cookie + "x")
        self.assertEqual(self.client.get("/privado").status_code, 302)

    def test_sesion_vencida_no_permite_acceso(self):
        hace_mas_de_ocho_horas = int(time.time()) - 8 * 60 * 60 - 10
        with patch("itsdangerous.timed.TimestampSigner.get_timestamp", return_value=hace_mas_de_ocho_horas):
            self.assertEqual(self.login().status_code, 302)
        self.assertEqual(self.client.get("/privado").status_code, 302)

    def test_permisos_se_comprueban_en_cada_peticion(self):
        self.login()
        self.assertEqual(self.client.get("/administracion-prueba").status_code, 403)
        self.cuenta.rol.permisos = [SimpleNamespace(codigo="RECURSOS_GESTIONAR")]
        self.assertEqual(self.client.get("/administracion-prueba").status_code, 200)
        self.cuenta.rol.permisos = []
        self.assertEqual(self.client.get("/administracion-prueba").status_code, 403)


if __name__ == "__main__":
    unittest.main()
