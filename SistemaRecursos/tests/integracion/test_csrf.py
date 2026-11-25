"""Los tokens inválidos se rechazan antes de autenticar o ejecutar acciones."""

import unittest
from unittest.mock import patch

from app import create_app
from tests.soporte_roles import cliente_autenticado, cuenta


class CsrfTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch('app.clave_local', return_value='pruebas-csrf'):
            cls.app = create_app(dict(TESTING=True))

    def test_login_rechaza_tokens_invalidos_sin_autenticar(self):
        for token in ('ñ', '🔒', '', 'otro-token'):
            with self.subTest(token=token):
                cliente = self.app.test_client()
                with cliente.session_transaction() as sesion:
                    sesion['csrf'] = 'token'
                with patch.object(self.app.extensions['servicios']['acceso'], 'autenticar_cuenta') as autenticar:
                    respuesta = cliente.post('/login', data={'csrf_token': token})
                self.assertEqual(respuesta.status_code, 400)
                autenticar.assert_not_called()

    def test_login_con_token_valido_autentica(self):
        cliente = self.app.test_client()
        with cliente.session_transaction() as sesion:
            sesion['csrf'] = 'token'
        acceso = self.app.extensions['servicios']['acceso']
        with patch.object(acceso, 'autenticar_cuenta', return_value=cuenta('USUARIO')) as autenticar, \
                patch.object(acceso, 'iniciar_sesion', return_value='token-sesion') as iniciar:
            respuesta = cliente.post('/login', data={
                'csrf_token': 'token', 'usuario': 'prueba', 'clave': 'clave',
            })
        self.assertEqual(respuesta.status_code, 302)
        autenticar.assert_called_once_with('prueba', 'clave', '127.0.0.1')
        iniciar.assert_called_once_with(1)
        with cliente.session_transaction() as sesion:
            self.assertEqual(sesion['sid'], 'token-sesion')

    def test_accion_autenticada_con_token_unicode_no_ejecuta_cambios(self):
        cliente = cliente_autenticado(self, self.app, cuenta('ADMINISTRADOR'))
        with patch.object(self.app.extensions['servicios']['cuentas'], 'asignar_rol_cuenta') as asignar:
            respuesta = cliente.post('/roles/asignar', data={
                'csrf_token': 'ñ', 'dni': '20000002', 'rol': 'USUARIO',
            })
        self.assertEqual(respuesta.status_code, 400)
        asignar.assert_not_called()
