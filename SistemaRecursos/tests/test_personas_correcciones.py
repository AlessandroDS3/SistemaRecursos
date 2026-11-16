import re

from dominio.compartido.validacion import Conflicto
from caso_mysql import CasoMySQL


class CorreccionesPersonasYCuentas(CasoMySQL):
    def datos_cuenta(self, **cambios):
        cuenta = self.servicios['cuentas'].consultar_cuenta('02167885')
        return dict(
            nombre_usuario=cuenta['nombre_usuario'],
            estado_cuenta=cuenta['estado_cuenta'],
            clave='',
            version=cuenta['version'],
            **cambios,
        )

    def test_formulario_antiguo_o_sin_version_no_reactiva_cuenta_bloqueada(self):
        self.login()
        pagina = self.cliente.get('/cuentas/02167885/editar').get_data(as_text=True)
        version = re.search(r'name="version"\s+value="([^"]+)"', pagina).group(1)
        anterior = self.datos_cuenta()
        self.assertEqual(anterior['version'], version)
        actual = dict(anterior, estado_cuenta='BLOQUEADA')
        self.assertEqual(self.post('/cuentas/02167885/editar', actual).status_code, 302)
        for datos in (anterior, dict(nombre_usuario='usuario1', estado_cuenta='ACTIVA', clave='')):
            with self.subTest(datos=datos):
                self.assertEqual(self.post('/cuentas/02167885/editar', datos).status_code, 409)
        cuenta = self.servicios['cuentas'].consultar_cuenta('02167885')
        self.assertEqual(cuenta['estado_cuenta'], 'BLOQUEADA')
        self.assertNotIn('contrasena_hash', cuenta)
        vigente = self.datos_cuenta()
        self.assertEqual(
            self.post(
                '/cuentas/02167885/editar', dict(vigente, estado_cuenta='ACTIVA')
            ).status_code,
            302,
        )

    def test_version_detecta_clave_rol_y_persona_pero_no_ultimo_acceso(self):
        cuentas = self.servicios['cuentas']
        anterior = self.datos_cuenta()
        self.servicios['acceso'].autenticar_cuenta('usuario1', 'UsuarioPrueba2026!')
        cuentas.actualizar_cuenta('02167885', anterior, 1)
        self.servicios['cuentas'].cambiar_clave_propia(
            3, 'UsuarioPrueba2026!', 'OtraClave2026!', 'OtraClave2026!'
        )
        with self.assertRaises(Conflicto):
            cuentas.actualizar_cuenta('02167885', anterior, 1)
        anterior = self.datos_cuenta()
        cuentas.asignar_rol_cuenta('02167885', 'ENCARGADO_PRESTAMOS', 1)
        with self.assertRaises(Conflicto):
            cuentas.actualizar_cuenta('02167885', anterior, 1)
        anterior = self.datos_cuenta()
        self.servicios['personas'].desactivar_persona('02167885', 1)
        with self.assertRaises(Conflicto):
            cuentas.actualizar_cuenta('02167885', anterior, 1)

    def test_etiqueta_y_enlaces_reflejan_persona_y_cuenta(self):
        self.login()
        for documento, tiene_cuenta in (('02167885', True), ('99000011', False)):
            with self.subTest(documento=documento):
                pagina = self.cliente.get('/personas/' + documento).get_data(as_text=True)
                self.assertEqual(f'href="/cuentas/{documento}/editar"' in pagina, tiene_cuenta)
                self.assertEqual(f'href="/cuentas/{documento}/nueva"' in pagina, not tiene_cuenta)
                self.servicios['personas'].desactivar_persona(documento, 1)
                pagina = self.cliente.get('/personas/' + documento).get_data(as_text=True)
                self.assertNotIn(f'href="/cuentas/{documento}/nueva"', pagina)
                listado = self.cliente.get('/personas?q=' + documento).get_data(as_text=True)
                fila = re.search(r'<tbody>.*?<tr>(.*?)</tr>', listado, re.S).group(1)
                self.assertNotIn('Con acceso', fila)
                self.assertNotIn(f'href="/cuentas/{documento}/nueva"', fila)
        self.assertIsNone(
            self.servicios['acceso'].autenticar_cuenta('usuario1', 'UsuarioPrueba2026!')
        )

    def test_creacion_de_cuenta_rechaza_persona_ausente_inactiva_o_con_cuenta(self):
        self.login()
        self.servicios['personas'].desactivar_persona('99000011', 1)
        for documento, codigo in (('77777777', 404), ('99000011', 400), ('02167885', 409)):
            with self.subTest(documento=documento):
                ruta = f'/cuentas/{documento}/nueva'
                self.assertEqual(self.cliente.get(ruta).status_code, codigo)
                self.assertEqual(
                    self.post(
                        ruta, dict(nombre_usuario='nuevo', clave='ClavePrueba2026!')
                    ).status_code,
                    codigo,
                )
        self.assertEqual(self.fila('SELECT COUNT(*) FROM usuario_sistema'), (3,))

    def test_duplicados_personales_devuelven_conflicto_y_revierten_todo(self):
        self.login()
        comunes = dict(
            dni='77000001',
            nombres='Persona',
            apellidos='Nueva',
            correo='nueva@ejemplo.com',
            tipo='ESTUDIANTE',
            cui='77000001',
        )
        total = self.fila('SELECT COUNT(*) FROM persona')
        for cambios, mensaje in (
            ({'dni': '02167885'}, 'DNI'),
            ({'correo': '02167885@ejemplo.com'}, 'correo'),
            ({'cui': '02167885'}, 'CUI'),
        ):
            with self.subTest(cambios=cambios):
                respuesta = self.post('/personas/nueva', dict(comunes, **cambios))
                self.assertEqual(respuesta.status_code, 409)
                self.assertIn(mensaje, respuesta.get_data(as_text=True))
                self.assertEqual(self.fila('SELECT COUNT(*) FROM persona'), total)
        persona, version = self.servicios['personas'].consultar_persona('99000011')
        respuesta = self.post(
            '/personas/99000011/editar',
            dict(persona.datos(), version=version, correo='02167885@ejemplo.com'),
        )
        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(
            self.servicios['personas'].consultar_persona('99000011')[0].correo, persona.correo
        )

    def test_tres_tipos_crean_cuenta_y_codigos_institucionales_no_se_duplican(self):
        self.login()
        for numero, (tipo, campos, codigo) in enumerate(
            (
                ('ESTUDIANTE', dict(cui='77000001', estado_matricula='VIGENTE'), 'CUI'),
                (
                    'DOCENTE',
                    dict(
                        codigo_docente='DOC-1',
                        departamento_academico='Computación',
                        facultad='Ingeniería',
                        escuela_profesional='Computación',
                    ),
                    'código docente',
                ),
                (
                    'ADMINISTRATIVO',
                    dict(codigo_empleado='EMP-1', area='Biblioteca'),
                    'código de empleado',
                ),
            ),
            1,
        ):
            with self.subTest(tipo=tipo):
                documento = f'7700000{numero}'
                datos = dict(
                    dni=documento,
                    nombres='Persona',
                    apellidos=tipo,
                    correo=documento + '@ejemplo.com',
                    tipo=tipo,
                    **campos,
                )
                self.assertEqual(self.post('/personas/nueva', datos).status_code, 302)
                self.assertEqual(self.cliente.get(f'/cuentas/{documento}/nueva').status_code, 200)
                self.assertEqual(
                    self.post(
                        f'/cuentas/{documento}/nueva',
                        dict(
                            nombre_usuario='nuevo' + str(numero),
                            clave='PruebaPersona2026!',
                            rol='ADMINISTRADOR',
                        ),
                    ).status_code,
                    302,
                )
                self.assertEqual(
                    self.servicios['cuentas'].consultar_cuenta(documento)['rol'], 'USUARIO'
                )
                duplicado = dict(datos, dni='77000009', correo='duplicado@ejemplo.com')
                respuesta = self.post('/personas/nueva', duplicado)
                self.assertEqual(respuesta.status_code, 409)
                self.assertIn(codigo, respuesta.get_data(as_text=True))
                self.assertEqual(
                    self.fila("SELECT COUNT(*) FROM persona WHERE dni='77000009'"), (0,)
                )

    def test_usuario_duplicado_en_alta_y_edicion_no_modifica_cuentas(self):
        self.login()
        respuesta = self.post(
            '/cuentas/99000011/nueva', dict(nombre_usuario='usuario1', clave='PruebaPersona2026!')
        )
        self.assertEqual(respuesta.status_code, 409)
        self.assertIn('nombre de usuario', respuesta.get_data(as_text=True))
        self.assertFalse(self.servicios['cuentas'].tiene_cuenta('99000011'))
        respuesta = self.post(
            '/cuentas/02167885/editar', dict(self.datos_cuenta(), nombre_usuario='admin')
        )
        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(
            self.servicios['cuentas'].consultar_cuenta('02167885')['nombre_usuario'], 'usuario1'
        )
