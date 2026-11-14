from time import time
from werkzeug.security import generate_password_hash
from caso_mysql import CasoMySQL


class AccesoWeb(CasoMySQL):
    def test_login_correcto_y_cookie_sin_hash_ni_datos_academicos(self):
        respuesta = self.login()
        self.assertEqual(respuesta.status_code, 302)
        with self.cliente.session_transaction() as sesion:
            self.assertEqual(sesion['id_usuario'], 1)
            self.assertNotIn('contrasena_hash', sesion)
            self.assertNotIn('cui', sesion)
        self.assertIsNotNone(
            self.fila('SELECT ultimo_acceso FROM usuario_sistema WHERE id_usuario=1')[0]
        )
        self.assertEqual(self.cliente.get('/recursos').status_code, 200)

    def test_credenciales_erradas_sin_sesion(self):
        for usuario, clave in (('admin', 'incorrecta'), ('no-existe', 'AdminPrueba2026!')):
            with self.subTest(usuario=usuario):
                respuesta = self.login(usuario, clave)
                self.assertEqual(respuesta.status_code, 200)
                self.assertIn(b'Credenciales incorrectas', respuesta.data)
                with self.cliente.session_transaction() as sesion:
                    self.assertNotIn('id_usuario', sesion)

    def test_login_sin_csrf_es_rechazado(self):
        respuesta = self.cliente.post(
            '/login', data=dict(usuario='admin', clave='AdminPrueba2026!')
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('formulario caducó', respuesta.get_data(as_text=True))

    def test_no_accede_persona_inactiva_ni_cuenta_bloqueada(self):
        self.ejecutar("UPDATE persona SET estado='INACTIVA' WHERE dni='98000001'")
        self.assertEqual(self.login().status_code, 200)
        self.ejecutar("UPDATE persona SET estado='ACTIVA' WHERE dni='98000001'")
        self.ejecutar("UPDATE usuario_sistema SET estado_cuenta='BLOQUEADA' WHERE id_usuario=1")
        self.assertEqual(self.login().status_code, 200)

    def test_cambio_password_invalida_cookie_vigente(self):
        self.login()
        self.ejecutar(
            'UPDATE usuario_sistema SET contrasena_hash=%s WHERE id_usuario=1',
            (generate_password_hash('NuevaClave2026!'),),
        )
        respuesta = self.cliente.get('/recursos')
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.location.endswith('/login'))

    def test_permiso_y_estado_se_recargan_en_cada_peticion(self):
        self.login('usuario1', 'UsuarioPrueba2026!')
        self.ejecutar(
            "DELETE FROM rol_permiso WHERE rol='USUARIO' AND permiso='CATALOGO_CONSULTAR'"
        )
        self.assertEqual(self.cliente.get('/recursos').status_code, 403)
        self.ejecutar("UPDATE persona SET estado='INACTIVA' WHERE dni='02167885'")
        self.assertEqual(self.cliente.get('/prestamos').status_code, 302)

    def test_usuario_no_gestiona_prestamos_y_no_cierra_sesion_por_get(self):
        self.login('usuario1', 'UsuarioPrueba2026!')
        self.assertEqual(self.cliente.get('/prestamos/nuevo').status_code, 403)
        self.assertEqual(self.cliente.get('/logout').status_code, 405)
        self.assertEqual(self.post('/logout').status_code, 302)
        self.assertEqual(self.cliente.get('/recursos').status_code, 302)

    def test_sesion_vence_a_las_ocho_horas_aunque_se_use(self):
        self.login()
        with self.cliente.session_transaction() as sesion:
            sesion['iniciada'] = time() - 8 * 3600 - 1
        self.assertEqual(self.cliente.get('/recursos').status_code, 302)

    def test_pantallas_principales_renderizan_y_no_exponen_hashes(self):
        self.login()
        urls = (
            '/',
            '/personas',
            '/personas/nueva',
            '/personas/02167885',
            '/personas/02167885/editar',
            '/cuentas/99000011/nueva',
            '/cuentas/02167885/editar',
            '/roles',
            '/recursos',
            '/recursos/nuevo',
            '/recursos/1',
            '/recursos/1/editar',
            '/recursos/categorias',
            '/bienes',
            '/bienes/nuevo',
            '/bienes/2',
            '/bienes/2/editar',
            '/politicas',
            '/politicas/nueva',
            '/politicas/24/editar',
            '/prestamos',
            '/prestamos/nuevo',
            '/reservas',
            '/reservas/nueva',
            '/sanciones',
            '/reportes',
        )
        for url in urls:
            with self.subTest(url=url):
                respuesta = self.cliente.get(url, follow_redirects=True)
                self.assertEqual(respuesta.status_code, 200)
                self.assertNotIn('scrypt:', respuesta.get_data(as_text=True))
        identificador = self.prestar()
        self.assertEqual(self.cliente.get(f'/prestamos/{identificador}').status_code, 200)
        reserva = self.reservar()
        self.assertEqual(self.cliente.get(f'/reservas/{reserva}').status_code, 200)
