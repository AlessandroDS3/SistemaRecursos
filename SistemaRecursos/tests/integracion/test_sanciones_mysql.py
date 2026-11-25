"""Reglas puras, permisos HTTP e integración con una base MySQL exclusiva de pruebas.

Para integración: TEST_MYSQL_PORT y opcionalmente TEST_MYSQL_PASSWORD.
Cada caso crea una base pruebas_sanciones_* y la elimina al terminar.
"""

from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
import os
from secrets import token_hex
import unittest
from unittest.mock import patch

import mysql.connector

from app import create_app
from dominio.compartido.validacion import Conflicto
from dominio.gestion_personas_usuarios.acceso import CuentaAcceso
from dominio.gestion_personas_usuarios.rol import permisos_del_rol
from repositorio.base_datos.conexion_mysql import MySQLConnection
from repositorio.control.repositorio_sancion_sql import RepositorioSancionSQL
from repositorio.prestamos.repositorio_prestamo_sql import RepositorioPrestamoSQL
from servicios.control.servicio_sancion import ServicioAplicacionSancion
from servicios.prestamos.servicio_prestamo import ServicioAplicacionPrestamo
from tests.soporte_roles import cliente_autenticado


@unittest.skipUnless(os.getenv('TEST_MYSQL_PORT'), 'Requiere TEST_MYSQL_PORT')
class BaseMySQLTest(unittest.TestCase):
    def setUp(self):
        self.nombre_base = 'pruebas_sanciones_' + token_hex(6)
        servidor = dict(host='127.0.0.1', port=int(os.environ['TEST_MYSQL_PORT']), user='root',
                        password=os.getenv('TEST_MYSQL_PASSWORD', ''), use_pure=True)
        # La conexión que crea el esquema se confirma y se cierra de inmediato: si siguiera
        # abierta, retendría bloqueos de metadatos y el DROP DATABASE final esperaría para siempre.
        conexion = mysql.connector.connect(**servidor)
        try:
            cursor = conexion.cursor()
            esquema = (Path(__file__).parents[2] / 'sql/schema.sql').read_text(encoding='utf-8')
            cursor.execute(esquema.replace('prestamos_escuela', self.nombre_base))
            while cursor.nextset():
                pass
            cursor.close()
            conexion.commit()
        finally:
            conexion.close()

        def eliminar_base():
            with mysql.connector.connect(**servidor) as c:
                with c.cursor() as cur:
                    cur.execute('DROP DATABASE `' + self.nombre_base + '`')
        self.addCleanup(eliminar_base)
        self.config = dict(servidor, database=self.nombre_base)
        self.conexion = MySQLConnection(self.config)

    def consulta(self, sql, parametros=()):
        with self.conexion.sesion(escritura=True) as cur:
            cur.execute(sql, parametros)
            return cur.fetchall() if cur.with_rows else []


