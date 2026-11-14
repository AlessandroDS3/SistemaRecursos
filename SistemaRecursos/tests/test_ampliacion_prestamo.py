from datetime import datetime, timedelta
import os
import unittest
from unittest.mock import patch

from dominio.gestion_control.control import HorarioAtencion
from dominio.gestion_control.control import PoliticaPrestamo
from dominio.gestion_prestamos.prestamos import AmpliacionPrestamo, ConflictoAmpliacionError


class AmpliacionDominioTest(unittest.TestCase):
    def setUp(self):
        self.ahora = datetime(2026, 11, 12, 14)
        self.anterior = self.ahora + timedelta(days=1)
        self.detalle = dict(fecha_devolucion=None, estado_actual='PRESTADO',
                            fecha_limite_devolucion=self.anterior)
        self.politica = PoliticaPrestamo(tipo_persona='ESTUDIANTE', id_categoria=1,
                                       plazo_maximo=2, unidad_plazo='DIAS')

    def ampliar(self, cantidad=1, unidad='DIAS', **cambios):
        ampliacion = AmpliacionPrestamo(cantidad=cantidad, unidad=unidad,
                                       fecha_limite_anterior=self.anterior)
        return ampliacion.calcular_fecha(dict(self.detalle, **cambios), self.ahora, self.politica)

    def test_suma_horas_o_dias_al_plazo_actual(self):
        self.assertEqual(self.ampliar(2, 'HORAS'), self.anterior + timedelta(hours=2))
        self.assertEqual(self.ampliar(2), self.anterior + timedelta(days=2))

    def test_no_supera_la_politica_y_rechaza_cantidades_invalidas(self):
        for cantidad in (0, -1, 1.5, True, 'abc', 3, 10**30):
            with self.subTest(cantidad=cantidad), self.assertRaises(ValueError):
                self.ampliar(cantidad)
        with self.assertRaises(ValueError):
            self.ampliar(1, 'MINUTOS')

    def test_vencido_devuelto_perdido_o_formulario_antiguo_no_se_amplian(self):
        variantes = [dict(fecha_devolucion=self.ahora), dict(estado_actual='PERDIDO'),
                     dict(fecha_limite_devolucion=self.anterior + timedelta(hours=1))]
        for cambios in variantes:
            with self.subTest(cambios=cambios), self.assertRaises(ConflictoAmpliacionError):
                self.ampliar(**cambios)
        self.anterior = self.ahora
        self.detalle['fecha_limite_devolucion'] = self.ahora
        with self.assertRaises(ConflictoAmpliacionError):
            self.ampliar()

    def test_horas_respetan_cierre_y_exigen_horario(self):
        politica = PoliticaPrestamo(tipo_persona='ESTUDIANTE', id_categoria=1,
                                   plazo_maximo=4, unidad_plazo='HORAS')
        anterior = datetime(2026, 11, 12, 20)  # 15:00 Lima.
        detalle = dict(self.detalle, fecha_limite_devolucion=anterior)
        regla = AmpliacionPrestamo(cantidad=1, unidad='HORAS', fecha_limite_anterior=anterior)
        self.assertEqual(regla.calcular_fecha(detalle, self.ahora, politica, HorarioAtencion()),
                         datetime(2026, 11, 12, 21))
        regla.cantidad = 2
        with self.assertRaises(ValueError):
            regla.calcular_fecha(detalle, self.ahora, politica, HorarioAtencion())
        with self.assertRaises(ValueError):
            regla.calcular_fecha(detalle, self.ahora, politica)


