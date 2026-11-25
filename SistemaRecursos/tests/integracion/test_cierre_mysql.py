"""Integración con MySQL del cierre de pendientes del informe.

Cubre SEG-01, SEG-02, SEG-03, AUT-01, AUT-02, MAN-01, AMP-01, OPE-01, MIG-01 y casos de
PRU-01 y PRU-03. Usa la misma base exclusiva de pruebas que test_sanciones_mysql:
requiere TEST_MYSQL_PORT (y TEST_MYSQL_PASSWORD si corresponde); cada caso crea y borra
su propia base, nunca la de la aplicación.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
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

    def prestar(self, bienes=(1,), persona='20000001', participantes=(), actor=2):
        return self.servicios['prestamos'].registrar_prestamo(dict(
            dni_persona=persona, bienes=[str(b) for b in bienes], acepta_condiciones='1',
            tipo_prestamo='GRUPAL' if participantes else 'INDIVIDUAL', participantes=participantes,
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
            detalles=[str(detalle['id_detalle'])], **{f"condicion_{detalle['id_detalle']}": 'BUENO'}), 2)
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
        datos = dict(detalles=[str(detalle)], **{f'condicion_{detalle}': 'BUENO'})
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
        prestamos.registrar_devolucion(primero, dict(detalles=[str(detalle)], **{f'condicion_{detalle}': 'BUENO'}), 2)
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