class SancionesMySQLTest(BaseMySQLTest):
    def setUp(self):
        super().setUp()
        self.repo = RepositorioSancionSQL(self.conexion)
        self.servicio = ServicioAplicacionSancion(self.repo)
        self.prestamos_repo = RepositorioPrestamoSQL(self.conexion)
        self.prestamos = ServicioAplicacionPrestamo(self.prestamos_repo)
        self.ahora = self.repo.consultar_fecha_actual()
        with self.conexion.sesion(escritura=True) as cur:
            for documento, nombre in (('10000001', 'Admin'), ('10000002', 'Encargado'),
                                      ('20000001', 'Estudiante'), ('20000002', 'Integrante')):
                cur.execute('INSERT INTO persona(dni,nombres,apellidos,estado) VALUES(%s,%s,%s,%s)',
                            (documento, nombre, 'Prueba', 'ACTIVA'))
            for identificador, rol, documento in ((1, 'ADMINISTRADOR', '10000001'),
                                                  (2, 'ENCARGADO_PRESTAMOS', '10000002'),
                                                  (3, 'USUARIO', '20000001')):
                cur.execute('''INSERT INTO usuario_sistema(id_usuario,dni_persona,nombre_usuario,
                    contrasena_hash,rol) VALUES(%s,%s,%s,'pruebas',%s)''',
                    (identificador, documento, rol.lower(), rol))
            cur.execute("INSERT INTO estudiante(dni,cui) VALUES('20000001','20000001'),('20000002','20000002')")
            cur.execute("INSERT INTO categoria_recurso(id_categoria,nombre) VALUES(1,'Equipos')")
            cur.execute("INSERT INTO recurso(id_recurso,id_categoria,nombre) VALUES(1,1,'Laptop de pruebas')")
            cur.execute("INSERT INTO bien_material(id_bien,id_recurso,codigo_inventario,estado) VALUES(1,1,'ORIGINAL','PRESTADO'),(2,1,'OTRO','DISPONIBLE')")
            cur.execute("INSERT INTO politica_prestamo(id_politica,tipo_persona,id_categoria,plazo_maximo,unidad_plazo) VALUES(1,'ESTUDIANTE',1,3,'HORAS')")
            cur.execute("INSERT INTO limite_articulos_prestamo VALUES('ESTUDIANTE',3)")
            cur.execute("INSERT INTO configuracion_general(id_configuracion,hora_apertura,hora_cierre,plazo_espera,plazo_retiro) VALUES(1,'08:00','16:00',2,24)")
            cur.execute("INSERT INTO prestamo(id_prestamo,dni_persona,dni_encargado,fecha_solicitud,fecha_entrega) VALUES(1,'20000001','10000002',%s,%s)",
                        (self.ahora - timedelta(hours=2), self.ahora - timedelta(hours=2)))
            cur.execute('INSERT INTO detalle_prestamo(id_detalle,id_prestamo,id_bien,id_politica,fecha_limite_devolucion) VALUES(1,1,1,1,%s)',
                        (self.ahora - timedelta(minutes=20),))

    def sancion(self):
        return self.repo.consultar_sanciones()[0]

    def devolver(self, condicion='BUENO'):
        self.prestamos.registrar_devolucion(1, dict(detalles=['1'], condicion_1=condicion, codigo_recibido_1='ORIGINAL',
                                                  observacion_1='Verificación física del bien'), 2)

    def perder(self):
        self.prestamos.registrar_perdida_bien_material(1, 1, 'Pérdida confirmada por el solicitante', 2)

    def reponer(self, identificador=None, codigo='REPOSICION'):
        self.servicio.regularizar_sancion(identificador or self.sancion()['id_sancion'], dict(
            tipo_regularizacion='REPOSICION', codigo_inventario=codigo,
            observacion='Se verificó equivalencia técnica y buen estado', acepta_equivalencia='1',
        ), 2)

    def cliente(self, rol):
        with patch('app.clave_local', return_value='pruebas-sanciones'):
            app = create_app(dict(TESTING=True, MYSQL_CONFIG=self.config))
        identificador, documento = {'ADMINISTRADOR': (1, '10000001'),
                                    'ENCARGADO_PRESTAMOS': (2, '10000002'),
                                    'USUARIO': (3, '20000001')}[rol]
        cuenta = CuentaAcceso(id_usuario=identificador, dni=documento, nombre_usuario='prueba',
                             nombres='Prueba', apellidos='Persona', rol=rol,
                             estado_cuenta='ACTIVA', estado_persona='ACTIVA',
                             contrasena_hash='pruebas', permisos=permisos_del_rol(rol))
        return cliente_autenticado(self, app, cuenta, identificador)

    def test_retraso_inmediato_sin_duplicados_y_bloqueo_grupal(self):
        self.consulta('UPDATE detalle_prestamo SET fecha_limite_devolucion=DATE_SUB(UTC_TIMESTAMP(),INTERVAL 1 SECOND)')
        self.consulta("UPDATE prestamo SET tipo_prestamo='GRUPAL'")
        self.consulta("INSERT INTO participante_prestamo(id_prestamo,dni_persona) VALUES(1,'20000001'),(1,'20000002')")
        self.assertEqual(self.servicio.procesar_sanciones_por_vencimiento(), 1)
        self.assertEqual(self.servicio.procesar_sanciones_por_vencimiento(), 0)
        s = self.sancion()
        self.assertEqual(s['gravedad'], 'LEVE')
        self.assertEqual(s['fecha_fin'], s['fecha_limite_devolucion'] + timedelta(days=14))
        for documento in ('20000001', '20000002'):
            self.assertTrue(self.repo.existen_sanciones_activas([documento]))

    def test_eliminar_politica_usada_muestra_conflicto_y_conserva_prestamo(self):
        cliente = self.cliente('ADMINISTRADOR')
        respuesta = cliente.post('/politicas/1/eliminar', data=dict(csrf_token='token'))
        self.assertEqual(respuesta.status_code, 409)
        self.assertIn('tiene préstamos asociados', respuesta.get_data(as_text=True))
        self.assertEqual(self.consulta('SELECT id_politica FROM detalle_prestamo'), [{'id_politica': 1}])
        self.assertEqual(self.consulta('SELECT id_politica FROM politica_prestamo'), [{'id_politica': 1}])

    def test_reparacion_pendiente_remite_a_sancion_y_regulariza_el_bien(self):
        self.devolver('DANADO')
        sancion = self.sancion()
        cliente = self.cliente('ADMINISTRADOR')
        respuesta = cliente.get('/bienes/1')
        self.assertIn(f'/sanciones/{sancion["id_sancion"]}', respuesta.get_data(as_text=True))
        respuesta = cliente.post('/bienes/1/estado', data=dict(
            csrf_token='token', estado='DISPONIBLE', estado_esperado='DANADO', motivo='Reparación',
        ))
        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(self.sancion()['estado_bien'], 'DANADO')
        self.servicio.regularizar_sancion(
            sancion['id_sancion'], dict(tipo_regularizacion='REPARACION', observacion='Verificado'), 2,
        )
        actual = self.sancion()
        self.assertEqual((actual['estado_bien'], actual['tipo_regularizacion']), ('DISPONIBLE', 'REPARACION'))

    def test_acepta_reparacion_registrada_previamente_desde_inventario(self):
        self.devolver('DANADO')
        sancion = self.sancion()
        self.consulta("UPDATE bien_material SET estado='DISPONIBLE' WHERE id_bien=1")
        self.servicio.regularizar_sancion(
            sancion['id_sancion'], dict(tipo_regularizacion='REPARACION', observacion='Verificado'), 2,
        )
        self.assertEqual(self.sancion()['tipo_regularizacion'], 'REPARACION')

    def test_reporte_e_historial_coinciden_en_bien_perdido(self):
        from repositorio.reportes.repositorio_reporte_sql import RepositorioReporteSQL
        from servicios.reportes.servicio_reporte import ServicioAplicacionReporte

        self.consulta('UPDATE detalle_prestamo SET fecha_limite_devolucion=DATE_ADD(UTC_TIMESTAMP(),INTERVAL 1 HOUR)')
        self.perder()
        reportes = ServicioAplicacionReporte(RepositorioReporteSQL(self.conexion))
        reporte = reportes.consultar_reportes(dict(tipo='prestamos'))
        historial = reportes.consultar_reportes(dict(tipo='historial_bien', codigo_inventario='ORIGINAL'))
        self.assertEqual(reporte['filas'][0]['situacion'], 'PERDIDO')
        self.assertEqual(historial['prestamos_agrupados'][0]['detalles'][0]['situacion'], 'PERDIDO')

    def test_posicion_reserva_coincide_con_orden_de_atencion(self):
        from repositorio.prestamos.repositorio_reserva_sql import RepositorioReservaSQL

        repo = RepositorioReservaSQL(self.conexion)
        for orden, requerida, vence in ((4, 60, 180), (3, -120, -60), (2, -30, 60), (1, -15, 60)):
            self.consulta('''INSERT INTO reserva(dni_persona,id_recurso,fecha_solicitud,
                fecha_requerida,fecha_limite_vencimiento) VALUES('20000001',1,%s,%s,%s)''',
                (self.ahora - timedelta(days=orden), self.ahora + timedelta(minutes=requerida),
                 self.ahora + timedelta(minutes=vence)))
        self.assertEqual({r['id_reserva']: r['posicion'] for r in repo.consultar_reservas()},
                         {1: None, 2: None, 3: 1, 4: 2})
        with repo.transaccion() as op:
            self.assertEqual(op.consultar_primera_reserva_en_espera(1, self.ahora)['id_reserva'], 3)

    def test_reservas_cerradas_conservan_historial_del_bien_liberado(self):
        from repositorio.prestamos.repositorio_reserva_sql import RepositorioReservaSQL
        from repositorio.reportes.repositorio_reporte_sql import RepositorioReporteSQL
        from servicios.prestamos.servicio_reserva import ServicioAplicacionReserva
        from servicios.reportes.servicio_reporte import ServicioAplicacionReporte

        repositorio = RepositorioReservaSQL(self.conexion)
        reservas = ServicioAplicacionReserva(repositorio)
        reportes = ServicioAplicacionReporte(RepositorioReporteSQL(self.conexion))
        for accion, estado in (('cancelar', 'CANCELADA'), ('rechazar', 'RECHAZADA'),
                               ('expirar', 'EXPIRADA'), ('automatica', 'EXPIRADA')):
            with self.subTest(accion=accion):
                self.consulta("UPDATE bien_material SET estado='RESERVADO' WHERE id_bien=2")
                self.consulta('''INSERT INTO reserva(dni_persona,id_recurso,fecha_solicitud,
                    fecha_requerida,fecha_preparacion,fecha_limite_vencimiento,id_bien,estado)
                    VALUES('20000001',1,%s,%s,%s,%s,2,'LISTA_PARA_RETIRO')''',
                    (self.ahora - timedelta(days=2), self.ahora - timedelta(days=1),
                     self.ahora - timedelta(hours=2), self.ahora - timedelta(minutes=1)))
                identificador = self.consulta('SELECT MAX(id_reserva) AS id FROM reserva')[0]['id']
                if accion == 'automatica':
                    self.assertEqual(reservas.expirar_reservas_vencidas(), 1)
                    self.assertEqual(reservas.expirar_reservas_vencidas(), 0)
                else:
                    getattr(reservas, accion + '_reserva')(identificador, {'motivo': 'Cierre de prueba'}, 2)
                reserva = repositorio.consultar_reserva(identificador)
                self.assertEqual((reserva['estado'], reserva['id_bien']), (estado, 2))
                with repositorio.transaccion() as op:
                    self.assertEqual(op.consultar_bien_disponible(1)['id_bien'], 2)
                historial = reportes.consultar_reportes(dict(tipo='historial_bien', codigo_inventario='OTRO'))
                self.assertIn(identificador, [r['id_reserva'] for r in historial['reservas']])
                self.assertTrue(any(h['id_reserva'] == identificador and h['estado_nuevo'] == estado
                                    for h in historial['historial_reservas']))

    def test_configuracion_solo_admin_con_version_y_snapshot(self):
        self.servicio.procesar_sanciones_por_vencimiento()
        config, version = self.servicio.consultar_configuracion_sanciones()
        nuevos = dict(dias_leve=5, dias_grave=45, dias_espera_perdida=2)
        with self.assertRaises(PermissionError):
            self.servicio.guardar_configuracion_sanciones(nuevos, version, 2)
        self.servicio.guardar_configuracion_sanciones(nuevos, version, 1)
        with self.assertRaises(Conflicto):
            self.servicio.guardar_configuracion_sanciones(config, version, 1)
        self.assertEqual(self.sancion()['dias_leve'], 14)
        self.assertEqual(self.servicio.consultar_configuracion_sanciones()[0]['dias_leve'], 5)
        self.assertEqual(len(self.repo.consultar_historial_estado('CONFIGURACION_SANCIONES', 1)), 1)
        self.consulta("UPDATE bien_material SET estado='PRESTADO' WHERE id_bien=2")
        self.consulta('''INSERT INTO detalle_prestamo(id_detalle,id_prestamo,id_bien,id_politica,fecha_limite_devolucion)
            VALUES(2,1,2,1,DATE_SUB(UTC_TIMESTAMP(),INTERVAL 1 MINUTE))''')
        self.servicio.procesar_sanciones_por_vencimiento()
        nueva = next(s for s in self.repo.consultar_sanciones() if s['id_detalle'] == 2)
        self.assertEqual((nueva['dias_leve'], nueva['dias_grave'], nueva['dias_espera_perdida']), (5, 45, 2))

    def test_devolucion_puntual_danada_aplica_grave(self):
        self.consulta('UPDATE detalle_prestamo SET fecha_limite_devolucion=DATE_ADD(UTC_TIMESTAMP(),INTERVAL 1 HOUR)')
        self.devolver('DANADO')
        s = self.sancion()
        self.assertEqual((s['gravedad'], s['tipo']), ('GRAVE', 'DANIO'))
        self.assertEqual(s['fecha_fin'], s['fecha_inicio_nivel'] + timedelta(days=180))
        self.assertIsNone(s['fecha_regularizacion'])
        with self.assertRaises(Conflicto):
            self.servicio.levantar_sancion(s['id_sancion'], 'Devuelto', 1)

    def test_retraso_y_danio_elevan_el_mismo_incidente(self):
        self.servicio.procesar_sanciones_por_vencimiento()
        anterior = self.sancion()
        self.devolver('DANADO')
        actual = self.sancion()
        self.assertEqual(actual['id_sancion'], anterior['id_sancion'])
        self.assertEqual(actual['fecha'], anterior['fecha'])
        self.assertEqual(actual['gravedad'], 'GRAVE')
        self.assertEqual(len(self.repo.consultar_sanciones()), 1)

    def test_perdida_y_reposicion_cierran_pendiente_sin_fingir_devolucion(self):
        self.perder()
        self.reponer()
        s = self.sancion()
        self.assertEqual(s['estado_bien'], 'PERDIDO')
        self.assertIsNone(s['fecha_devolucion'])
        self.assertIsNotNone(s['fecha_cierre_regularizacion'])
        self.assertIsNotNone(s['id_bien_reposicion'])
        self.assertEqual(s['estado'], 'ACTIVA')
        self.assertEqual(self.prestamos_repo.consultar_prestamo(1)['estado_actual'], 'REGULARIZADO')
        self.assertEqual(self.prestamos_repo.consultar_resumen_prestamos()['prestamos_pendientes'], 0)
        self.assertTrue(self.repo.existen_sanciones_activas(['20000001']))
        with self.assertRaises(Conflicto):
            self.devolver()

    def test_reposicion_parcial_conserva_los_otros_bienes_pendientes(self):
        self.consulta("UPDATE bien_material SET estado='PRESTADO' WHERE id_bien=2")
        self.consulta('''INSERT INTO detalle_prestamo(id_detalle,id_prestamo,id_bien,id_politica,fecha_limite_devolucion)
            VALUES(2,1,2,1,DATE_ADD(UTC_TIMESTAMP(),INTERVAL 1 HOUR))''')
        self.perder()
        self.reponer()
        self.assertEqual(self.prestamos_repo.consultar_prestamo(1)['estado_actual'], 'PARCIALMENTE_DEVUELTO')
        self.assertEqual(self.prestamos_repo.consultar_resumen_prestamos()['prestamos_pendientes'], 1)
        self.prestamos.registrar_devolucion(1, dict(detalles=['2'], condicion_2='BUENO', codigo_recibido_2='OTRO'), 2)
        self.assertEqual(self.prestamos_repo.consultar_prestamo(1)['estado_actual'], 'REGULARIZADO')

    def test_recuperacion_original_conserva_el_periodo_grave(self):
        self.perder()
        fin = self.sancion()['fecha_fin']
        self.servicio.regularizar_sancion(self.sancion()['id_sancion'], dict(
            tipo_regularizacion='RECUPERACION', codigo_recibido='ORIGINAL', observacion='Original recuperado en buen estado'), 2)
        s = self.sancion()
        self.assertIsNotNone(s['fecha_devolucion'])
        self.assertEqual((s['tipo_regularizacion'], s['estado'], s['fecha_fin']), ('RECUPERACION', 'ACTIVA', fin))
        self.assertEqual(s['estado_bien'], 'DISPONIBLE')

    def test_admin_anula_sancion_sin_borrar_el_pendiente(self):
        self.perder()
        sancion = self.sancion()['id_sancion']
        with self.assertRaises(PermissionError):
            self.servicio.anular_sancion(sancion, 'Aplicada por error', 2)
        self.servicio.anular_sancion(sancion, 'Aplicada por error', 1)
        self.assertEqual(self.sancion()['estado'], 'ANULADA')
        self.assertEqual(self.prestamos_repo.consultar_resumen_prestamos()['prestamos_pendientes'], 1)
        self.devolver('DANADO')
        filas = {s['tipo']: s['estado'] for s in self.repo.consultar_sanciones()}
        self.assertEqual(filas, {'DANIO': 'ACTIVA', 'PERDIDA': 'ANULADA'})

    def test_encargado_integrante_no_puede_adjudicar_sancion_propia(self):
        self.consulta("INSERT INTO participante_prestamo(id_prestamo,dni_persona) VALUES(1,'10000002')")
        with self.assertRaises(PermissionError):
            self.perder()
        self.prestamos.registrar_perdida_bien_material(1, 1, 'Pérdida comprobada', 1)
        sancion = self.sancion()['id_sancion']
        with self.assertRaises(PermissionError):
            self.servicio.levantar_sancion(sancion, 'Intento de levantamiento propio', 2)
        self.assertEqual(self.sancion()['estado'], 'ACTIVA')

    def test_original_recuperado_despues_de_reponer_va_a_revision(self):
        self.perder()
        self.reponer()
        anterior = self.sancion()
        self.servicio.registrar_original_recuperado(anterior['id_sancion'], 'Encontrado en almacén', 1)
        sancion = self.sancion()
        self.assertEqual(sancion['id_bien_reposicion'], anterior['id_bien_reposicion'])
        self.assertEqual(sancion['estado_bien'], 'MANTENIMIENTO')
        self.assertIsNotNone(sancion['fecha_recuperacion_original'])
        self.assertEqual(self.prestamos_repo.consultar_prestamo(1)['estado_actual'], 'REGULARIZADO')

    def test_plazo_cumplido_sin_reponer_no_libera_y_reposicion_posterior_cumple(self):
        self.perder()
        self.consulta('UPDATE sancion SET fecha_fin=DATE_SUB(UTC_TIMESTAMP(),INTERVAL 1 DAY)')
        self.servicio.procesar_sanciones_por_vencimiento()
        self.assertEqual(self.sancion()['estado'], 'ACTIVA')
        self.assertTrue(self.servicio.consultar_sancion(self.sancion()['id_sancion'])['revision_administrador'])
        self.reponer()
        self.assertEqual(self.sancion()['estado'], 'CUMPLIDA')
        self.assertFalse(self.repo.existen_sanciones_activas(['20000001']))

    def test_muy_grave_solo_admin_sin_cierre_automatico(self):
        self.perder()
        s = self.sancion()
        datos = dict(causa='PERDIDA', gravedad='MUY_GRAVE', motivo='Evaluación administrativa del caso')
        with self.assertRaises(PermissionError):
            self.servicio.evaluar_sancion(s['id_sancion'], datos, 2)
        self.assertEqual(self.sancion()['gravedad'], 'GRAVE')
        self.servicio.evaluar_sancion(s['id_sancion'], datos, 1)
        self.assertIsNone(self.sancion()['fecha_fin'])
        self.reponer()
        self.servicio.procesar_sanciones_por_vencimiento()
        self.assertEqual(self.sancion()['estado'], 'ACTIVA')
        with self.assertRaises(PermissionError):
            self.servicio.levantar_sancion(s['id_sancion'], 'Reposición comprobada', 2)
        self.servicio.levantar_sancion(s['id_sancion'], 'Rehabilitación autorizada', 1)
        self.assertEqual(self.sancion()['estado'], 'LEVANTADA')

    def test_elevar_no_borra_una_reposicion_ya_aceptada(self):
        self.perder()
        self.reponer()
        original = self.sancion()
        self.servicio.evaluar_sancion(original['id_sancion'], dict(
            causa='PERDIDA', gravedad='MUY_GRAVE', motivo='Evaluación del impacto del incidente'), 1)
        actual = self.sancion()
        self.assertEqual(actual['fecha_regularizacion'], original['fecha_regularizacion'])
        self.assertEqual(actual['id_bien_reposicion'], original['id_bien_reposicion'])
        self.assertIsNone(actual['fecha_fin'])

    def test_encargado_puede_recibir_original_danado_con_muy_grave(self):
        self.perder()
        self.servicio.evaluar_sancion(self.sancion()['id_sancion'], dict(
            causa='PERDIDA', gravedad='MUY_GRAVE', motivo='Evaluación administrativa'), 1)
        self.devolver('DANADO')
        s = self.sancion()
        self.assertEqual((s['gravedad'], s['tipo']), ('MUY_GRAVE', 'DANIO'))
        self.assertIsNotNone(s['fecha_devolucion'])
        self.assertIsNone(s['fecha_regularizacion'])
        self.servicio.regularizar_sancion(s['id_sancion'], dict(
            tipo_regularizacion='REPARACION', observacion='Reparación comprobada'), 2)
        self.assertEqual(self.sancion()['estado'], 'ACTIVA')

    def test_dos_procesadores_no_duplican_sancion(self):
        with ThreadPoolExecutor(max_workers=2) as procesos:
            resultados = list(procesos.map(lambda _: self.servicio.procesar_sanciones_por_vencimiento(), range(2)))
        self.assertEqual(sum(resultados), 1)
        self.assertEqual(len(self.repo.consultar_sanciones()), 1)

    def test_devolucion_leve_no_perdona_automaticamente_y_encargado_decide(self):
        self.devolver()
        self.assertEqual(self.sancion()['estado'], 'ACTIVA')
        with self.assertRaises(ValueError):
            self.servicio.levantar_sancion(self.sancion()['id_sancion'], '', 2)
        self.servicio.levantar_sancion(self.sancion()['id_sancion'], 'Demora del encargado al recibir', 2)
        self.assertEqual(self.sancion()['estado'], 'LEVANTADA')

    def test_leve_cumple_solo_despues_de_devolver(self):
        self.consulta('UPDATE detalle_prestamo SET fecha_limite_devolucion=DATE_SUB(UTC_TIMESTAMP(),INTERVAL 16 DAY)')
        self.servicio.procesar_sanciones_por_vencimiento()
        self.assertEqual(self.sancion()['estado'], 'ACTIVA')
        self.devolver()
        self.assertEqual(self.sancion()['estado'], 'CUMPLIDA')

    def test_posible_perdida_es_solo_alerta(self):
        self.consulta('UPDATE detalle_prestamo SET fecha_limite_devolucion=DATE_SUB(UTC_TIMESTAMP(),INTERVAL 22 DAY)')
        self.servicio.procesar_sanciones_por_vencimiento()
        s = self.servicio.consultar_sancion(self.sancion()['id_sancion'])
        self.assertTrue(s['posible_perdida'])
        self.assertEqual((s['gravedad'], s['estado_bien']), ('LEVE', 'PRESTADO'))

    def test_reparacion_no_acorta_sancion_grave(self):
        self.devolver('DANADO')
        self.servicio.regularizar_sancion(self.sancion()['id_sancion'], dict(
            tipo_regularizacion='REPARACION', observacion='Reparación comprobada y funcionamiento verificado'), 2)
        self.assertEqual(self.sancion()['estado'], 'ACTIVA')
        self.assertEqual(self.sancion()['estado_bien'], 'DISPONIBLE')
        self.consulta('UPDATE sancion SET fecha_fin=DATE_SUB(UTC_TIMESTAMP(),INTERVAL 1 SECOND)')
        self.servicio.procesar_sanciones_por_vencimiento()
        self.assertEqual(self.sancion()['estado'], 'CUMPLIDA')

    def test_reposicion_invalida_revierte_toda_la_operacion(self):
        self.perder()
        with self.assertRaises(ValueError):
            self.reponer(codigo='ORIGINAL')
        s = self.sancion()
        self.assertIsNone(s['fecha_regularizacion'])
        self.assertIsNone(s['fecha_cierre_regularizacion'])
        self.assertEqual(len(self.consulta('SELECT * FROM bien_material')), 2)

    def test_salida_sin_permiso_exige_evaluacion_y_respeta_politica_aplicada(self):
        datos = dict(causa='SALIDA_NO_AUTORIZADA', gravedad='GRAVE', motivo='Retiro del equipo verificado')
        self.consulta('UPDATE politica_prestamo SET permite_salida=1')
        with self.assertRaises(Conflicto):
            self.servicio.registrar_sancion_por_detalle_prestamo(1, 1, datos, 2)
        self.assertFalse(self.repo.consultar_sanciones())
        self.consulta('UPDATE politica_prestamo SET permite_salida=0')
        self.devolver()
        self.servicio.evaluar_sancion(self.sancion()['id_sancion'], datos, 2)
        self.assertEqual(self.sancion()['gravedad'], 'GRAVE')
        self.assertIsNotNone(self.sancion()['fecha_regularizacion'])

    def test_pantallas_permisos_y_csrf(self):
        self.perder()
        identificador = self.sancion()['id_sancion']
        admin = self.cliente('ADMINISTRADOR')
        self.assertEqual(admin.get('/sanciones').status_code, 200)
        self.assertIn('Configurar plazos', admin.get('/sanciones').get_data(as_text=True))
        detalle = admin.get(f'/sanciones/{identificador}')
        self.assertEqual(detalle.status_code, 200)
        self.assertIn('Reposición equivalente', detalle.get_data(as_text=True))
        self.assertEqual(admin.get('/prestamos/1').status_code, 200)
        self.assertEqual(admin.post(f'/sanciones/{identificador}/regularizar', data={}).status_code, 400)
        encargado = self.cliente('ENCARGADO_PRESTAMOS')
        self.assertNotIn('Configurar plazos', encargado.get('/sanciones').get_data(as_text=True))
        self.assertEqual(encargado.post('/sanciones/configuracion', data=dict(
            csrf_token='token', dias_leve=14, dias_grave=180, dias_espera_perdida=7,
        )).status_code, 403)
        self.assertEqual(encargado.post(f'/sanciones/{identificador}/evaluar', data=dict(
            csrf_token='token', causa='PERDIDA', gravedad='MUY_GRAVE', motivo='Intento no autorizado',
        )).status_code, 403)
        usuario = self.cliente('USUARIO')
        self.assertEqual(usuario.get('/sanciones').status_code, 403)
        self.assertEqual(usuario.post(f'/sanciones/{identificador}/levantar', data=dict(
            csrf_token='token', justificacion='Intento no autorizado',
        )).status_code, 403)

    def test_reportes_exportan_gravedad_y_distinguen_reposicion_de_devolucion(self):
        self.perder()
        self.reponer()
        cliente = self.cliente('ADMINISTRADOR')
        reporte = cliente.get('/reportes?tipo=prestamos')
        self.assertEqual(reporte.status_code, 200)
        self.assertIn('Regularizado', reporte.get_data(as_text=True))
        csv = cliente.get('/reportes/exportar.csv?tipo=sanciones')
        self.assertEqual(csv.status_code, 200)
        self.assertIn('gravedad', csv.get_data(as_text=True))
        self.assertIn('GRAVE', csv.get_data(as_text=True))
        self.assertIn('REPOSICION', csv.get_data(as_text=True))
        pdf = cliente.get('/reportes/exportar.pdf?tipo=sanciones')
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.data.startswith(b'%PDF'))
        historial = cliente.get('/reportes?tipo=historial_persona&dni_persona=20000001')
        self.assertEqual(historial.status_code, 200)
        self.assertIn('Regularización por reposición', historial.get_data(as_text=True))


