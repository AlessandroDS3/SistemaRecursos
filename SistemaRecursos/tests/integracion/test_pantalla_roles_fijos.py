"""Permisos y asignación de roles a través de Flask."""

import unittest
from unittest.mock import patch

from app import create_app
from dominio.gestion_personas_usuarios.rol import permisos_del_rol
from tests.soporte_roles import cliente_autenticado, cuenta


class PantallaRolesFijosTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch('app.clave_local', return_value='pruebas-roles'):
            cls.app = create_app(dict(TESTING=True))

    def cliente(self, rol):
        return cliente_autenticado(self, self.app, cuenta(rol))

    def test_administrador_consulta_permisos_sin_formulario_de_edicion(self):
        cliente = self.cliente('ADMINISTRADOR')
        cuentas = self.app.extensions['servicios']['cuentas']
        with patch.object(cuentas, 'buscar_cuentas', return_value=[dict(
            persona='Ana Prueba', dni_persona='20000001', nombre_usuario='prueba',
            estado_cuenta='ACTIVA', rol='ADMINISTRADOR',
        )]):
            respuesta = cliente.get('/roles?q=Ana')
        self.assertEqual(respuesta.status_code, 200)
        html = respuesta.get_data(as_text=True)
        self.assertIn('Los tres roles y sus permisos son fijos', html)
        self.assertIn('/roles/asignar', html)
        self.assertNotIn('/roles/permisos', html)
        self.assertNotIn('Guardar permisos', html)
        self.assertNotIn('type="checkbox"', html)

    def test_antigua_ruta_de_edicion_no_existe(self):
        cliente = self.cliente('ADMINISTRADOR')
        respuesta = cliente.post('/roles/permisos', data={
            'csrf_token': 'token', 'permisos_USUARIO': 'ROLES_GESTIONAR',
        })
        self.assertEqual(respuesta.status_code, 404)
        self.assertNotIn('ROLES_GESTIONAR', permisos_del_rol('USUARIO'))

    def test_solo_administrador_puede_asignar_roles(self):
        cuentas = self.app.extensions['servicios']['cuentas']
        for rol in ('USUARIO', 'ENCARGADO_PRESTAMOS', 'ADMINISTRADOR'):
            with self.subTest(rol=rol):
                cliente = self.cliente(rol)
                with patch.object(cuentas, 'asignar_rol_cuenta') as asignar:
                    respuesta = cliente.post('/roles/asignar', data={
                        'csrf_token': 'token', 'dni': '20000002', 'rol': 'USUARIO',
                    })
                    if rol == 'ADMINISTRADOR':
                        self.assertEqual(respuesta.status_code, 302)
                        asignar.assert_called_once_with('20000002', 'USUARIO', 1)
                    else:
                        self.assertEqual(respuesta.status_code, 403)
                        asignar.assert_not_called()
                        self.assertEqual(cliente.get('/roles').status_code, 403)


if __name__ == '__main__':
    unittest.main()
