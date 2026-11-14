from dominio.compartido.validacion import Conflicto
from caso_mysql import CasoMySQL


class PersonasYCuentas(CasoMySQL):
    def datos_persona(self, documento='02167885'):
        persona, version = self.servicios['personas'].consultar(documento)
        return dict(persona.datos(), version=version)

    def test_edicion_persona_rechaza_formulario_viejo(self):
        datos = self.datos_persona()
        self.servicios['personas'].guardar(dict(datos, nombres='Nuevo'), 1, '02167885')
        with self.assertRaises(Conflicto):
            self.servicios['personas'].guardar(dict(datos, nombres='Perdido'), 1, '02167885')
        self.assertEqual(self.servicios['personas'].consultar('02167885')[0].nombres, 'Nuevo')

    def test_cambio_dni_actualiza_ficha_y_cuenta_juntas(self):
        datos = self.datos_persona()
        self.servicios['personas'].guardar(dict(datos, dni='02167886'), 1, '02167885')
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
            self.servicios['personas'].guardar(datos, 1)
        self.assertEqual(self.fila("SELECT COUNT(*) FROM persona WHERE dni='77777777'"), (0,))

    def test_no_desactivar_propia_persona_ni_ultimo_admin(self):
        with self.assertRaises(ValueError):
            self.servicios['personas'].desactivar('98000001', 1)
        with self.assertRaises(ValueError):
            self.servicios['cuentas'].asignar_rol('98000001', 'USUARIO', 1)

    def test_creacion_y_cambio_clave_por_servicio(self):
        cuentas = self.servicios['cuentas']
        cuentas.crear('99000011', 'nuevo', 'NuevaClave2026!', 1)
        self.assertIsNotNone(self.servicios['acceso'].autenticar('nuevo', 'NuevaClave2026!'))
        cuentas.actualizar(
            '99000011',
            dict(nombre_usuario='nuevo', clave='OtraClave2026!', estado_cuenta='ACTIVA'),
            1,
        )
        self.assertIsNone(self.servicios['acceso'].autenticar('nuevo', 'NuevaClave2026!'))
        self.assertIsNotNone(self.servicios['acceso'].autenticar('nuevo', 'OtraClave2026!'))
        self.assertNotIn('contrasena_hash', cuentas.consultar('99000011'))

    def test_actualizacion_cuenta_no_permite_asignar_rol(self):
        with self.assertRaises(ValueError):
            self.servicios['cuentas'].actualizar(
                '02167885', dict(nombre_usuario='usuario1', rol='ADMINISTRADOR'), 1
            )
        with self.assertRaises(PermissionError):
            self.servicios['cuentas'].crear('99000011', 'nuevo', 'NuevaClave2026!', 2)

    def test_matriz_permisos_con_version_y_reglas_admin(self):
        roles = self.servicios['roles']
        matriz, version = roles.consultar()
        matriz['USUARIO'].append('PERSONAS_CONSULTAR')
        roles.guardar(matriz, version, 1)
        with self.assertRaises(Conflicto):
            roles.guardar(matriz, version, 1)
        self.assertTrue(self.servicios['acceso'].recuperar(3).permite('PERSONAS_CONSULTAR'))
