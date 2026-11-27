"""Permisos y asignación de roles a través de Flask."""

import unittest
from unittest.mock import patch

from app import create_app
from dominio.gestion_personas_usuarios.rol import permisos_del_rol
from tests.soporte_roles import crear_cliente_con_sesion_simulada, crear_cuenta_de_prueba


class PantallaRolesFijosTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch('app.obtener_clave_de_sesion_flask', return_value='pruebas-roles'):
            cls.app = create_app(dict(TESTING=True))

    def crear_cliente_para_rol(self, rol):
        return crear_cliente_con_sesion_simulada(self, self.app, crear_cuenta_de_prueba(rol))

    def test_administrador_consulta_permisos_sin_formulario_de_edicion(self):
        cliente = self.crear_cliente_para_rol('ADMINISTRADOR')
        cuentas = self.app.extensions['servicios']['cuentas']
        with patch.object(cuentas, 'consultar_cuenta', return_value=dict(
            nombre_usuario='prueba', estado_cuenta='ACTIVA', rol='USUARIO', version='vigente',
        )):
            respuesta = cliente.get('/cuentas/20000002/editar')
        self.assertEqual(respuesta.status_code, 200)
        html = respuesta.get_data(as_text=True)
        self.assertIn('Permisos por rol', html)
        self.assertIn('name="rol"', html)
        self.assertIn('value="USUARIO" selected', html)
        self.assertNotIn('href="/roles"', html)

    def test_antigua_ruta_de_edicion_no_existe(self):
        cliente = self.crear_cliente_para_rol('ADMINISTRADOR')
        respuesta = cliente.post('/roles/permisos', data={
            'csrf_token': 'token', 'permisos_USUARIO': 'ROLES_GESTIONAR',
        })
        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(cliente.get('/roles').status_code, 404)
        self.assertNotIn('ROLES_GESTIONAR', permisos_del_rol('USUARIO'))

    def test_solo_administrador_puede_asignar_roles(self):
        cuentas = self.app.extensions['servicios']['cuentas']
        datos = {'csrf_token': 'token', 'version': 'vigente', 'rol': 'ENCARGADO_PRESTAMOS'}
        for rol in ('USUARIO', 'ENCARGADO_PRESTAMOS', 'ADMINISTRADOR'):
            with self.subTest(rol=rol):
                cliente = self.crear_cliente_para_rol(rol)
                with patch.object(cuentas, 'actualizar_cuenta') as actualizar:
                    respuesta = cliente.post('/cuentas/20000002/editar', data=datos)
                    if rol == 'ADMINISTRADOR':
                        self.assertEqual(respuesta.status_code, 302)
                        self.assertTrue(respuesta.location.endswith('/personas/20000002'))
                        actualizar.assert_called_once_with('20000002', datos, 1)
                    else:
                        self.assertEqual(respuesta.status_code, 403)
                        actualizar.assert_not_called()
                        self.assertEqual(cliente.get('/cuentas/20000002/editar').status_code, 403)


if __name__ == '__main__':
    unittest.main()
