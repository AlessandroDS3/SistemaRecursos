from dominio.compartido.validacion import Conflicto
from caso_mysql import CasoMySQL


class PersonasYCuentas(CasoMySQL):
    def test_clave_sin_nombre_se_valida_y_no_modifica_cuenta_si_es_invalida(self):
        anterior = self.fila('SELECT contrasena_hash FROM usuario_sistema WHERE id_usuario=3')
        for clave in ('corta', 'x' * 257, None, False, 0, ['ClavePrueba2026!']):
            with self.subTest(tipo=type(clave).__name__), self.assertRaises(ValueError):
                self.servicios['cuentas'].actualizar_cuenta('02167885', dict(clave=clave), 1)
        self.assertEqual(
            self.fila('SELECT contrasena_hash FROM usuario_sistema WHERE id_usuario=3'), anterior
        )

    def test_cambio_solo_de_clave_y_clave_vacia_conserva_la_actual(self):
        self.servicios['cuentas'].actualizar_cuenta('02167885', dict(clave='NuevaClave2026!'), 1)
        self.assertIsNotNone(
            self.servicios['acceso'].autenticar_cuenta('usuario1', 'NuevaClave2026!')
        )
        self.assertIsNone(
            self.servicios['acceso'].autenticar_cuenta('usuario1', 'UsuarioPrueba2026!')
        )
        anterior = self.fila('SELECT contrasena_hash FROM usuario_sistema WHERE id_usuario=3')
        self.servicios['cuentas'].actualizar_cuenta('02167885', dict(clave=''), 1)
        self.assertEqual(
            self.fila('SELECT contrasena_hash FROM usuario_sistema WHERE id_usuario=3'), anterior
        )

    def test_formulario_sin_nombre_no_admite_clave_corta(self):
        self.login()
        anterior = self.fila('SELECT contrasena_hash FROM usuario_sistema WHERE id_usuario=3')
        respuesta = self.post('/cuentas/02167885/editar', dict(clave='corta'))
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            self.fila('SELECT contrasena_hash FROM usuario_sistema WHERE id_usuario=3'), anterior
        )

    def datos_persona(self, documento='02167885'):
        persona, version = self.servicios['personas'].consultar_persona(documento)
        return dict(persona.datos(), version=version)

    def test_edicion_persona_rechaza_formulario_viejo(self):
        datos = self.datos_persona()
        self.servicios['personas'].guardar_persona(dict(datos, nombres='Nuevo'), 1, '02167885')
        with self.assertRaises(Conflicto):
            self.servicios['personas'].guardar_persona(
                dict(datos, nombres='Perdido'), 1, '02167885'
            )
        self.assertEqual(
            self.servicios['personas'].consultar_persona('02167885')[0].nombres, 'Nuevo'
        )

    def test_cambio_dni_actualiza_ficha_y_cuenta_juntas(self):
        datos = self.datos_persona()
        self.servicios['personas'].guardar_persona(dict(datos, dni='02167886'), 1, '02167885')
        self.assertEqual(
            self.fila('SELECT dni FROM estudiante WHERE dni=%s', ('02167886',)), ('02167886',)
        )
        self.assertEqual(
            self.fila('SELECT dni_persona FROM usuario_sistema WHERE id_usuario=3'), ('02167886',)
        )

    def test_alta_con_dato_duplicado_revierte_persona_entera(self):
        from mysql.connector import IntegrityError

        datos = dict(
            self.datos_persona(), dni='77777777', cui='02167885', correo='nuevo@ejemplo.com'
        )
        with self.assertRaises(IntegrityError):
            self.servicios['personas'].guardar_persona(datos, 1)
        self.assertEqual(self.fila("SELECT COUNT(*) FROM persona WHERE dni='77777777'"), (0,))

    def test_no_desactivar_propia_persona_ni_ultimo_admin(self):
        with self.assertRaises(ValueError):
            self.servicios['personas'].desactivar_persona('98000001', 1)
        with self.assertRaises(ValueError):
            self.servicios['cuentas'].asignar_rol_cuenta('98000001', 'USUARIO', 1)

    def test_creacion_y_cambio_clave_por_servicio(self):
        cuentas = self.servicios['cuentas']
        cuentas.registrar_cuenta('99000011', 'nuevo', 'NuevaClave2026!', 1)
        self.assertIsNotNone(self.servicios['acceso'].autenticar_cuenta('nuevo', 'NuevaClave2026!'))
        cuentas.actualizar_cuenta(
            '99000011',
            dict(nombre_usuario='nuevo', clave='OtraClave2026!', estado_cuenta='ACTIVA'),
            1,
        )
        self.assertIsNone(self.servicios['acceso'].autenticar_cuenta('nuevo', 'NuevaClave2026!'))
        self.assertIsNotNone(self.servicios['acceso'].autenticar_cuenta('nuevo', 'OtraClave2026!'))
        self.assertNotIn('contrasena_hash', cuentas.consultar_cuenta('99000011'))

    def test_actualizacion_cuenta_no_permite_asignar_rol(self):
        with self.assertRaises(ValueError):
            self.servicios['cuentas'].actualizar_cuenta(
                '02167885', dict(nombre_usuario='usuario1', rol='ADMINISTRADOR'), 1
            )
        with self.assertRaises(PermissionError):
            self.servicios['cuentas'].registrar_cuenta('99000011', 'nuevo', 'NuevaClave2026!', 2)

    def test_matriz_permisos_con_version_y_reglas_admin(self):
        roles = self.servicios['roles']
        matriz, version = roles.consultar_matriz_permisos()
        matriz['USUARIO'].append('PERSONAS_CONSULTAR')
        roles.guardar_matriz_permisos(matriz, version, 1)
        with self.assertRaises(Conflicto):
            roles.guardar_matriz_permisos(matriz, version, 1)
        self.assertTrue(
            self.servicios['acceso'].consultar_cuenta_activa(3).permite('PERSONAS_CONSULTAR')
        )