@unittest.skipUnless(os.environ.get('TEST_MYSQL_PORT'), 'Configura MySQL de pruebas.')
class AmpliacionIntegracionTest(unittest.TestCase):
    def setUp(self):
        from soporte_prestamos import preparar_base_prestamos
        preparar_base_prestamos(self)
        self.servicio = self.app.extensions['ampliaciones']
        self.anterior = self.detalle()['fecha_limite_devolucion']
        self.ruta = '/prestamos/1/detalles/1/ampliar'

    def detalle(self):
        with self.db.sesion() as cursor:
            cursor.execute('SELECT * FROM detalle_prestamo WHERE id_detalle=1')
            return cursor.fetchone()

    def ampliar(self, usuario=2, cantidad=2, unidad='HORAS', fecha=None):
        return self.servicio.ampliar_plazo(1, 1, cantidad, unidad,
            (fecha or self.anterior).isoformat(), usuario, 'Más tiempo para la práctica')

    def cuenta(self, numero):
        cliente = self.app.test_client()
        cliente.get('/login')
        with cliente.session_transaction() as sesion:
            token = sesion['csrf_token']
        respuesta = cliente.post('/login', data=dict(usuario='cuenta' + str(numero),
                                                    clave=self.clave, csrf_token=token))
        self.assertEqual(respuesta.status_code, 302)
        cliente.get('/')
        with cliente.session_transaction() as sesion:
            token = sesion['csrf_token']
        return cliente, token

    def datos(self, token, **cambios):
        return dict(dict(csrf_token=token, cantidad='2', unidad='HORAS',
                         fecha_actual=self.anterior.isoformat()), **cambios)

    def test_encargado_amplia_inmediatamente_y_guarda_actor_y_fechas(self):
        nueva = self.ampliar()
        self.assertEqual(nueva, self.anterior + timedelta(hours=2))
        self.assertEqual(self.detalle()['fecha_limite_devolucion'], nueva)
        with self.db.sesion() as cursor:
            cursor.execute("SELECT * FROM historial_estado WHERE entidad='PRESTAMO' AND id_entidad=1")
            filas = cursor.fetchall()
            self.assertEqual(len(filas), 1)
            self.assertEqual(filas[0]['dni_responsable'], '98000002')
            self.assertIn(self.anterior.isoformat(sep=' '), filas[0]['observacion'])
            self.assertIn(nueva.isoformat(sep=' '), filas[0]['observacion'])
            cursor.execute("SHOW TABLES LIKE 'ampliacion_prestamo'")
            self.assertIsNone(cursor.fetchone())

    def test_administrador_amplia_y_repetir_formulario_no_duplica_tiempo(self):
        nueva = self.ampliar(usuario=1)
        with self.assertRaises(ConflictoAmpliacionError):
            self.ampliar(usuario=1)
        self.assertEqual(self.detalle()['fecha_limite_devolucion'], nueva)
        self.assertEqual(self.ampliar(usuario=1, fecha=nueva), nueva + timedelta(hours=2))

    def test_usuario_responsable_integrante_y_otro_no_pueden_ampliar(self):
        for usuario in (3, 4, 5):
            with self.subTest(usuario=usuario), self.assertRaises(PermissionError):
                self.ampliar(usuario)
        self.assertEqual(self.detalle()['fecha_limite_devolucion'], self.anterior)

    def test_limite_politica_y_detalle_ajeno_no_escriben(self):
        with self.assertRaises(ValueError):
            self.ampliar(cantidad=3, unidad='DIAS')
        with self.assertRaises(LookupError):
            self.servicio.ampliar_plazo(2, 1, 1, 'HORAS', self.anterior.isoformat(), 2)
        self.assertEqual(self.detalle()['fecha_limite_devolucion'], self.anterior)

    def test_perdida_devolucion_y_vencimiento_impiden_ampliacion(self):
        with self.db.sesion(escritura=True) as cursor:
            cursor.execute("UPDATE bien_material SET estado='PERDIDO' WHERE id_bien=1")
        with self.assertRaises(ConflictoAmpliacionError):
            self.ampliar()
        with self.db.sesion(escritura=True) as cursor:
            cursor.execute("UPDATE bien_material SET estado='DISPONIBLE' WHERE id_bien=1")
            cursor.execute("UPDATE detalle_prestamo SET fecha_devolucion=UTC_TIMESTAMP(),dni_encargado_devolucion='98000002',condicion_devolucion='BUENO' WHERE id_detalle=1")
        with self.assertRaises(ConflictoAmpliacionError):
            self.ampliar()
        with self.db.sesion(escritura=True) as cursor:
            cursor.execute("UPDATE bien_material SET estado='PRESTADO' WHERE id_bien=1")
            cursor.execute("UPDATE detalle_prestamo SET fecha_devolucion=NULL,dni_encargado_devolucion=NULL,condicion_devolucion=NULL,fecha_limite_devolucion=DATE_SUB(UTC_TIMESTAMP(),INTERVAL 1 MINUTE) WHERE id_detalle=1")
        with self.assertRaises(ConflictoAmpliacionError):
            self.ampliar(fecha=self.detalle()['fecha_limite_devolucion'])

    def test_fallo_historial_revierte_fecha(self):
        from repositorio.repositorio_prestamo_sql import OperacionPrestamoSQL
        with patch.object(OperacionPrestamoSQL, '_guardar_historial', side_effect=RuntimeError('Fallo simulado')):
            with self.assertRaises(RuntimeError):
                self.ampliar()
        self.assertEqual(self.detalle()['fecha_limite_devolucion'], self.anterior)

    def test_web_solo_personal_ve_formulario_usuario_solo_consulta(self):
        for numero in (3, 4):
            cliente, token = self.cuenta(numero)
            pagina = cliente.get('/prestamos/1')
            self.assertEqual(pagina.status_code, 200)
            self.assertNotIn(b'formulario-ampliacion', pagina.data)
            self.assertEqual(cliente.post(self.ruta, data=self.datos(token)).status_code, 403)
        encargado, token = self.cuenta(2)
        pagina = encargado.get('/prestamos/1')
        self.assertIn(b'formulario-ampliacion', pagina.data)
        self.assertNotIn(b'Aprobar ampliaci', pagina.data)
        self.assertIn(b'ampliacion.js', pagina.data)
        self.assertEqual(encargado.post(self.ruta, data=self.datos(token)).status_code, 302)
        self.assertEqual(self.detalle()['fecha_limite_devolucion'], self.anterior + timedelta(hours=2))

    def test_web_csrf_datos_invalidos_conflicto_y_permiso_revocado(self):
        cliente, token = self.cuenta(2)
        self.assertEqual(cliente.post(self.ruta, data={'cantidad': '2'}).status_code, 400)
        for cambios in ({'cantidad': '0'}, {'unidad': 'MINUTOS'}, {'fecha_actual': 'invalida'}):
            self.assertEqual(cliente.post(self.ruta, data=self.datos(token, **cambios)).status_code, 400)
        self.assertEqual(cliente.post(self.ruta, data=self.datos(token)).status_code, 302)
        self.assertEqual(cliente.post(self.ruta, data=self.datos(token)).status_code, 409)
        with self.db.sesion(escritura=True) as cursor:
            cursor.execute("DELETE FROM rol_permiso WHERE rol='ENCARGADO_PRESTAMOS' AND permiso='PRESTAMOS_GESTIONAR'")
        with self.assertRaises(PermissionError):
            self.ampliar(fecha=self.detalle()['fecha_limite_devolucion'])
        self.assertEqual(cliente.post(self.ruta, data=self.datos(token)).status_code, 403)

    def test_cuenta_o_persona_inactiva_no_puede_ampliar(self):
        for tabla, campo, valor in (('usuario_sistema', 'estado_cuenta', 'INACTIVA'),
                                    ('persona', 'estado', 'INACTIVA')):
            with self.db.sesion(escritura=True) as cursor:
                cursor.execute(f'UPDATE {tabla} SET {campo}=%s WHERE ' +
                               ('id_usuario=2' if tabla == 'usuario_sistema' else "dni='98000002'"), (valor,))
            with self.assertRaises(PermissionError):
                self.ampliar()
            with self.db.sesion(escritura=True) as cursor:
                cursor.execute(f'UPDATE {tabla} SET {campo}=%s WHERE ' +
                               ('id_usuario=2' if tabla == 'usuario_sistema' else "dni='98000002'"), ('ACTIVA',))
