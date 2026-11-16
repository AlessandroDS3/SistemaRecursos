from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from dominio.compartido.validacion import Conflicto
from dominio.gestion_personas_usuarios.rol import DEPENDENCIAS_PERMISOS
from repositorio.repositorio_cuenta_sql import RepositorioCuentaSQL, cargar_cuentas_para_actualizar
from repositorio.repositorio_persona_sql import RepositorioPersonaSQL
from caso_mysql import CasoMySQL


class PersonasYCuentas(CasoMySQL):
    def test_matriz_incompleta_se_rechaza_por_http_sin_cambiar_permisos(self):
        self.login()
        roles = self.servicios['roles']
        original, version = roles.consultar_matriz_permisos()
        for permiso in DEPENDENCIAS_PERMISOS:
            with self.subTest(permiso=permiso):
                matriz = {rol: list(permisos) for rol, permisos in original.items()}
                matriz['ENCARGADO_PRESTAMOS'] = [permiso]
                datos = {'permisos_' + rol: permisos for rol, permisos in matriz.items()}
                datos['version'] = version
                respuesta = self.post('/roles/permisos', datos)
                self.assertEqual(respuesta.status_code, 400)
                self.assertIn('también debes marcar', respuesta.get_data(as_text=True))
                self.assertEqual(roles.consultar_matriz_permisos(), (original, version))

    def test_permisos_personalizados_permiten_completar_la_navegacion_y_el_guardado(self):
        self.login('usuario1', 'UsuarioPrueba2026!')
        self.assertNotIn('Registrar persona', self.cliente.get('/').get_data(as_text=True))
        roles = self.servicios['roles']
        matriz, version = roles.consultar_matriz_permisos()
        matriz['USUARIO'].extend(
            ('PERSONAS_GESTIONAR', 'PERSONAS_CONSULTAR', 'ROLES_GESTIONAR', 'ROLES_CONSULTAR')
        )
        roles.guardar_matriz_permisos(matriz, version, 1)
        inicio = self.cliente.get('/').get_data(as_text=True)
        self.assertIn('Registrar persona', inicio)
        self.assertIn('Gestionar permisos', inicio)
        for ruta in ('/personas', '/personas/nueva', '/roles'):
            self.assertEqual(self.cliente.get(ruta).status_code, 200)
        respuesta = self.post(
            '/personas/nueva',
            dict(
                dni='77777777',
                nombres='Persona',
                apellidos='Personalizada',
                correo='personalizada@ejemplo.com',
                tipo='ESTUDIANTE',
                cui='77777777',
                ciclo='1',
                estado_matricula='VIGENTE',
            ),
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.cliente.get(respuesta.location).status_code, 200)
        matriz, version = roles.consultar_matriz_permisos()
        datos = {'permisos_' + rol: permisos for rol, permisos in matriz.items()}
        datos['version'] = version
        respuesta = self.post('/roles/permisos', datos)
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.cliente.get(respuesta.location).status_code, 200)

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

    def test_editar_datos_personales_no_espera_el_bloqueo_de_otra_cuenta(self):
        for estado in ('ACTIVA', 'INACTIVA'):
            with self.subTest(estado=estado):
                self.ejecutar("UPDATE persona SET estado=%s WHERE dni='02167885'", (estado,))
                datos = dict(self.datos_persona(), telefono='999888777')
                ejecutor = ThreadPoolExecutor(max_workers=1)
                try:
                    with self.db.sesion(escritura=True) as cursor:
                        cursor.execute(
                            'SELECT id_usuario FROM usuario_sistema WHERE id_usuario=1 FOR UPDATE'
                        )
                        cursor.fetchall()
                        guardado = ejecutor.submit(
                            self.servicios['personas'].guardar_persona, datos, 1, '02167885'
                        )
                        self.assertEqual(guardado.result(timeout=5), '02167885')
                finally:
                    ejecutor.shutdown(wait=True)
                self.assertEqual(
                    self.fila("SELECT telefono,estado FROM persona WHERE dni='02167885'"),
                    ('999888777', estado),
                )

    def test_cambio_concurrente_de_estado_rechaza_la_edicion_ya_preparada(self):
        datos = dict(self.datos_persona(), telefono='999888777')
        consultar = RepositorioPersonaSQL.consultar_persona

        def consultar_despues_del_cambio(repositorio, documento, bloquear=False):
            if bloquear:
                with self.db.sesion(escritura=True) as cursor:
                    cursor.execute(
                        "UPDATE persona SET estado='INACTIVA' WHERE dni=%s", (documento,)
                    )
            return consultar(repositorio, documento, bloquear)

        with patch.object(RepositorioPersonaSQL, 'consultar_persona', consultar_despues_del_cambio):
            with self.assertRaises(Conflicto):
                self.servicios['personas'].guardar_persona(datos, 1, '02167885')
        self.assertEqual(
            self.fila("SELECT telefono,estado FROM persona WHERE dni='02167885'"),
            (None, 'INACTIVA'),
        )

    def test_cambios_simultaneos_de_persona_y_rol_conservan_un_administrador(self):
        cuentas = self.servicios['cuentas']
        segundo = cuentas.registrar_cuenta('99000011', 'segundo_admin', 'NuevaClave2026!', 1)
        cuentas.asignar_rol_cuenta('99000011', 'ADMINISTRADOR', 1)

        for segunda_operacion in ('desactivar', 'cambiar_rol'):
            with self.subTest(segunda_operacion=segunda_operacion):
                self.ejecutar(
                    "UPDATE persona SET estado='ACTIVA' WHERE dni IN ('98000001','99000011')"
                )
                self.ejecutar(
                    "UPDATE usuario_sistema SET rol='ADMINISTRADOR' WHERE id_usuario IN (1,%s)",
                    (segundo,),
                )
                datos_primero = dict(self.datos_persona('98000001'), estado='INACTIVA')
                datos_segundo = dict(self.datos_persona('99000011'), estado='INACTIVA')
                barrera = Barrier(2)

                def bloquear_juntos(repositorio):
                    barrera.wait(timeout=5)
                    return cargar_cuentas_para_actualizar(repositorio)

                with (
                    patch.object(
                        RepositorioPersonaSQL, 'consultar_cuentas_para_actualizar', bloquear_juntos
                    ),
                    patch.object(
                        RepositorioCuentaSQL, 'consultar_cuentas_para_actualizar', bloquear_juntos
                    ),
                    ThreadPoolExecutor(max_workers=2) as ejecutor,
                ):
                    primera = ejecutor.submit(
                        self.servicios['personas'].guardar_persona, datos_segundo, 1, '99000011'
                    )
                    if segunda_operacion == 'desactivar':
                        segunda = ejecutor.submit(
                            self.servicios['personas'].guardar_persona,
                            datos_primero,
                            segundo,
                            '98000001',
                        )
                    else:
                        segunda = ejecutor.submit(
                            cuentas.asignar_rol_cuenta, '98000001', 'USUARIO', segundo
                        )
                    errores = [tarea.exception(timeout=10) for tarea in (primera, segunda)]

                self.assertEqual(sum(error is None for error in errores), 1, errores)
                self.assertTrue(
                    all(
                        error is None or isinstance(error, (ValueError, PermissionError))
                        for error in errores
                    ),
                    errores,
                )
                self.assertEqual(
                    self.fila(
                        """SELECT COUNT(*) FROM usuario_sistema u JOIN persona p ON p.dni=u.dni_persona
                        WHERE u.rol='ADMINISTRADOR' AND u.estado_cuenta='ACTIVA' AND p.estado='ACTIVA'"""
                    ),
                    (1,),
                )

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
