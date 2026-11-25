"""Integración con MySQL del cierre de pendientes del informe.

Cubre SEG-01, SEG-02, SEG-03, AUT-01, AUT-02, MAN-01, AMP-01, OPE-01, MIG-01 y casos de
PRU-01 y PRU-03. Usa la misma base exclusiva de pruebas que test_sanciones_mysql:
requiere TEST_MYSQL_PORT (y TEST_MYSQL_PASSWORD si corresponde); cada caso crea y borra
su propia base, nunca la de la aplicación.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import re
from threading import Barrier
import unittest
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from app import create_app, crear_servicios
from arranque.esquema_cierre import migrar_esquema_cierre
from dominio.compartido.validacion import LIMA, Conflicto
from repositorio.control.repositorio_procesador_sql import RepositorioProcesadorSQL
from servicios.control.servicio_procesador import ServicioAplicacionProcesador
from tests.integracion.test_sanciones_mysql import BaseMySQLTest
from tests.soporte_roles import cliente_autenticado

CLAVE = 'ClavePrueba2026!'


def intentar(funcion, *args):
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

    def prestar(self, bienes=(1,), persona='20000001', participantes=(), actor=2, autorizacion=None):
        return self.servicios['prestamos'].registrar_prestamo(dict(
            dni_persona=persona, bienes=[str(b) for b in bienes], acepta_condiciones='1',
            tipo_prestamo='GRUPAL' if participantes else 'INDIVIDUAL', participantes=participantes,
            autorizacion=autorizacion,
        ), actor)

    def detalle(self, prestamo, bien):
        return self.consulta('SELECT * FROM detalle_prestamo WHERE id_prestamo=%s AND id_bien=%s',
                             (prestamo, bien))[0]

    def app(self):
        with patch('app.clave_local', return_value='pruebas-cierre'):
            return create_app(dict(TESTING=True, MYSQL_CONFIG=self.config))

    def iniciar_sesion(self, aplicacion, usuario, clave=CLAVE, origen='10.0.0.1'):
        cliente = aplicacion.test_client()
        with cliente.session_transaction() as sesion:
            sesion['csrf'] = 'token'
        respuesta = cliente.post('/login', data=dict(csrf_token='token', usuario=usuario, clave=clave),
                                 environ_base={'REMOTE_ADDR': origen})
        return cliente, respuesta

    # SEG-01

    def test_seg01_limite_de_intentos_por_cuenta(self):
        aplicacion = self.app()
        for _ in range(5):
            _, respuesta = self.iniciar_sesion(aplicacion, 'lucia', 'incorrecta')
            self.assertEqual(respuesta.status_code, 401)
        _, respuesta = self.iniciar_sesion(aplicacion, 'lucia')
        self.assertEqual(respuesta.status_code, 429, 'la clave correcta también espera el bloqueo')
        self.assertIn('Demasiados intentos', respuesta.get_data(as_text=True))
        _, respuesta = self.iniciar_sesion(aplicacion, 'diego')
        self.assertEqual(respuesta.status_code, 302, 'otra cuenta del mismo origen sigue entrando')

    def test_seg01_cuenta_inexistente_recibe_el_mismo_trato(self):
        aplicacion = self.app()
        for _ in range(5):
            self.iniciar_sesion(aplicacion, 'no-existe', 'x', origen='10.0.0.9')
        _, respuesta = self.iniciar_sesion(aplicacion, 'no-existe', 'x', origen='10.0.0.9')
        self.assertEqual(respuesta.status_code, 429)

    # SEG-02

    def test_seg02_cerrar_sesion_invalida_la_cookie_copiada(self):
        aplicacion = self.app()
        cliente, respuesta = self.iniciar_sesion(aplicacion, 'lucia')
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
        self.assertEqual(self.consulta('SELECT COUNT(*) n FROM sesion_usuario WHERE fecha_cierre IS NULL')[0]['n'], 0)

    def test_seg02_inactividad_y_duracion_maxima(self):
        acceso = self.servicios['acceso']
        token = acceso.iniciar_sesion(3)
        self.assertTrue(acceso.validar_sesion(token, 3))
        self.assertFalse(acceso.validar_sesion(token, 4), 'el token pertenece a otra cuenta')
        self.consulta('UPDATE sesion_usuario SET ultima_actividad=UTC_TIMESTAMP()-INTERVAL 31 MINUTE')
        self.assertFalse(acceso.validar_sesion(token, 3))
        self.assertIsNotNone(self.consulta('SELECT fecha_cierre FROM sesion_usuario')[0]['fecha_cierre'])
        otra = acceso.iniciar_sesion(3)
        self.consulta('''UPDATE sesion_usuario SET fecha_inicio=UTC_TIMESTAMP()-INTERVAL 9 HOUR
            WHERE fecha_cierre IS NULL''')
        self.assertFalse(acceso.validar_sesion(otra, 3))

    def test_seg02_desactivar_cuenta_expulsa_de_inmediato(self):
        aplicacion = self.app()
        cliente, _ = self.iniciar_sesion(aplicacion, 'lucia')
        self.assertEqual(cliente.get('/').status_code, 200)
        self.consulta("UPDATE usuario_sistema SET estado_cuenta='INACTIVA' WHERE id_usuario=3")
        self.assertEqual(cliente.get('/').status_code, 302)

    def test_restablecer_acceso_auditado_con_codigo_de_un_solo_uso(self):
        app = self.app()
        cliente, _ = self.iniciar_sesion(app, 'lucia')
        admin, _ = self.iniciar_sesion(app, 'admin')
        encargado, _ = self.iniciar_sesion(app, 'encargado')
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
        self.assertEqual(self.iniciar_sesion(app, 'lucia', codigo)[1].status_code, 401)
        self.assertEqual(self.iniciar_sesion(app, 'lucia')[1].status_code, 401)
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
        self.assertEqual(self.iniciar_sesion(app, 'lucia', clave)[1].location, '/')
        filas = self.consulta("SELECT observacion,dni_responsable FROM historial_estado WHERE entidad='CUENTA' AND estado_nuevo='RESTABLECIDA'")
        self.assertEqual(filas, [dict(observacion='Solicitud verificada', dni_responsable='10000001')])

    def test_cambios_simultaneos_conservan_un_administrador_activo(self):
        self.consulta("UPDATE usuario_sistema SET rol='ADMINISTRADOR',debe_cambiar_clave=FALSE WHERE id_usuario=2")
        cuentas = self.servicios['cuentas']
        barrera = Barrier(2)

        def desactivar(par):
            documento, actor = par
            datos = dict(version=cuentas.consultar_cuenta(documento)['version'], estado_cuenta='INACTIVA')
            barrera.wait(timeout=10)
            return intentar(cuentas.actualizar_cuenta, documento, datos, actor)

        with ThreadPoolExecutor(max_workers=2) as hilos:
            resultados = list(hilos.map(desactivar, [('10000001', 2), ('10000002', 1)]))
        self.assertEqual(sum(estado == 'ok' for estado, _ in resultados), 1)
        self.assertIsInstance(next(error for estado, error in resultados if estado == 'error'), PermissionError)
        self.assertEqual(self.consulta("SELECT COUNT(*) n FROM usuario_sistema WHERE rol='ADMINISTRADOR' AND estado_cuenta='ACTIVA'")[0]['n'], 1)

    def test_alta_de_cuentas_elige_correo_cui_o_nombre_manual(self):
        for documento, correo in [('30000001', 'lucia@unsa.edu.pe'), ('30000002', None), ('30000003', None)]:
            self.consulta("INSERT INTO persona(dni,nombres,apellidos,correo) VALUES(%s,'Persona','Prueba',%s)",
                          (documento, correo))
        self.consulta("INSERT INTO estudiante(dni,cui) VALUES('30000002','20267777')")
        cuentas = self.servicios['cuentas']
        self.assertEqual(cuentas.consultar_propuesta_cuenta('30000001')['nombre_usuario'], 'lucia2')
        self.assertEqual(cuentas.consultar_propuesta_cuenta('30000002')['nombre_usuario'], '20267777')
        self.assertTrue(cuentas.consultar_propuesta_cuenta('30000003')['requiere_nombre'])
        with self.assertRaises(Conflicto):
            cuentas.registrar_cuenta('30000003', 'lucia', 1)
        alta = cuentas.registrar_cuenta('30000003', 'invitada', 1)
        self.consulta("""UPDATE usuario_sistema
            SET contrasena_hash=CONCAT('activacion$1$',SUBSTRING_INDEX(contrasena_hash,'$',-1))
            WHERE id_usuario=%s""", (alta.id_usuario,))
        with self.assertRaisesRegex(ValueError, 'venció'):
            cuentas.activar_cuenta('invitada', alta.codigo_activacion, CLAVE, CLAVE)

    def test_cambiar_rol_dos_veces_no_reabre_sesion_anterior(self):
        cliente, _ = self.iniciar_sesion(self.app(), 'lucia')
        cuentas = self.servicios['cuentas']
        for rol in ('ENCARGADO_PRESTAMOS', 'USUARIO'):
            version = cuentas.consultar_cuenta('20000001')['version']
            cuentas.actualizar_cuenta('20000001', dict(version=version, rol=rol), 1)
        self.assertEqual(cliente.get('/').location, '/login')

    def test_perder_habilitacion_conserva_prestamo_y_permite_devolver(self):
        prestamo = self.prestar()
        personas = self.servicios['personas']
        persona, version = personas.consultar_persona('20000001')
        personas.actualizar_persona(persona.dni, dict(persona.datos(), version=version, estado_matricula='NO_VIGENTE'), 2)
        with self.assertRaisesRegex(ValueError, 'matrícula'):
            self.prestar([2])
        personas.desactivar_persona(persona.dni, 2)
        with self.assertRaisesRegex(ValueError, 'activa'):
            self.prestar([2])
        detalle = self.detalle(prestamo, 1)
        self.assertIsNone(detalle['fecha_devolucion'])
        identificador = detalle['id_detalle']
        self.servicios['prestamos'].registrar_devolucion(prestamo, dict(detalles=[str(identificador)], **{
            f'codigo_recibido_{identificador}': 'LAP-1', f'condicion_{identificador}': 'BUENO',
        }), 2)
        self.assertIsNotNone(self.detalle(prestamo, 1)['fecha_devolucion'])

    # SEG-03

    def cliente_real(self, aplicacion, identificador):
        cuenta = aplicacion.extensions['servicios']['acceso'].consultar_cuenta_activa(identificador)
        return cliente_autenticado(self, aplicacion, cuenta)

    def test_seg03_permisos_en_el_servidor(self):
        prestamo_lucia = self.prestar()
        aplicacion = self.app()
        diego = self.cliente_real(aplicacion, 4)
        self.assertEqual(diego.get(f'/prestamos/{prestamo_lucia}').status_code, 403)
        self.assertEqual(diego.get('/ampliaciones/solicitudes').status_code, 403)
        respuesta = diego.post('/bienes/2/mantenimiento/abrir', data=dict(
            csrf_token='token', tipo='PREVENTIVO', motivo='Intento sin permiso'))
        self.assertEqual(respuesta.status_code, 403)
        respuesta = diego.post(f'/prestamos/{prestamo_lucia}/detalles/'
                               f"{self.detalle(prestamo_lucia, 1)['id_detalle']}/solicitar-ampliacion",
                               data=dict(csrf_token='token', cantidad='1', unidad='DIAS', motivo='Ajeno'))
        self.assertEqual(respuesta.status_code, 403)
        encargado = self.cliente_real(aplicacion, 2)
        self.assertEqual(encargado.post('/bienes/2/mantenimiento/abrir', data=dict(
            csrf_token='token', tipo='PREVENTIVO', motivo='Solo administra recursos')).status_code, 403)
        self.assertEqual(encargado.post('/bienes/2/mantenimiento/abrir', data=dict(
            tipo='PREVENTIVO', motivo='Sin token')).status_code, 400)
        self.assertEqual(self.consulta('SELECT COUNT(*) n FROM mantenimiento_bien')[0]['n'], 0)
        self.assertEqual(self.consulta('SELECT COUNT(*) n FROM solicitud_ampliacion')[0]['n'], 0)

    # AUT-01 y AUT-02

    def test_aut01_identificadores_unicos_en_registros_simultaneos(self):
        bienes = self.servicios['bienes']
        with ThreadPoolExecutor(max_workers=8) as hilos:
            resultados = list(hilos.map(lambda n: intentar(
                bienes.registrar_bien_material,
                dict(id_recurso='1', codigo_inventario=f'NUEVO-{n}', numero_serie='FAB-123'), 1,
            ), range(12)))
        self.assertTrue(all(estado == 'ok' for estado, _ in resultados), resultados)
        filas = self.consulta("SELECT * FROM bien_material WHERE codigo_inventario LIKE 'NUEVO-%'")
        identificadores = [f['identificador_sistema'] for f in filas]
        self.assertEqual(len(set(identificadores)), 12)
        for fila in filas:
            self.assertRegex(fila['identificador_sistema'], r'^SR-\d{4}-[2-9A-HJ-NP-Z]{6}$')
            self.assertEqual(fila['numero_serie'], 'FAB-123', 'la serie del fabricante se conserva')
            self.assertIsNotNone(fila['fecha_registro'])

    def test_aut02_edicion_no_cambia_identificador_ni_acepta_fecha_futura(self):
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

    def test_man01_ciclo_completo_y_bloqueo_de_prestamo(self):
        bienes = self.servicios['bienes']
        bienes.abrir_mantenimiento(1, dict(tipo='CORRECTIVO', motivo='Teclado'), 1)
        self.assertEqual(bienes.consultar_bien_material(1)['estado'], 'MANTENIMIENTO')
        with self.assertRaises(ValueError):
            self.prestar([1])
        with self.assertRaises(Conflicto):
            bienes.abrir_mantenimiento(1, dict(tipo='PREVENTIVO', motivo='Otra vez'), 1)
        with self.assertRaises(Conflicto):
            bienes.cambiar_estado_bien_material(1, dict(estado='DISPONIBLE', estado_esperado='MANTENIMIENTO',
                                                        motivo='Saltarse el cierre'), 1)
        bienes.cerrar_mantenimiento(1, dict(resultado='DISPONIBLE', observacion='Teclado cambiado'), 1)
        self.assertEqual(bienes.consultar_bien_material(1)['estado'], 'DISPONIBLE')
        registro = self.consulta('SELECT * FROM mantenimiento_bien')[0]
        self.assertEqual(registro['resultado'], 'DISPONIBLE')
        self.assertIsNotNone(registro['fecha_fin_real'])
        self.assertEqual(len(bienes.consultar_historial_bien_material(1)), 2)
        self.prestar([1])

    def test_man01_aperturas_simultaneas_dejan_un_solo_registro(self):
        bienes = self.servicios['bienes']
        with ThreadPoolExecutor(max_workers=4) as hilos:
            resultados = list(hilos.map(lambda n: intentar(
                bienes.abrir_mantenimiento, 2, dict(tipo='PREVENTIVO', motivo=f'Intento {n}'), 1,
            ), range(4)))
        self.assertEqual(sum(estado == 'ok' for estado, _ in resultados), 1)
        self.assertEqual(self.consulta('SELECT COUNT(*) n FROM mantenimiento_bien')[0]['n'], 1)

    def test_man01_no_entra_con_prestamo_pendiente(self):
        self.prestar([3])
        with self.assertRaises(Conflicto):
            self.servicios['bienes'].abrir_mantenimiento(3, dict(tipo='PREVENTIVO', motivo='x'), 1)
        with self.assertRaises(ValueError):
            self.servicios['bienes'].cambiar_estado_bien_material(1, dict(
                estado='MANTENIMIENTO', estado_esperado='DISPONIBLE', motivo='Por atajo'), 1)

    # AMP-01

    def test_amp01_solicitar_rechazar_y_aprobar_una_sola_vez(self):
        ampliaciones = self.servicios['ampliaciones']
        prestamo = self.prestar([1])
        detalle = self.detalle(prestamo, 1)
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
        self.assertEqual(self.detalle(prestamo, 1)['fecha_limite_devolucion'], limite)
        segunda = ampliaciones.solicitar_ampliacion(prestamo, detalle['id_detalle'],
                                                    dict(cantidad='1', unidad='DIAS', motivo='Sustentación'), 3)
        with ThreadPoolExecutor(max_workers=2) as hilos:
            resultados = list(hilos.map(lambda _: intentar(
                ampliaciones.aprobar_solicitud_ampliacion, segunda, {}, 2), range(2)))
        self.assertEqual(sum(estado == 'ok' for estado, _ in resultados), 1)
        self.assertEqual(self.detalle(prestamo, 1)['fecha_limite_devolucion'], limite + timedelta(days=1))
        fila = self.consulta('SELECT * FROM solicitud_ampliacion WHERE id_solicitud=%s', (segunda,))[0]
        self.assertEqual((fila['estado'], fila['dni_resolucion']), ('APROBADA', '10000002'))
        self.assertEqual(fila['fecha_limite_anterior'], limite)

    def test_amp01_aprobacion_rechazada_si_el_bien_ya_se_devolvio(self):
        ampliaciones = self.servicios['ampliaciones']
        prestamo = self.prestar([2])
        detalle = self.detalle(prestamo, 2)
        solicitud = ampliaciones.solicitar_ampliacion(prestamo, detalle['id_detalle'],
                                                      dict(cantidad='1', unidad='DIAS', motivo='Tesis'), 3)
        self.servicios['prestamos'].registrar_devolucion(prestamo, dict(
            detalles=[str(detalle['id_detalle'])], **{f"condicion_{detalle['id_detalle']}": 'BUENO',
                                                      f"codigo_recibido_{detalle['id_detalle']}": 'LAP-2'}), 2)
        with self.assertRaisesRegex(Conflicto, 'Rechaza'):
            ampliaciones.aprobar_solicitud_ampliacion(solicitud, {}, 2)
        self.assertEqual(self.consulta('SELECT estado FROM solicitud_ampliacion')[0]['estado'], 'PENDIENTE')

    def test_amp01_pedido_que_supera_la_politica_no_se_registra(self):
        prestamo = self.prestar([1])
        detalle = self.detalle(prestamo, 1)
        with self.assertRaises(ValueError):
            self.servicios['ampliaciones'].solicitar_ampliacion(
                prestamo, detalle['id_detalle'], dict(cantidad='10', unidad='DIAS', motivo='Mucho'), 3)
        self.assertEqual(self.consulta('SELECT COUNT(*) n FROM solicitud_ampliacion')[0]['n'], 0)

    # PRU-01 y PRU-03

    def test_pru01_devolucion_parcial_y_repeticion(self):
        prestamos = self.servicios['prestamos']
        prestamo = self.prestar([1, 2])
        detalle = self.detalle(prestamo, 1)['id_detalle']
        datos = dict(detalles=[str(detalle)], **{f'condicion_{detalle}': 'BUENO', f'codigo_recibido_{detalle}': 'LAP-1'})
        prestamos.registrar_devolucion(prestamo, datos, 2)
        estado = self.consulta('SELECT estado FROM prestamo WHERE id_prestamo=%s', (prestamo,))[0]['estado']
        self.assertEqual(estado, 'PARCIALMENTE_DEVUELTO')
        self.assertIsNone(self.detalle(prestamo, 2)['fecha_devolucion'])
        primera = self.detalle(prestamo, 1)['fecha_devolucion']
        with self.assertRaises(ValueError):
            prestamos.registrar_devolucion(prestamo, datos, 2)
        self.assertEqual(self.detalle(prestamo, 1)['fecha_devolucion'], primera)
        bienes = {f['id_bien']: f['estado'] for f in self.consulta('SELECT id_bien,estado FROM bien_material')}
        self.assertEqual((bienes[1], bienes[2]), ('DISPONIBLE', 'PRESTADO'))

    def test_pru03_dos_prestamos_simultaneos_del_mismo_bien(self):
        with ThreadPoolExecutor(max_workers=2) as hilos:
            resultados = list(hilos.map(lambda persona: intentar(self.prestar, [3], persona),
                                        ('20000001', '20000002')))
        self.assertEqual(sum(estado == 'ok' for estado, _ in resultados), 1, resultados)
        self.assertEqual(self.consulta('SELECT COUNT(*) n FROM detalle_prestamo WHERE id_bien=3')[0]['n'], 1)

    def _preparar_prueba_cupo_grupal(self):
        self.consulta("INSERT INTO persona(dni,nombres,apellidos) VALUES('20000003','Rosa','Prueba')")
        self.consulta("INSERT INTO estudiante(dni,cui) VALUES('20000003','20000003')")
        self.consulta("INSERT INTO bien_material(id_bien,id_recurso,codigo_inventario) VALUES(4,1,'LAP-4')")

    def test_cn06_integrante_acumula_cupo_entre_grupos_y_libera_al_devolver(self):
        self._preparar_prueba_cupo_grupal()
        prestamos = self.servicios['prestamos']
        integrante = '20000002'
        primero = self.prestar([1, 2], '20000001', [integrante])
        self.assertEqual(prestamos.consultar_condiciones_prestamo('20000001')['pendientes'], 2)
        self.prestar([3], '20000003', [integrante])
        self.assertEqual(prestamos.consultar_condiciones_prestamo(integrante)['pendientes'], 3)
        with self.assertRaisesRegex(Conflicto, 'Diego Prueba tiene 3 bienes pendientes'):
            self.prestar([4], '20000003', [integrante])
        with self.assertRaises(Conflicto):
            self.prestar([4], integrante)

        detalle = self.detalle(primero, 1)['id_detalle']
        prestamos.registrar_devolucion(primero, dict(detalles=[str(detalle)], **{
            f'condicion_{detalle}': 'BUENO', f'codigo_recibido_{detalle}': 'LAP-1'}), 2)
        self.assertEqual(prestamos.consultar_condiciones_prestamo('20000001')['pendientes'], 1)
        self.assertEqual(prestamos.consultar_condiciones_prestamo(integrante)['pendientes'], 2)
        self.assertTrue(self.prestar([4], integrante))

    def test_cn06_entregas_simultaneas_comparten_el_cupo_del_integrante(self):
        self._preparar_prueba_cupo_grupal()
        integrante = '20000002'
        self.prestar([1, 2], '20000001', [integrante])
        inicio = Barrier(2)

        def entregar(datos):
            bien, responsable, actor = datos
            inicio.wait(timeout=5)
            return intentar(self.prestar, [bien], responsable, [integrante], actor)

        with ThreadPoolExecutor(max_workers=2) as hilos:
            resultados = list(hilos.map(entregar, ((3, '20000001', 1), (4, '20000003', 2))))
        self.assertEqual(sum(estado == 'ok' for estado, _ in resultados), 1, resultados)
        bloqueado = next(resultado for estado, resultado in resultados if estado == 'error')
        self.assertIsInstance(bloqueado, Conflicto)
        self.assertIn('Diego Prueba', str(bloqueado))

    def test_cupo_compartido_prioridad_y_entrega_de_la_reserva(self):
        reservas = self.servicios['reservas']
        self.consulta("UPDATE limite_articulos_prestamo SET maximo_articulos=1 WHERE tipo_persona='ESTUDIANTE'")
        self.consulta("INSERT INTO recurso(id_recurso,id_categoria,nombre) VALUES(2,1,'Tablet')")
        manana = (datetime.now(LIMA).date() + timedelta(days=1)).isoformat()
        datos = dict(id_recurso=1, fecha_requerida=f'{manana}T10:00', acepta_condiciones='1')
        reserva = reservas.registrar_reserva(datos, 3)
        with self.assertRaisesRegex(Conflicto, 'reservas activas'):
            reservas.registrar_reserva(dict(datos, id_recurso=2), 3)
        with self.assertRaisesRegex(Conflicto, 'reservas activas'):
            self.prestar([1])
        with self.assertRaisesRegex(Conflicto, 'después de su plazo'):
            reservas.expirar_reserva(reserva, {'motivo': 'Todavía en plazo'}, 2)
        self.consulta('UPDATE reserva SET fecha_requerida=UTC_TIMESTAMP()-INTERVAL 1 SECOND WHERE id_reserva=%s', (reserva,))
        self.consulta("UPDATE bien_material SET estado='MANTENIMIENTO' WHERE id_bien IN (2,3)")
        with self.assertRaisesRegex(Conflicto, 'Atiende primero'):
            self.prestar([1], '20000002')
        reservas.preparar_reserva(reserva, {}, 2)
        prestamo = reservas.entregar_reserva(reserva, {'acepta_condiciones': '1'}, 2)
        self.assertEqual(reservas.consultar_reserva(reserva, '20000001')['estado'], 'ATENDIDA')
        self.assertIsNotNone(self.detalle(prestamo, 1))

    def test_ampliacion_unica_y_reserva_sin_ejemplar(self):
        ampliaciones = self.servicios['ampliaciones']
        prestamo = self.prestar([1, 2, 3])
        detalle = self.detalle(prestamo, 1)
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
        self.consulta("INSERT INTO estudiante(dni,cui) VALUES('10000002','10000002')")
        servicio = self.servicios['prestamos']
        with self.assertRaisesRegex(Conflicto, 'otro administrador'):
            self.prestar([1], '10000002')
        permiso = servicio.autorizar_operacion_propia(dict(dni_operador='10000002', accion='ENTREGA', motivo='Préstamo autorizado del ejemplar LAP-1.'), 1)
        prestamo = self.prestar([1], '10000002', autorizacion=permiso)
        with self.assertRaisesRegex(Conflicto, 'ya se usó'):
            self.prestar([2], '10000002', autorizacion=permiso)
        detalle = self.detalle(prestamo, 1)['id_detalle']
        datos = dict(detalles=[str(detalle)], **{f'condicion_{detalle}': 'BUENO', f'codigo_recibido_{detalle}': 'LAP-1'})
        with self.assertRaisesRegex(Conflicto, 'no corresponde'):
            servicio.registrar_devolucion(prestamo, dict(datos, autorizacion=permiso), 2)
        recepcion = servicio.autorizar_operacion_propia(dict(dni_operador='10000002', accion='DEVOLUCION', id_prestamo=prestamo, motivo='Recepción autorizada del ejemplar LAP-1.'), 1)
        servicio.registrar_devolucion(prestamo, dict(datos, autorizacion=recepcion), 2)
        self.assertIsNotNone(self.detalle(prestamo, 1)['fecha_devolucion'])
        registro = self.consulta('''SELECT estado_nuevo,dni_objetivo,dni_responsable,
            datos->>'$.id_prestamo_uso' AS prestamo FROM historial_estado WHERE id_historial_estado=%s''',
            (recepcion,))[0]
        self.assertEqual(registro, dict(estado_nuevo='UTILIZADA',dni_objetivo='10000002',
                                       dni_responsable='10000001',prestamo=str(prestamo)))

    def test_cambio_tipo_persona_conserva_cuenta_prestamo_y_motivo(self):
        prestamo = self.prestar()
        servicio = self.servicios['personas']
        persona, version = servicio.consultar_persona('20000001')
        datos = dict(persona.datos(), version=version, tipo='DOCENTE', correo='lucia@unsa.edu.pe',
                     codigo_docente='DOC-001', departamento_academico='Informática',
                     facultad='Ingeniería', escuela_profesional='Computación', motivo_cambio_tipo='Nombramiento')
        servicio.actualizar_persona(persona.dni, datos, 1)
        nueva, _ = servicio.consultar_persona(persona.dni)
        self.assertEqual(nueva.tipo, 'DOCENTE')
        self.assertEqual(servicio.consultar_cambios_tipo_persona(persona.dni)[0]['motivo'], 'Nombramiento')
        historial = self.consulta('''SELECT datos->>'$.datos_institucionales.cui' AS cui
            FROM historial_estado WHERE entidad='TIPO_PERSONA' AND dni_objetivo=%s''', (persona.dni,))[0]
        self.assertEqual(historial['cui'], '20000001')
        self.assertEqual(self.consulta('SELECT dni_persona FROM usuario_sistema WHERE id_usuario=3')[0]['dni_persona'], persona.dni)
        self.assertEqual(self.detalle(prestamo, 1)['id_politica'], 1)

    def test_codigo_devolucion_y_rectificacion_administrativa(self):
        servicio = self.servicios['prestamos']
        prestamo = self.prestar()
        detalle = self.detalle(prestamo, 1)['id_detalle']
        datos = dict(detalles=[str(detalle)], **{f'condicion_{detalle}': 'BUENO'})
        with self.assertRaisesRegex(Conflicto, 'no coincide'):
            servicio.registrar_devolucion(prestamo, dict(datos, **{f'codigo_recibido_{detalle}': 'LAP-2'}), 2)
        servicio.registrar_discrepancia_devolucion(prestamo, detalle, 'Se presentó LAP-2.', 2)
        self.assertIsNone(self.detalle(prestamo, 1)['fecha_devolucion'])
        servicio.registrar_devolucion(prestamo, dict(datos, **{f'codigo_recibido_{detalle}': 'LAP-1'}), 2)
        with self.assertRaises(PermissionError):
            servicio.rectificar_devolucion(prestamo, detalle, 'Registro accidental', 2)
        servicio.rectificar_devolucion(prestamo, detalle, 'Registro accidental', 1)
        self.assertIsNone(self.detalle(prestamo, 1)['fecha_devolucion'])
        self.assertEqual(self.consulta('SELECT estado FROM bien_material WHERE id_bien=1')[0]['estado'], 'PRESTADO')
        registro = self.consulta('''SELECT dni_objetivo,datos->>'$.condicion_original' AS condicion,
            datos->>'$.fecha_devolucion_original' AS fecha FROM historial_estado
            WHERE entidad='RECTIFICACION_DEVOLUCION' AND id_entidad=%s''', (detalle,))[0]
        self.assertEqual((registro['dni_objetivo'], registro['condicion']), ('10000002', 'BUENO'))
        self.assertIsNotNone(registro['fecha'])

    # OPE-01

    def test_ope01_exclusion_y_registro_de_ejecuciones(self):
        repositorio = RepositorioProcesadorSQL(self.conexion)
        with repositorio.bloqueo_exclusivo() as primero:
            with RepositorioProcesadorSQL(self.conexion).bloqueo_exclusivo() as segundo:
                self.assertTrue(primero)
                self.assertFalse(segundo)
        procesador = ServicioAplicacionProcesador(repositorio)
        self.assertTrue(procesador.consultar_estado_procesador()['alerta'], 'nunca se ejecutó')
        self.assertEqual(procesador.ejecutar_revision([lambda: None]), 'ok')
        self.assertFalse(procesador.consultar_estado_procesador()['alerta'])

        def falla():
            raise RuntimeError('base caída')

        self.assertEqual(procesador.ejecutar_revision([falla]), 'error')
        estado = procesador.consultar_estado_procesador()
        self.assertIn('base caída', estado['ultimo_error'])
        self.assertEqual(estado['fallos_consecutivos'], 1)
        self.consulta('''UPDATE estado_procesador
            SET ultima_ejecucion_correcta=UTC_TIMESTAMP()-INTERVAL 6 MINUTE''')
        self.assertTrue(procesador.consultar_estado_procesador()['alerta'])

    def test_ope01_revision_real_de_vencimientos(self):
        procesador = ServicioAplicacionProcesador(RepositorioProcesadorSQL(self.conexion))
        resultado = procesador.ejecutar_revision([
            self.servicios['sanciones'].procesar_sanciones_por_vencimiento,
            self.servicios['reservas'].expirar_reservas_vencidas,
        ])
        self.assertEqual(resultado, 'ok')

    def test_ope01_reinicio_y_segundo_procesador_respetan_el_intervalo(self):
        primero = ServicioAplicacionProcesador(RepositorioProcesadorSQL(self.conexion))
        segundo = ServicioAplicacionProcesador(RepositorioProcesadorSQL(self.conexion))
        revisiones = []
        operaciones = [lambda: revisiones.append('revisado')]
        periodo = timedelta(seconds=30)
        self.assertEqual(primero.ejecutar_revision(operaciones, intervalo_minimo=periodo), 'ok')
        self.assertEqual(segundo.ejecutar_revision(operaciones, intervalo_minimo=periodo), 'omitida')
        self.consulta('UPDATE estado_procesador SET ultima_ejecucion_correcta=UTC_TIMESTAMP()-INTERVAL 31 SECOND')
        self.assertEqual(segundo.ejecutar_revision(operaciones, intervalo_minimo=periodo), 'ok')
        self.assertEqual(revisiones, ['revisado', 'revisado'])

    # MIG-01

    def test_mig01_migracion_desde_esquema_anterior_y_repetible(self):
        with self.conexion.sesion(escritura=True) as cur:
            for tabla in ('estado_procesador', 'solicitud_ampliacion', 'mantenimiento_bien', 'sesion_usuario'):
                cur.execute(f'DROP TABLE {tabla}')
            cur.execute('ALTER TABLE bien_material DROP INDEX uq_bien_identificador_sistema, '
                        'DROP COLUMN identificador_sistema, DROP COLUMN fecha_registro')
        migrar_esquema_cierre(self.conexion)
        migrar_esquema_cierre(self.conexion)
        filas = self.consulta('SELECT codigo_inventario,identificador_sistema FROM bien_material')
        self.assertEqual(len(filas), 3)
        self.assertEqual(len({f['identificador_sistema'] for f in filas}), 3)
        self.assertTrue(all(f['identificador_sistema'] for f in filas))
        self.assertEqual(self.consulta('SELECT COUNT(*) n FROM estado_procesador')[0]['n'], 1)


if __name__ == '__main__':
    unittest.main()
