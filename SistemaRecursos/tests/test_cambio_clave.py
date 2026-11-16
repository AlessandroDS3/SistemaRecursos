from werkzeug.security import check_password_hash
from caso_mysql import CasoMySQL


class CambioClavePropia(CasoMySQL):
    ruta = '/cuentas/mi-contrasena'
    nueva = 'MiNuevaClave2026!'

    def datos(self, **cambios):
        return dict(
            clave_actual='UsuarioPrueba2026!',
            clave_nueva=self.nueva,
            confirmacion=self.nueva,
            **cambios,
        )

    def test_formulario_disponible_para_los_tres_roles_y_exige_sesion(self):
        self.assertEqual(self.cliente.get(self.ruta).status_code, 302)
        for usuario, clave in (
            ('admin', 'AdminPrueba2026!'),
            ('encargado1', 'EncargadoPrueba2026!'),
            ('usuario1', 'UsuarioPrueba2026!'),
        ):
            self.cliente = self.app.test_client()
            self.login(usuario, clave)
            self.assertIn(self.ruta, self.cliente.get('/').get_data(as_text=True))
            pagina = self.cliente.get(self.ruta)
            self.assertEqual(pagina.status_code, 200)
            self.assertIn('autocomplete="current-password"', pagina.get_data(as_text=True))

    def test_rechaza_clave_actual_incorrecta_confirmacion_y_longitud_y_csrf(self):
        self.login('usuario1', 'UsuarioPrueba2026!')
        antes = self.fila('SELECT contrasena_hash FROM usuario_sistema WHERE id_usuario=3')
        for cambios in (
            {'clave_actual': 'incorrecta'},
            {'confirmacion': 'diferente'},
            {'clave_nueva': 'corta', 'confirmacion': 'corta'},
        ):
            datos = self.datos()
            datos.update(cambios)
            respuesta = self.post(self.ruta, datos)
            self.assertEqual(respuesta.status_code, 400)
            self.assertNotIn(self.nueva, respuesta.get_data(as_text=True))
        self.assertEqual(self.cliente.post(self.ruta, data=self.datos()).status_code, 400)
        self.assertEqual(
            self.fila('SELECT contrasena_hash FROM usuario_sistema WHERE id_usuario=3'), antes
        )

    def test_cambia_solo_la_cuenta_de_sesion_y_revoca_las_sesiones_anteriores(self):
        self.login('usuario1', 'UsuarioPrueba2026!')
        otro = self.app.test_client()
        otro.get('/login')
        with otro.session_transaction() as sesion:
            token = sesion['csrf']
        otro.post(
            '/login', data=dict(usuario='usuario1', clave='UsuarioPrueba2026!', csrf_token=token)
        )
        administrador = self.fila('SELECT contrasena_hash FROM usuario_sistema WHERE id_usuario=1')
        datos = self.datos(
            id_usuario='1',
            documento='98000001',
            rol='ADMINISTRADOR',
            estado_cuenta='BLOQUEADA',
            nombre_usuario='intruso',
        )
        respuesta = self.post(self.ruta, datos)
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.location.endswith('/login'))
        self.assertEqual(self.cliente.get('/').status_code, 302)
        self.assertEqual(otro.get('/').status_code, 302)
        self.assertEqual(
            self.fila('SELECT contrasena_hash FROM usuario_sistema WHERE id_usuario=1'),
            administrador,
        )
        nombre, rol, estado, clave = self.fila(
            'SELECT nombre_usuario,rol,estado_cuenta,contrasena_hash FROM usuario_sistema WHERE id_usuario=3'
        )
        self.assertEqual((nombre, rol, estado), ('usuario1', 'USUARIO', 'ACTIVA'))
        self.assertTrue(check_password_hash(clave, self.nueva))
        self.assertEqual(self.login('usuario1', 'UsuarioPrueba2026!').status_code, 200)
        self.assertEqual(self.login('usuario1', self.nueva).status_code, 302)

    def test_servicio_rechaza_cuenta_inactiva(self):
        self.ejecutar("UPDATE usuario_sistema SET estado_cuenta='BLOQUEADA' WHERE id_usuario=3")
        with self.assertRaises(PermissionError):
            self.servicios['cuentas'].cambiar_clave_propia(
                3, 'UsuarioPrueba2026!', self.nueva, self.nueva
            )