class AltaInicialMySQLTest(BaseMySQLTest):
    def test_alta_inicial_en_base_vacia(self):
        from arranque.inicializar_administrador import main

        args = ['--dni', '10000001', '--nombres', 'Ana', '--apellidos', 'Prueba',
                '--correo', 'ana@example.edu', '--codigo-empleado', 'ADM001',
                '--area', 'Administración', '--usuario', 'ana']
        entorno = dict(DB_HOST='127.0.0.1', DB_PORT=str(self.config['port']),
                       DB_NAME=self.nombre_base, DB_USER='root', DB_PASSWORD=self.config['password'])
        salida = StringIO()
        with patch.dict(os.environ, entorno), redirect_stdout(salida), redirect_stderr(StringIO()):
            self.assertEqual(main(args), 0)
            args[1] = '10000002'
            self.assertEqual(main(args), 1)
        codigo = salida.getvalue().splitlines()[1].split(': ', 1)[1]
        self.assertEqual(self.consulta('SELECT dni FROM persona'), [{'dni': '10000001'}])
        with patch('app.clave_local', return_value='prueba-alta-inicial'):
            app = create_app(dict(TESTING=True, MYSQL_CONFIG=self.config))
        cliente = app.test_client()
        self.assertEqual(cliente.get('/cuentas/activar').status_code, 200)
        with cliente.session_transaction() as sesion:
            csrf = sesion['csrf']
        clave = 'UnaClaveNueva2026!'
        respuesta = cliente.post('/cuentas/activar', data=dict(csrf_token=csrf, usuario='ana', codigo=codigo,
                                                              clave_nueva=clave, confirmacion=clave))
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta.location, '/login')
        cliente.get('/login')
        with cliente.session_transaction() as sesion:
            csrf = sesion['csrf']
        self.assertEqual(cliente.post('/login', data=dict(csrf_token=csrf, usuario='ana', clave=clave)).location, '/')
        self.assertEqual(self.consulta('SELECT rol FROM usuario_sistema'), [{'rol': 'ADMINISTRADOR'}])


if __name__ == '__main__':
    unittest.main()
