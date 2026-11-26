"""Integración con MySQL del cierre de pendientes del informe.

Cubre SEG-01, SEG-02, SEG-03, AUT-01, AUT-02, MAN-01, AMP-01, OPE-01 y casos de
PRU-01 y PRU-03. Usa la misma base exclusiva de pruebas que test_sanciones_mysql:
requiere TEST_MYSQL_PORT (y TEST_MYSQL_PASSWORD si corresponde); cada caso crea y borra
su propia base, nunca la de la aplicación.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import json
import re
from threading import Barrier
import unittest
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from app import create_app, crear_servicios
from dominio.compartido.validacion import LIMA, Conflicto
from repositorio.control.repositorio_procesador_sql import RepositorioProcesadorSQL
from servicios.control.servicio_procesador import ServicioAplicacionProcesador
from tests.integracion.test_sanciones_mysql import BaseMySQLTest
from tests.soporte_roles import crear_cliente_con_sesion_simulada

CLAVE = 'ClavePrueba2026!'


def capturar_resultado_o_excepcion(funcion, *args):
    try:
        return 'ok', funcion(*args)
    except Exception as error:  # Las pruebas comparan qué operaciones fallaron.
        return 'error', error


class CierreMySQLTest(BaseMySQLTest):
    def setUp(self):
        super().setUp()
        clave = generate_password_hash(CLAVE, method='pbkdf2:sha256:1000')
        with self.conexion.sesion(escritura=True) as cur:
            for documento, nombre in (('10000001', 'Admin'), ('10000002', 'Encargado'),
                                      ('20000001', 'Lucia'), ('20000002', 'Diego')):
                cur.execute('INSERT INTO persona(dni,nombres,apellidos,estado) VALUES(%s,%s,%s,%s)',
                            (documento, nombre, 'Prueba', 'ACTIVA'))
            for identificador, rol, documento, usuario in (
                (1, 'ADMINISTRADOR', '10000001', 'admin'),
                (2, 'ENCARGADO_PRESTAMOS', '10000002', 'encargado'),
                (3, 'USUARIO', '20000001', 'lucia'),
                (4, 'USUARIO', '20000002', 'diego'),
            ):
                cur.execute('''INSERT INTO usuario_sistema(id_usuario,dni_persona,nombre_usuario,
                    contrasena_hash,rol) VALUES(%s,%s,%s,%s,%s)''',
                            (identificador, documento, usuario, clave, rol))
            cur.execute("INSERT INTO estudiante(dni,cui) VALUES('20000001','20000001'),('20000002','20000002')")
            cur.execute("INSERT INTO categoria_recurso(id_categoria,nombre) VALUES(1,'Equipos')")
            cur.execute("INSERT INTO recurso(id_recurso,id_categoria,nombre) VALUES(1,1,'Laptop')")
            cur.execute("""INSERT INTO bien_material(id_bien,id_recurso,codigo_inventario,estado)
                VALUES(1,1,'LAP-1','DISPONIBLE'),(2,1,'LAP-2','DISPONIBLE'),(3,1,'LAP-3','DISPONIBLE')""")
            cur.execute("""INSERT INTO politica_prestamo(id_politica,tipo_persona,id_categoria,
                plazo_maximo,unidad_plazo) VALUES(1,'ESTUDIANTE',1,3,'DIAS')""")
            cur.execute("INSERT INTO limite_articulos_prestamo VALUES('ESTUDIANTE',3)")
            cur.execute("""INSERT INTO configuracion_general(id_configuracion,hora_apertura,hora_cierre,
                dias_atencion,plazo_espera,plazo_retiro) VALUES(1,'00:00','23:59',127,2,24)""")
        self.servicios = crear_servicios(self.conexion)

    # Utilidades

    def registrar_prestamo_de_prueba(self, bienes=(1,), persona='20000001', participantes=(), actor=2, autorizacion=None):
        return self.servicios['prestamos'].registrar_prestamo(dict(
            dni_persona=persona, bienes=[str(b) for b in bienes], acepta_condiciones='1',
            tipo_prestamo='GRUPAL' if participantes else 'INDIVIDUAL', participantes=participantes,
            autorizacion=autorizacion,
        ), actor)

    def consultar_detalle_por_prestamo_y_bien(self, prestamo, bien):
        return self.ejecutar_sql_de_prueba('SELECT * FROM detalle_prestamo WHERE id_prestamo=%s AND id_bien=%s',
                             (prestamo, bien))[0]

    def crear_aplicacion_de_prueba(self):
        with patch('app.obtener_clave_de_sesion_flask', return_value='pruebas-cierre'):
            return create_app(dict(TESTING=True, MYSQL_CONFIG=self.config))

    def enviar_formulario_de_inicio_de_sesion(self, aplicacion, usuario, clave=CLAVE, origen='10.0.0.1'):
        cliente = aplicacion.test_client()
        with cliente.session_transaction() as sesion:
            sesion['csrf'] = 'token'
        respuesta = cliente.post('/login', data=dict(csrf_token='token', usuario=usuario, clave=clave),
                                 environ_base={'REMOTE_ADDR': origen})
        return cliente, respuesta

    def test_registrar_y_editar_categoria_desde_los_formularios(self):
        cliente, sesion_iniciada = self.enviar_formulario_de_inicio_de_sesion(self.crear_aplicacion_de_prueba(), 'admin')
        self.assertEqual(sesion_iniciada.status_code, 302)
        categorias = '/recursos/categorias'
        listado = cliente.get(categorias)
        self.assertEqual(listado.status_code, 200)
        self.assertIn(f'action="{categorias}"', listado.get_data(as_text=True))

        with cliente.session_transaction() as sesion:
            csrf = sesion['csrf']
        alta = cliente.post(categorias, data=dict(csrf_token=csrf, nombre='Proyectores'))
        self.assertEqual((alta.status_code, alta.location), (302, categorias))
        fila = self.ejecutar_sql_de_prueba("SELECT id_categoria FROM categoria_recurso WHERE nombre='Proyectores'")[0]
        identificador = fila['id_categoria']
        version = self.servicios['recursos'].consultar_categoria(identificador)['version']
        cambio = cliente.post(categorias, data=dict(
            csrf_token=csrf, id_categoria=identificador, version=version, nombre='Proyectores y pantallas',
        ))
        self.assertEqual((cambio.status_code, cambio.location), (302, categorias))
        self.assertIn('Proyectores y pantallas', cliente.get(categorias).get_data(as_text=True))
        self.assertEqual(self.ejecutar_sql_de_prueba('SELECT nombre FROM categoria_recurso WHERE id_categoria=%s', (identificador,)),
                         [dict(nombre='Proyectores y pantallas')])

    # SEG-01

    def test_login_bloquea_intentos_por_cuenta(self):
        aplicacion = self.crear_aplicacion_de_prueba()
        for _ in range(5):
            _, respuesta = self.enviar_formulario_de_inicio_de_sesion(aplicacion, 'lucia', 'incorrecta')
            self.assertEqual(respuesta.status_code, 401)
        _, respuesta = self.enviar_formulario_de_inicio_de_sesion(aplicacion, 'lucia')
        self.assertEqual(respuesta.status_code, 429, 'la clave correcta también espera el bloqueo')
        self.assertIn('Demasiados intentos', respuesta.get_data(as_text=True))
        _, respuesta = self.enviar_formulario_de_inicio_de_sesion(aplicacion, 'diego')
        self.assertEqual(respuesta.status_code, 302, 'otra cuenta del mismo origen sigue entrando')

    def test_login_limita_intentos_de_cuenta_inexistente(self):
        aplicacion = self.crear_aplicacion_de_prueba()
        for _ in range(5):
            self.enviar_formulario_de_inicio_de_sesion(aplicacion, 'no-existe', 'x', origen='10.0.0.9')
        _, respuesta = self.enviar_formulario_de_inicio_de_sesion(aplicacion, 'no-existe', 'x', origen='10.0.0.9')
        self.assertEqual(respuesta.status_code, 429)

    # SEG-02

    def test_cerrar_sesion_invalida_la_cookie_copiada(self):
        aplicacion = self.crear_aplicacion_de_prueba()
        cliente, respuesta = self.enviar_formulario_de_inicio_de_sesion(aplicacion, 'lucia')
        self.assertEqual(respuesta.status_code, 302)
        cookie = cliente.get_cookie('recursos_rehecho').value
        self.assertEqual(cliente.get('/').status_code, 200)
        with cliente.session_transaction() as sesion:
            sesion['csrf'] = 'token'
        cookie = cliente.get_cookie('recursos_rehecho').value
        cliente.post('/logout', data=dict(csrf_token='token'))
        copia = aplicacion.test_client()
        copia.set_cookie('recursos_rehecho', cookie)
        respuesta = copia.get('/')
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/login', respuesta.headers['Location'])
        self.assertEqual(self.ejecutar_sql_de_prueba('SELECT COUNT(*) n FROM sesion_usuario WHERE fecha_cierre IS NULL')[0]['n'], 0)

    def test_sesion_vence_por_inactividad_o_duracion_maxima(self):
        acceso = self.servicios['acceso']
        token = acceso.crear_sesion_de_cuenta(3)
        self.assertTrue(acceso.validar_sesion(token, 3))
        self.assertFalse(acceso.validar_sesion(token, 4), 'el token pertenece a otra cuenta')
        self.ejecutar_sql_de_prueba('UPDATE sesion_usuario SET ultima_actividad=UTC_TIMESTAMP()-INTERVAL 31 MINUTE')
        self.assertFalse(acceso.validar_sesion(token, 3))
        self.assertIsNotNone(self.ejecutar_sql_de_prueba('SELECT fecha_cierre FROM sesion_usuario')[0]['fecha_cierre'])
        otra = acceso.crear_sesion_de_cuenta(3)
        self.ejecutar_sql_de_prueba('''UPDATE sesion_usuario SET fecha_inicio=UTC_TIMESTAMP()-INTERVAL 9 HOUR
            WHERE fecha_cierre IS NULL''')
        self.assertFalse(acceso.validar_sesion(otra, 3))

    def test_desactivar_cuenta_cierra_el_acceso_de_inmediato(self):
        aplicacion = self.crear_aplicacion_de_prueba()
        cliente, _ = self.enviar_formulario_de_inicio_de_sesion(aplicacion, 'lucia')
        self.assertEqual(cliente.get('/').status_code, 200)
        self.ejecutar_sql_de_prueba("UPDATE usuario_sistema SET estado_cuenta='INACTIVA' WHERE id_usuario=3")
        self.assertEqual(cliente.get('/').status_code, 302)

    def test_restablecer_acceso_auditado_con_codigo_de_un_solo_uso(self):
        app = self.crear_aplicacion_de_prueba()
        cliente, _ = self.enviar_formulario_de_inicio_de_sesion(app, 'lucia')
        admin, _ = self.enviar_formulario_de_inicio_de_sesion(app, 'admin')
        encargado, _ = self.enviar_formulario_de_inicio_de_sesion(app, 'encargado')
        version = self.servicios['cuentas'].consultar_cuenta('20000001')['version']
        with encargado.session_transaction() as sesion:
            formulario = dict(csrf_token=sesion['csrf'], motivo='Solicitud verificada', version=version)
        self.assertEqual(encargado.post('/cuentas/20000001/restablecer', data=formulario).status_code, 403)
        with admin.session_transaction() as sesion:
            formulario['csrf_token'] = sesion['csrf']
        self.assertEqual(admin.post('/cuentas/10000001/restablecer', data=formulario).status_code, 403)
        respuesta = admin.post('/cuentas/20000001/restablecer', data=formulario)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(admin.post('/cuentas/20000001/restablecer', data=formulario).status_code, 409)
        self.assertIn('no-store', respuesta.headers['Cache-Control'])
        codigo = re.search(r'<code>([A-Za-z0-9_-]{43})</code>', respuesta.get_data(as_text=True))[1]
        self.assertEqual(cliente.get('/').location, '/login')
        self.assertEqual(self.enviar_formulario_de_inicio_de_sesion(app, 'lucia', codigo)[1].status_code, 401)
        self.assertEqual(self.enviar_formulario_de_inicio_de_sesion(app, 'lucia')[1].status_code, 401)
        cliente.get('/cuentas/activar')
        with cliente.session_transaction() as datos:
            csrf = datos['csrf']
        clave = 'OtraClaveSegura2026!'
        datos_publicos = dict(csrf_token=csrf, usuario='lucia', codigo=codigo, clave_nueva=clave, confirmacion=clave)
        self.assertEqual(cliente.post('/cuentas/activar', data=datos_publicos).location, '/login')
        cliente.get('/cuentas/activar')
        with cliente.session_transaction() as datos:
            datos_publicos['csrf_token'] = datos['csrf']
        self.assertEqual(cliente.post('/cuentas/activar', data=datos_publicos).status_code, 400)
        self.assertEqual(self.enviar_formulario_de_inicio_de_sesion(app, 'lucia', clave)[1].location, '/')
        filas = self.ejecutar_sql_de_prueba("SELECT observacion,dni_responsable FROM historial_estado WHERE entidad='CUENTA' AND estado_nuevo='RESTABLECIDA'")
        self.assertEqual(filas, [dict(observacion='Solicitud verificada', dni_responsable='10000001')])

    def test_cambios_simultaneos_conservan_un_administrador_activo(self):
        self.ejecutar_sql_de_prueba("UPDATE usuario_sistema SET rol='ADMINISTRADOR',debe_cambiar_clave=FALSE WHERE id_usuario=2")
        cuentas = self.servicios['cuentas']
        barrera = Barrier(2)

        def desactivar_cuenta_en_simultaneo(par):
            documento, actor = par
            datos = dict(version=cuentas.consultar_cuenta(documento)['version'], estado_cuenta='INACTIVA')
            barrera.wait(timeout=10)
            return capturar_resultado_o_excepcion(cuentas.actualizar_cuenta, documento, datos, actor)

        with ThreadPoolExecutor(max_workers=2) as hilos:
            resultados = list(hilos.map(desactivar_cuenta_en_simultaneo, [('10000001', 2), ('10000002', 1)]))
        self.assertEqual(sum(estado == 'ok' for estado, _ in resultados), 1)
        self.assertIsInstance(next(error for estado, error in resultados if estado == 'error'), PermissionError)
        self.assertEqual(self.ejecutar_sql_de_prueba("SELECT COUNT(*) n FROM usuario_sistema WHERE rol='ADMINISTRADOR' AND estado_cuenta='ACTIVA'")[0]['n'], 1)

    def test_alta_de_cuentas_elige_correo_cui_o_nombre_manual(self):
        for documento, correo in [('30000001', 'lucia@unsa.edu.pe'), ('30000002', None), ('30000003', None)]:
            self.ejecutar_sql_de_prueba("INSERT INTO persona(dni,nombres,apellidos,correo) VALUES(%s,'Persona','Prueba',%s)",
                          (documento, correo))
        self.ejecutar_sql_de_prueba("INSERT INTO estudiante(dni,cui) VALUES('30000002','20267777')")
        cuentas = self.servicios['cuentas']
        self.assertEqual(cuentas.consultar_propuesta_cuenta('30000001')['nombre_usuario'], 'lucia2')
        self.assertEqual(cuentas.consultar_propuesta_cuenta('30000002')['nombre_usuario'], '20267777')
        self.assertTrue(cuentas.consultar_propuesta_cuenta('30000003')['requiere_nombre'])
        with self.assertRaises(Conflicto):
            cuentas.registrar_cuenta('30000003', 'lucia', 1)
        alta = cuentas.registrar_cuenta('30000003', 'invitada', 1)
        self.ejecutar_sql_de_prueba("""UPDATE usuario_sistema
            SET contrasena_hash=CONCAT('activacion$1$',SUBSTRING_INDEX(contrasena_hash,'$',-1))
            WHERE id_usuario=%s""", (alta.id_usuario,))
        with self.assertRaisesRegex(ValueError, 'venció'):
            cuentas.activar_cuenta('invitada', alta.codigo_activacion, CLAVE, CLAVE)

    def test_cambiar_rol_dos_veces_no_reabre_sesion_anterior(self):
        cliente, _ = self.enviar_formulario_de_inicio_de_sesion(self.crear_aplicacion_de_prueba(), 'lucia')
        cuentas = self.servicios['cuentas']
        for rol in ('ENCARGADO_PRESTAMOS', 'USUARIO'):
            version = cuentas.consultar_cuenta('20000001')['version']
            cuentas.actualizar_cuenta('20000001', dict(version=version, rol=rol), 1)
        self.assertEqual(cliente.get('/').location, '/login')

    def test_perder_habilitacion_conserva_prestamo_y_permite_devolver(self):
        prestamo = self.registrar_prestamo_de_prueba()
        personas = self.servicios['personas']
        persona, version = personas.consultar_persona('20000001')
        personas.actualizar_persona(persona.dni, dict(persona.como_diccionario(), version=version, estado_matricula='NO_VIGENTE'), 2)
        with self.assertRaisesRegex(ValueError, 'matrícula'):
            self.registrar_prestamo_de_prueba([2])
        personas.desactivar_persona(persona.dni, 2)
        with self.assertRaisesRegex(ValueError, 'activa'):
            self.registrar_prestamo_de_prueba([2])
        detalle = self.consultar_detalle_por_prestamo_y_bien(prestamo, 1)
        self.assertIsNone(detalle['fecha_devolucion'])
        identificador = detalle['id_detalle']
        self.servicios['prestamos'].registrar_devolucion(prestamo, dict(detalles=[str(identificador)], **{
            f'codigo_recibido_{identificador}': 'LAP-1', f'condicion_{identificador}': 'BUENO',
        }), 2)
        self.assertIsNotNone(self.consultar_detalle_por_prestamo_y_bien(prestamo, 1)['fecha_devolucion'])

    # SEG-03

    def crear_cliente_con_cuenta_de_mysql(self, aplicacion, identificador):
        cuenta = aplicacion.extensions['servicios']['acceso'].consultar_cuenta_activa(identificador)
        return crear_cliente_con_sesion_simulada(self, aplicacion, cuenta)

    def test_rutas_rechazan_peticion_sin_permiso_o_sin_token(self):
        prestamo_lucia = self.registrar_prestamo_de_prueba()
        aplicacion = self.crear_aplicacion_de_prueba()
        diego = self.crear_cliente_con_cuenta_de_mysql(aplicacion, 4)
        self.assertEqual(diego.get(f'/prestamos/{prestamo_lucia}').status_code, 403)
        self.assertEqual(diego.get('/ampliaciones/solicitudes').status_code, 403)
        respuesta = diego.post('/bienes/2/mantenimiento/abrir', data=dict(
            csrf_token='token', tipo='PREVENTIVO', motivo='Intento sin permiso'))
        self.assertEqual(respuesta.status_code, 403)
        respuesta = diego.post(f'/prestamos/{prestamo_lucia}/detalles/'
                               f"{self.consultar_detalle_por_prestamo_y_bien(prestamo_lucia, 1)['id_detalle']}/solicitar-ampliacion",
                               data=dict(csrf_token='token', cantidad='1', unidad='DIAS', motivo='Ajeno'))
        self.assertEqual(respuesta.status_code, 403)
        encargado = self.crear_cliente_con_cuenta_de_mysql(aplicacion, 2)
        self.assertEqual(encargado.post('/bienes/2/mantenimiento/abrir', data=dict(
            csrf_token='token', tipo='PREVENTIVO', motivo='Solo administra recursos')).status_code, 403)
        self.assertEqual(encargado.post('/bienes/2/mantenimiento/abrir', data=dict(
            tipo='PREVENTIVO', motivo='Sin token')).status_code, 400)
        self.assertEqual(self.ejecutar_sql_de_prueba('SELECT COUNT(*) n FROM mantenimiento_bien')[0]['n'], 0)
        self.assertEqual(self.ejecutar_sql_de_prueba('SELECT COUNT(*) n FROM solicitud_ampliacion')[0]['n'], 0)

    # AUT-01 y AUT-02

    def test_registros_simultaneos_de_bienes_generan_identificadores_unicos(self):
        bienes = self.servicios['bienes']
        with ThreadPoolExecutor(max_workers=8) as hilos:
            resultados = list(hilos.map(lambda n: capturar_resultado_o_excepcion(
                bienes.registrar_bien_material,
                dict(id_recurso='1', codigo_inventario=f'NUEVO-{n}', numero_serie='FAB-123'), 1,
            ), range(12)))
        self.assertTrue(all(estado == 'ok' for estado, _ in resultados), resultados)
        filas = self.ejecutar_sql_de_prueba("SELECT * FROM bien_material WHERE codigo_inventario LIKE 'NUEVO-%'")
        identificadores = [f['identificador_sistema'] for f in filas]
        self.assertEqual(len(set(identificadores)), 12)
        for fila in filas:
            self.assertRegex(fila['identificador_sistema'], r'^SR-\d{4}-[2-9A-HJ-NP-Z]{6}$')
            self.assertEqual(fila['numero_serie'], 'FAB-123', 'la serie del fabricante se conserva')
            self.assertIsNotNone(fila['fecha_registro'])

    def test_editar_bien_conserva_identificador_y_rechaza_fecha_futura(self):
        bienes = self.servicios['bienes']
        nuevo = bienes.registrar_bien_material(dict(id_recurso='1', codigo_inventario='EDITAR-1'), 1)
        antes = bienes.consultar_bien_material(nuevo)
        bienes.actualizar_bien_material(nuevo, dict(version=antes['version'], ubicacion='Lab 2'), 1)
        despues = bienes.consultar_bien_material(nuevo)
        self.assertEqual(despues['identificador_sistema'], antes['identificador_sistema'])
        self.assertEqual(despues['fecha_registro'], antes['fecha_registro'])
        futura = (datetime.now(LIMA) + timedelta(days=3)).date().isoformat()
        with self.assertRaisesRegex(ValueError, 'futura'):
            bienes.registrar_bien_material(dict(id_recurso='1', codigo_inventario='FUT-1',
                                                fecha_adquisicion=futura), 1)

    # MAN-01

    def test_mantenimiento_bloquea_prestamo_hasta_su_cierre(self):
        bienes = self.servicios['bienes']
        bienes.abrir_mantenimiento(1, dict(tipo='CORRECTIVO', motivo='Teclado'), 1)
        self.assertEqual(bienes.consultar_bien_material(1)['estado'], 'MANTENIMIENTO')
        with self.assertRaises(ValueError):
            self.registrar_prestamo_de_prueba([1])
        with self.assertRaises(Conflicto):
            bienes.abrir_mantenimiento(1, dict(tipo='PREVENTIVO', motivo='Otra vez'), 1)
        with self.assertRaises(Conflicto):
            bienes.cambiar_estado_bien_material(1, dict(estado='DISPONIBLE', estado_esperado='MANTENIMIENTO',
                                                        motivo='Saltarse el cierre'), 1)
        bienes.cerrar_mantenimiento(1, dict(resultado='DISPONIBLE', observacion='Teclado cambiado'), 1)
        self.assertEqual(bienes.consultar_bien_material(1)['estado'], 'DISPONIBLE')
        registro = self.ejecutar_sql_de_prueba('SELECT * FROM mantenimiento_bien')[0]
        self.assertEqual(registro['resultado'], 'DISPONIBLE')
        self.assertIsNotNone(registro['fecha_fin_real'])
        self.assertEqual(len(bienes.consultar_historial_bien_material(1)), 2)
        self.registrar_prestamo_de_prueba([1])

    def test_aperturas_simultaneas_dejan_un_solo_mantenimiento(self):
        bienes = self.servicios['bienes']
        with ThreadPoolExecutor(max_workers=4) as hilos:
            resultados = list(hilos.map(lambda n: capturar_resultado_o_excepcion(
                bienes.abrir_mantenimiento, 2, dict(tipo='PREVENTIVO', motivo=f'Intento {n}'), 1,
            ), range(4)))
        self.assertEqual(sum(estado == 'ok' for estado, _ in resultados), 1)
        self.assertEqual(self.ejecutar_sql_de_prueba('SELECT COUNT(*) n FROM mantenimiento_bien')[0]['n'], 1)

    def test_no_abre_mantenimiento_con_prestamo_pendiente(self):
        self.registrar_prestamo_de_prueba([3])
        with self.assertRaises(Conflicto):
            self.servicios['bienes'].abrir_mantenimiento(3, dict(tipo='PREVENTIVO', motivo='x'), 1)
        with self.assertRaises(ValueError):
            self.servicios['bienes'].cambiar_estado_bien_material(1, dict(
                estado='MANTENIMIENTO', estado_esperado='DISPONIBLE', motivo='Por atajo'), 1)

    # AMP-01

    def test_solicitud_de_ampliacion_se_aprueba_una_sola_vez(self):
        ampliaciones = self.servicios['ampliaciones']
        prestamo = self.registrar_prestamo_de_prueba([1])
        detalle = self.consultar_detalle_por_prestamo_y_bien(prestamo, 1)
        limite = detalle['fecha_limite_devolucion']
        with self.assertRaises(PermissionError):
            ampliaciones.solicitar_ampliacion(prestamo, detalle['id_detalle'],
                                              dict(cantidad='1', unidad='DIAS', motivo='Ajena'), 4)
        primera = ampliaciones.solicitar_ampliacion(prestamo, detalle['id_detalle'],
                                                    dict(cantidad='1', unidad='DIAS', motivo='Proyecto'), 3)
        with self.assertRaises(Conflicto):
            ampliaciones.solicitar_ampliacion(prestamo, detalle['id_detalle'],
                                              dict(cantidad='1', unidad='DIAS', motivo='Duplicada'), 3)
        ampliaciones.rechazar_solicitud_ampliacion(primera, dict(observacion='Hay reserva'), 2)
        self.assertEqual(self.consultar_detalle_por_prestamo_y_bien(prestamo, 1)['fecha_limite_devolucion'], limite)
        segunda = ampliaciones.solicitar_ampliacion(prestamo, detalle['id_detalle'],
                                                    dict(cantidad='1', unidad='DIAS', motivo='Sustentación'), 3)
        with ThreadPoolExecutor(max_workers=2) as hilos:
            resultados = list(hilos.map(lambda _: capturar_resultado_o_excepcion(
                ampliaciones.aprobar_solicitud_ampliacion, segunda, {}, 2), range(2)))
        self.assertEqual(sum(estado == 'ok' for estado, _ in resultados), 1)
        self.assertEqual(self.consultar_detalle_por_prestamo_y_bien(prestamo, 1)['fecha_limite_devolucion'], limite + timedelta(days=1))
        fila = self.ejecutar_sql_de_prueba('SELECT * FROM solicitud_ampliacion WHERE id_solicitud=%s', (segunda,))[0]
        self.assertEqual((fila['estado'], fila['dni_resolucion']), ('APROBADA', '10000002'))
        self.assertEqual(fila['fecha_limite_anterior'], limite)

    def test_no_aprueba_ampliacion_de_bien_ya_devuelto(self):
        ampliaciones = self.servicios['ampliaciones']
        prestamo = self.registrar_prestamo_de_prueba([2])
        detalle = self.consultar_detalle_por_prestamo_y_bien(prestamo, 2)
        solicitud = ampliaciones.solicitar_ampliacion(prestamo, detalle['id_detalle'],
                                                      dict(cantidad='1', unidad='DIAS', motivo='Tesis'), 3)
        self.servicios['prestamos'].registrar_devolucion(prestamo, dict(
            detalles=[str(detalle['id_detalle'])], **{f"condicion_{detalle['id_detalle']}": 'BUENO',
                                                      f"codigo_recibido_{detalle['id_detalle']}": 'LAP-2'}), 2)
        with self.assertRaisesRegex(Conflicto, 'Rechaza'):
            ampliaciones.aprobar_solicitud_ampliacion(solicitud, {}, 2)
        self.assertEqual(self.ejecutar_sql_de_prueba('SELECT estado FROM solicitud_ampliacion')[0]['estado'], 'PENDIENTE')

    def test_historial_de_ampliaciones_muestra_solo_el_bien_afectado(self):
        ampliaciones = self.servicios['ampliaciones']
        reportes = self.servicios['reportes']
        prestamo = self.registrar_prestamo_de_prueba([1, 2, 3])
        directa, solicitada = (self.consultar_detalle_por_prestamo_y_bien(prestamo, bien) for bien in (1, 2))
        datos = dict(cantidad='1', unidad='DIAS', motivo='Proyecto')
        limite_directo = directa['fecha_limite_devolucion']
        nueva_fecha = ampliaciones.ampliar_prestamo(
            prestamo, directa['id_detalle'], dict(datos, fecha_actual=limite_directo.isoformat()), 2,
        )
        solicitud = ampliaciones.solicitar_ampliacion(prestamo, solicitada['id_detalle'], datos, 3)
        nueva_solicitada = ampliaciones.aprobar_solicitud_ampliacion(solicitud, {}, 2)

        movimientos = self.ejecutar_sql_de_prueba('''SELECT id_historial_estado,datos FROM historial_estado
            WHERE entidad='PRESTAMO' AND id_entidad=%s AND datos->>'$.evento'='AMPLIACION_PLAZO'
            ORDER BY id_historial_estado''', (prestamo,))
        self.assertEqual([json.loads(h['datos']) for h in movimientos], [
            dict(evento='AMPLIACION_PLAZO', id_detalle=directa['id_detalle'],
                 fecha_limite_anterior=limite_directo.isoformat(), fecha_limite_nueva=nueva_fecha.isoformat()),
            dict(evento='AMPLIACION_PLAZO', id_detalle=solicitada['id_detalle'], id_solicitud=solicitud,
                 fecha_limite_anterior=solicitada['fecha_limite_devolucion'].isoformat(),
                 fecha_limite_nueva=nueva_solicitada.isoformat()),
        ])

        def ampliaciones_del_bien(codigo):
            historial = reportes.consultar_reporte_filtrado(dict(tipo='historial_bien', codigo_inventario=codigo))
            return [(fila['codigo_inventario'], fila['referencia']) for fila in historial['filas']
                    if fila['evento'] == 'Ampliación de plazo']

        for formato in ('actual', 'historico'):
            with self.subTest(formato=formato):
                for codigo, detalle in (('LAP-1', directa), ('LAP-2', solicitada)):
                    self.assertEqual(ampliaciones_del_bien(codigo), [
                        (codigo, f'Préstamo #{prestamo} / detalle #{detalle["id_detalle"]}'),
                    ])
                self.assertEqual(ampliaciones_del_bien('LAP-3'), [])
            if formato == 'actual':
                self.ejecutar_sql_de_prueba('UPDATE historial_estado SET datos=NULL WHERE id_historial_estado IN (%s,%s)',
                             tuple(h['id_historial_estado'] for h in movimientos))

    def test_rechaza_solicitud_de_ampliacion_que_supera_la_politica(self):
        prestamo = self.registrar_prestamo_de_prueba([1])
        detalle = self.consultar_detalle_por_prestamo_y_bien(prestamo, 1)
        with self.assertRaises(ValueError):
            self.servicios['ampliaciones'].solicitar_ampliacion(
                prestamo, detalle['id_detalle'], dict(cantidad='10', unidad='DIAS', motivo='Mucho'), 3)
        self.assertEqual(self.ejecutar_sql_de_prueba('SELECT COUNT(*) n FROM solicitud_ampliacion')[0]['n'], 0)

    # PRU-01 y PRU-03

    def test_devolucion_parcial_rechaza_repetir_el_mismo_bien(self):
        prestamos = self.servicios['prestamos']
        prestamo = self.registrar_prestamo_de_prueba([1, 2])
        detalle = self.consultar_detalle_por_prestamo_y_bien(prestamo, 1)['id_detalle']
        datos = dict(detalles=[str(detalle)], **{f'condicion_{detalle}': 'BUENO', f'codigo_recibido_{detalle}': 'LAP-1'})
        prestamos.registrar_devolucion(prestamo, datos, 2)
        estado = self.ejecutar_sql_de_prueba('SELECT estado FROM prestamo WHERE id_prestamo=%s', (prestamo,))[0]['estado']
        self.assertEqual(estado, 'PARCIALMENTE_DEVUELTO')
        self.assertIsNone(self.consultar_detalle_por_prestamo_y_bien(prestamo, 2)['fecha_devolucion'])
        primera = self.consultar_detalle_por_prestamo_y_bien(prestamo, 1)['fecha_devolucion']
        with self.assertRaises(ValueError):
            prestamos.registrar_devolucion(prestamo, datos, 2)
        self.assertEqual(self.consultar_detalle_por_prestamo_y_bien(prestamo, 1)['fecha_devolucion'], primera)
        bienes = {f['id_bien']: f['estado'] for f in self.ejecutar_sql_de_prueba('SELECT id_bien,estado FROM bien_material')}
        self.assertEqual((bienes[1], bienes[2]), ('DISPONIBLE', 'PRESTADO'))

    def test_dos_prestamos_simultaneos_del_mismo_bien(self):
        with ThreadPoolExecutor(max_workers=2) as hilos:
            resultados = list(hilos.map(lambda persona: capturar_resultado_o_excepcion(self.registrar_prestamo_de_prueba, [3], persona),
                                        ('20000001', '20000002')))
        self.assertEqual(sum(estado == 'ok' for estado, _ in resultados), 1, resultados)
        self.assertEqual(self.ejecutar_sql_de_prueba('SELECT COUNT(*) n FROM detalle_prestamo WHERE id_bien=3')[0]['n'], 1)

    def _preparar_prueba_cupo_grupal(self):
        self.ejecutar_sql_de_prueba("INSERT INTO persona(dni,nombres,apellidos) VALUES('20000003','Rosa','Prueba')")
        self.ejecutar_sql_de_prueba("INSERT INTO estudiante(dni,cui) VALUES('20000003','20000003')")
        self.ejecutar_sql_de_prueba("INSERT INTO bien_material(id_bien,id_recurso,codigo_inventario) VALUES(4,1,'LAP-4')")

    def test_integrante_acumula_cupo_entre_grupos_y_libera_al_devolver(self):
        self._preparar_prueba_cupo_grupal()
        prestamos = self.servicios['prestamos']
        integrante = '20000002'
        primero = self.registrar_prestamo_de_prueba([1, 2], '20000001', [integrante])
        self.assertEqual(prestamos.consultar_condiciones_prestamo('20000001')['pendientes'], 2)
        self.registrar_prestamo_de_prueba([3], '20000003', [integrante])
        self.assertEqual(prestamos.consultar_condiciones_prestamo(integrante)['pendientes'], 3)
        with self.assertRaisesRegex(Conflicto, 'Diego Prueba tiene 3 bienes pendientes'):
            self.registrar_prestamo_de_prueba([4], '20000003', [integrante])
        with self.assertRaises(Conflicto):
            self.registrar_prestamo_de_prueba([4], integrante)

        detalle = self.consultar_detalle_por_prestamo_y_bien(primero, 1)['id_detalle']
        prestamos.registrar_devolucion(primero, dict(detalles=[str(detalle)], **{
            f'condicion_{detalle}': 'BUENO', f'codigo_recibido_{detalle}': 'LAP-1'}), 2)
        self.assertEqual(prestamos.consultar_condiciones_prestamo('20000001')['pendientes'], 1)
        self.assertEqual(prestamos.consultar_condiciones_prestamo(integrante)['pendientes'], 2)
        self.assertTrue(self.registrar_prestamo_de_prueba([4], integrante))

    def test_entregas_simultaneas_comparten_el_cupo_del_integrante(self):
        self._preparar_prueba_cupo_grupal()
        integrante = '20000002'
        self.registrar_prestamo_de_prueba([1, 2], '20000001', [integrante])
        inicio = Barrier(2)

        def registrar_prestamo_grupal_en_simultaneo(datos):
            bien, responsable, actor = datos
            inicio.wait(timeout=5)
            return capturar_resultado_o_excepcion(self.registrar_prestamo_de_prueba, [bien], responsable, [integrante], actor)

        with ThreadPoolExecutor(max_workers=2) as hilos:
            resultados = list(hilos.map(registrar_prestamo_grupal_en_simultaneo, ((3, '20000001', 1), (4, '20000003', 2))))
        self.assertEqual(sum(estado == 'ok' for estado, _ in resultados), 1, resultados)
        bloqueado = next(resultado for estado, resultado in resultados if estado == 'error')
        self.assertIsInstance(bloqueado, Conflicto)
        self.assertIn('Diego Prueba', str(bloqueado))

    def test_cupo_compartido_prioridad_y_entrega_de_la_reserva(self):
        reservas = self.servicios['reservas']
        self.ejecutar_sql_de_prueba("UPDATE limite_articulos_prestamo SET maximo_articulos=1 WHERE tipo_persona='ESTUDIANTE'")
        self.ejecutar_sql_de_prueba("INSERT INTO recurso(id_recurso,id_categoria,nombre) VALUES(2,1,'Tablet')")
        manana = (datetime.now(LIMA).date() + timedelta(days=1)).isoformat()
        datos = dict(id_recurso=1, fecha_requerida=f'{manana}T10:00', acepta_condiciones='1')
        reserva = reservas.registrar_reserva(datos, 3)
        with self.assertRaisesRegex(Conflicto, 'reservas activas'):
            reservas.registrar_reserva(dict(datos, id_recurso=2), 3)
        with self.assertRaisesRegex(Conflicto, 'reservas activas'):
            self.registrar_prestamo_de_prueba([1])
        with self.assertRaisesRegex(Conflicto, 'después de su plazo'):
            reservas.expirar_reserva(reserva, {'motivo': 'Todavía en plazo'}, 2)
        self.ejecutar_sql_de_prueba('UPDATE reserva SET fecha_requerida=UTC_TIMESTAMP()-INTERVAL 1 SECOND WHERE id_reserva=%s', (reserva,))
        self.ejecutar_sql_de_prueba("UPDATE bien_material SET estado='MANTENIMIENTO' WHERE id_bien IN (2,3)")
        with self.assertRaisesRegex(Conflicto, 'Atiende primero'):
            self.registrar_prestamo_de_prueba([1], '20000002')
        reservas.preparar_reserva(reserva, {}, 2)
        prestamo = reservas.entregar_reserva(reserva, {'acepta_condiciones': '1'}, 2)
        self.assertEqual(reservas.consultar_reserva(reserva, '20000001')['estado'], 'ATENDIDA')
        self.assertIsNotNone(self.consultar_detalle_por_prestamo_y_bien(prestamo, 1))

    def test_ampliacion_unica_y_reserva_sin_ejemplar(self):
        ampliaciones = self.servicios['ampliaciones']
        prestamo = self.registrar_prestamo_de_prueba([1, 2, 3])
        detalle = self.consultar_detalle_por_prestamo_y_bien(prestamo, 1)
        datos = dict(cantidad=1, unidad='DIAS', fecha_actual=detalle['fecha_limite_devolucion'].isoformat())
        manana = (datetime.now(LIMA).date() + timedelta(days=1)).isoformat()
        reservas = self.servicios['reservas']
        reserva = reservas.registrar_reserva(dict(id_recurso=1, fecha_requerida=f'{manana}T10:00', acepta_condiciones='1'), 4)
        with self.assertRaisesRegex(Conflicto, 'reservas vigentes'):
            ampliaciones.ampliar_prestamo(prestamo, detalle['id_detalle'], datos, 2)
        reservas.cancelar_reserva(reserva, {}, 4)
        nuevo = ampliaciones.ampliar_prestamo(prestamo, detalle['id_detalle'], datos, 2)
        with self.assertRaisesRegex(Conflicto, 'única ampliación'):
            ampliaciones.ampliar_prestamo(prestamo, detalle['id_detalle'], dict(datos, fecha_actual=nuevo.isoformat()), 2)

    def test_operacion_propia_necesita_autorizacion_distinta_para_cada_accion(self):
        self.ejecutar_sql_de_prueba("INSERT INTO estudiante(dni,cui) VALUES('10000002','10000002')")
        servicio = self.servicios['prestamos']
        with self.assertRaisesRegex(Conflicto, 'otro administrador'):
            self.registrar_prestamo_de_prueba([1], '10000002')
        permiso = servicio.autorizar_operacion_propia(dict(dni_operador='10000002', accion='ENTREGA', motivo='Préstamo autorizado del ejemplar LAP-1.'), 1)
        prestamo = self.registrar_prestamo_de_prueba([1], '10000002', autorizacion=permiso)
        with self.assertRaisesRegex(Conflicto, 'ya se usó'):
            self.registrar_prestamo_de_prueba([2], '10000002', autorizacion=permiso)
        detalle = self.consultar_detalle_por_prestamo_y_bien(prestamo, 1)['id_detalle']
        datos = dict(detalles=[str(detalle)], **{f'condicion_{detalle}': 'BUENO', f'codigo_recibido_{detalle}': 'LAP-1'})
        with self.assertRaisesRegex(Conflicto, 'no corresponde'):
            servicio.registrar_devolucion(prestamo, dict(datos, autorizacion=permiso), 2)
        recepcion = servicio.autorizar_operacion_propia(dict(dni_operador='10000002', accion='DEVOLUCION', id_prestamo=prestamo, motivo='Recepción autorizada del ejemplar LAP-1.'), 1)
        servicio.registrar_devolucion(prestamo, dict(datos, autorizacion=recepcion), 2)
        self.assertIsNotNone(self.consultar_detalle_por_prestamo_y_bien(prestamo, 1)['fecha_devolucion'])
        registro = self.ejecutar_sql_de_prueba('''SELECT estado_nuevo,dni_objetivo,dni_responsable,
            datos->>'$.id_prestamo_uso' AS prestamo FROM historial_estado WHERE id_historial_estado=%s''',
            (recepcion,))[0]
        self.assertEqual(registro, dict(estado_nuevo='UTILIZADA',dni_objetivo='10000002',
                                       dni_responsable='10000001',prestamo=str(prestamo)))

    def test_cambio_tipo_persona_conserva_cuenta_prestamo_y_motivo(self):
        prestamo = self.registrar_prestamo_de_prueba()
        servicio = self.servicios['personas']
        persona, version = servicio.consultar_persona('20000001')
        datos = dict(persona.como_diccionario(), version=version, tipo='DOCENTE', correo='lucia@unsa.edu.pe',
                     codigo_docente='DOC-001', departamento_academico='Informática',
                     facultad='Ingeniería', escuela_profesional='Computación', motivo_cambio_tipo='Nombramiento')
        servicio.actualizar_persona(persona.dni, datos, 1)
        nueva, _ = servicio.consultar_persona(persona.dni)
        self.assertEqual(nueva.tipo, 'DOCENTE')
        self.assertEqual(servicio.consultar_cambios_tipo_persona(persona.dni)[0]['motivo'], 'Nombramiento')
        historial = self.ejecutar_sql_de_prueba('''SELECT datos->>'$.datos_institucionales.cui' AS cui
            FROM historial_estado WHERE entidad='TIPO_PERSONA' AND dni_objetivo=%s''', (persona.dni,))[0]
        self.assertEqual(historial['cui'], '20000001')
        self.assertEqual(self.ejecutar_sql_de_prueba('SELECT dni_persona FROM usuario_sistema WHERE id_usuario=3')[0]['dni_persona'], persona.dni)
        self.assertEqual(self.consultar_detalle_por_prestamo_y_bien(prestamo, 1)['id_politica'], 1)

    def test_codigo_devolucion_y_rectificacion_administrativa(self):
        servicio = self.servicios['prestamos']
        prestamo = self.registrar_prestamo_de_prueba()
        detalle = self.consultar_detalle_por_prestamo_y_bien(prestamo, 1)['id_detalle']
        datos = dict(detalles=[str(detalle)], **{f'condicion_{detalle}': 'BUENO'})
        with self.assertRaisesRegex(Conflicto, 'no coincide'):
            servicio.registrar_devolucion(prestamo, dict(datos, **{f'codigo_recibido_{detalle}': 'LAP-2'}), 2)
        servicio.registrar_discrepancia_devolucion(prestamo, detalle, 'Se presentó LAP-2.', 2)
        self.assertIsNone(self.consultar_detalle_por_prestamo_y_bien(prestamo, 1)['fecha_devolucion'])
        servicio.registrar_devolucion(prestamo, dict(datos, **{f'codigo_recibido_{detalle}': 'LAP-1'}), 2)
        with self.assertRaises(PermissionError):
            servicio.rectificar_devolucion(prestamo, detalle, 'Registro accidental', 2)
        servicio.rectificar_devolucion(prestamo, detalle, 'Registro accidental', 1)
        self.assertIsNone(self.consultar_detalle_por_prestamo_y_bien(prestamo, 1)['fecha_devolucion'])
        self.assertEqual(self.ejecutar_sql_de_prueba('SELECT estado FROM bien_material WHERE id_bien=1')[0]['estado'], 'PRESTADO')
        registro = self.ejecutar_sql_de_prueba('''SELECT dni_objetivo,datos->>'$.condicion_original' AS condicion,
            datos->>'$.fecha_devolucion_original' AS fecha FROM historial_estado
            WHERE entidad='RECTIFICACION_DEVOLUCION' AND id_entidad=%s''', (detalle,))[0]
        self.assertEqual((registro['dni_objetivo'], registro['condicion']), ('10000002', 'BUENO'))
        self.assertIsNotNone(registro['fecha'])

    # OPE-01

    def test_revision_excluye_segundo_procesador_y_registra_el_resultado(self):
        repositorio = RepositorioProcesadorSQL(self.conexion)
        with repositorio.bloqueo_exclusivo() as primero:
            with RepositorioProcesadorSQL(self.conexion).bloqueo_exclusivo() as segundo:
                self.assertTrue(primero)
                self.assertFalse(segundo)
        procesador = ServicioAplicacionProcesador(repositorio)
        self.assertTrue(procesador.consultar_estado_procesador()['alerta'], 'nunca se ejecutó')
        self.assertEqual(procesador.ejecutar_revision_de_vencimientos([lambda: None]), 'ok')
        self.assertFalse(procesador.consultar_estado_procesador()['alerta'])

        def simular_revision_con_base_caida():
            raise RuntimeError('base caída')

        self.assertEqual(procesador.ejecutar_revision_de_vencimientos([simular_revision_con_base_caida]), 'error')
        estado = procesador.consultar_estado_procesador()
        self.assertIn('base caída', estado['ultimo_error'])
        self.assertEqual(estado['fallos_consecutivos'], 1)
        self.ejecutar_sql_de_prueba('''UPDATE estado_procesador
            SET ultima_ejecucion_correcta=UTC_TIMESTAMP()-INTERVAL 6 MINUTE''')
        self.assertTrue(procesador.consultar_estado_procesador()['alerta'])

    def test_procesador_ejecuta_revision_de_sanciones_y_reservas(self):
        procesador = ServicioAplicacionProcesador(RepositorioProcesadorSQL(self.conexion))
        resultado = procesador.ejecutar_revision_de_vencimientos([
            self.servicios['sanciones'].procesar_sanciones_por_vencimiento,
            self.servicios['reservas'].expirar_reservas_vencidas,
        ])
        self.assertEqual(resultado, 'ok')

    def test_reinicio_y_segundo_procesador_respetan_intervalo_de_revision(self):
        primero = ServicioAplicacionProcesador(RepositorioProcesadorSQL(self.conexion))
        segundo = ServicioAplicacionProcesador(RepositorioProcesadorSQL(self.conexion))
        revisiones = []
        operaciones = [lambda: revisiones.append('revisado')]
        periodo = timedelta(seconds=30)
        self.assertEqual(primero.ejecutar_revision_de_vencimientos(operaciones, intervalo_minimo=periodo), 'ok')
        self.assertEqual(segundo.ejecutar_revision_de_vencimientos(operaciones, intervalo_minimo=periodo), 'omitida')
        self.ejecutar_sql_de_prueba('UPDATE estado_procesador SET ultima_ejecucion_correcta=UTC_TIMESTAMP()-INTERVAL 31 SECOND')
        self.assertEqual(segundo.ejecutar_revision_de_vencimientos(operaciones, intervalo_minimo=periodo), 'ok')
        self.assertEqual(revisiones, ['revisado', 'revisado'])

if __name__ == '__main__':
    unittest.main()
