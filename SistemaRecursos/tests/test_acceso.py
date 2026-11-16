from time import time
from unittest.mock import patch
import re
from werkzeug.security import generate_password_hash
from caso_mysql import CasoMySQL


class AccesoWeb(CasoMySQL):
    def test_inicio_y_navegacion_respetan_el_rol_y_las_acciones_abren(self):
        escenarios = (
            (
                'admin',
                'AdminPrueba2026!',
                [
                    'Inicio',
                    'Personas',
                    'Roles y permisos',
                    'Catálogo de recursos',
                    'Administrar recursos',
                    'Préstamos',
                    'Reservas',
                    'Políticas de préstamo',
                    'Reportes',
                    'Sanciones',
                ],
            ),
            (
                'encargado1',
                'EncargadoPrueba2026!',
                [
                    'Inicio',
                    'Personas',
                    'Catálogo de recursos',
                    'Préstamos',
                    'Reservas',
                    'Reportes',
                    'Sanciones',
                ],
            ),
            (
                'usuario1',
                'UsuarioPrueba2026!',
                [
                    'Inicio',
                    'Catálogo de recursos',
                    'Mis préstamos',
                    'Mis reservas',
                ],
            ),
        )
        for usuario, clave, esperados in escenarios:
            with self.subTest(usuario=usuario):
                login = self.login(usuario, clave)
                self.assertEqual(login.status_code, 302)
                self.assertTrue(login.location.endswith('/'))
                respuesta = self.cliente.get('/')
                self.assertEqual(respuesta.status_code, 200)
                pagina = respuesta.get_data(as_text=True)
                menu = re.search(
                    r'<nav aria-label="Navegación principal">(.*?)</nav>', pagina, re.S
                ).group(1)
                etiquetas = [
                    texto.strip() for texto in re.findall(r'<a\b[^>]*>(.*?)</a>', menu, re.S)
                ]
                self.assertEqual(etiquetas, esperados)
                self.assertRegex(menu, r'href="/"\s+aria-current="page"')
                acciones = re.search(r'<div class="acciones">(.*?)</div>', pagina, re.S).group(1)
                enlaces = re.findall(r'href="([^"]+)"', acciones)
                self.assertTrue(enlaces)
                for enlace in enlaces:
                    with self.subTest(enlace=enlace):
                        self.assertEqual(self.cliente.get(enlace).status_code, 200)
                self.post('/logout')

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

    def test_csrf_rechaza_tokens_ausentes_anteriores_al_login_y_de_otra_sesion(self):
        self.cliente.get('/login')
        token_anterior = self.token()
        self.assertEqual(self.login().status_code, 302)
        self.assertNotEqual(self.token(), token_anterior)
        otro_cliente = self.app.test_client()
        otro_cliente.get('/login')
        with otro_cliente.session_transaction() as sesion:
            token_ajeno = sesion['csrf']
        url = '/personas/99000011/desactivar'
        for datos in (
            {},
            {'csrf_token': 'incorrecto'},
            {'csrf_token': token_anterior},
            {'csrf_token': token_ajeno},
        ):
            with self.subTest(datos=datos):
                self.assertEqual(self.cliente.post(url, data=datos).status_code, 400)
                self.assertEqual(
                    self.fila("SELECT estado FROM persona WHERE dni='99000011'"), ('ACTIVA',)
                )
        self.assertEqual(self.post(url).status_code, 302)
        self.assertEqual(
            self.fila("SELECT estado FROM persona WHERE dni='99000011'"), ('INACTIVA',)
        )

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

    def test_sesion_sigue_activa_despues_de_ocho_horas(self):
        inicio = time()
        with patch('itsdangerous.timed.time.time', return_value=inicio):
            respuesta = self.login()
        self.assertEqual(respuesta.status_code, 302)
        self.assertNotIn('Expires=', respuesta.headers['Set-Cookie'])
        with patch('itsdangerous.timed.time.time', return_value=inicio + 9 * 3600):
            self.assertEqual(self.cliente.get('/recursos').status_code, 200)

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
