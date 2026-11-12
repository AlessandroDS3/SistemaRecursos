from datetime import datetime, timedelta
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

from dominio.gestion_control.horario_atencion import HorarioAtencion, ZONA_INSTITUCION
from dominio.gestion_control.politica_prestamo import PoliticaPrestamo
from dominio.gestion_prestamos.ampliacion_prestamo import AmpliacionPrestamo, ConflictoAmpliacionError


class AmpliacionDominioTest(unittest.TestCase):
    def setUp(self):
        self.ahora = datetime(2026, 11, 12, 14)
        self.anterior = self.ahora + timedelta(days=1)
        self.politica = PoliticaPrestamo(tipo_persona='ESTUDIANTE', id_categoria=1,
                                       plazo_maximo=2, unidad_plazo='DIAS')

    def solicitud(self, fecha):
        return AmpliacionPrestamo(id_detalle=1, fecha_limite_nueva=fecha, motivo='Completar práctica')

    def test_limite_de_otro_plazo_y_fecha_posterior(self):
        self.solicitud(self.anterior + timedelta(days=2)).validar_plazo(self.anterior, self.ahora, self.politica)
        for fecha in (self.anterior, self.anterior - timedelta(minutes=1), self.anterior + timedelta(days=2, minutes=1)):
            with self.subTest(fecha=fecha), self.assertRaises(ValueError):
                self.solicitud(fecha).validar_plazo(self.anterior, self.ahora, self.politica)

    def test_horas_respetan_el_cierre(self):
        politica = PoliticaPrestamo(tipo_persona='ESTUDIANTE', id_categoria=1,
                                   plazo_maximo=4, unidad_plazo='HORAS')
        anterior = datetime(2026, 11, 12, 20)  # 15:00 en Lima.
        horario = HorarioAtencion()
        self.solicitud(datetime(2026, 11, 12, 21)).validar_plazo(anterior, self.ahora, politica, horario)
        with self.assertRaises(ValueError):
            self.solicitud(datetime(2026, 11, 12, 21, 1)).validar_plazo(anterior, self.ahora, politica, horario)

    def test_vencido_y_solicitud_desactualizada_no_se_aprueban(self):
        with self.assertRaises(ConflictoAmpliacionError):
            self.solicitud(self.anterior).validar_plazo(self.ahora, self.ahora, self.politica)
        solicitud = self.solicitud(self.anterior + timedelta(days=1))
        solicitud.fecha_limite_anterior = self.anterior
        with self.assertRaises(ConflictoAmpliacionError):
            solicitud.validar_plazo(self.anterior + timedelta(hours=1), self.ahora, self.politica)

    def test_resolucion_unica_y_motivo_de_rechazo(self):
        solicitud = self.solicitud(self.anterior)
        with self.assertRaises(ValueError):
            solicitud.rechazar(2, self.ahora, '')
        solicitud.rechazar(2, self.ahora, 'El bien tiene otra reserva')
        self.assertEqual(solicitud.estado, 'RECHAZADA')
        self.assertEqual(solicitud.id_usuario_resolucion, 2)
        with self.assertRaises(ConflictoAmpliacionError):
            solicitud.aprobar(2, self.ahora)


@unittest.skipUnless(os.environ.get('TEST_MYSQL_PORT'), 'Configura MySQL de pruebas.')
class AmpliacionIntegracionTest(unittest.TestCase):
    def setUp(self):
        import mysql.connector
        from werkzeug.security import generate_password_hash
        from app import create_app
        from repositorio.conexion_mysql import MySQLConnection

        cfg = dict(host='127.0.0.1', port=int(os.environ['TEST_MYSQL_PORT']),
                   user=os.environ.get('TEST_MYSQL_USER', 'root'),
                   password=os.environ.get('TEST_MYSQL_PASSWORD', ''), use_pure=True, connection_timeout=5)
        self.nombre = 'test_ampliacion_' + uuid4().hex
        self.cn = mysql.connector.connect(**cfg)
        self.addCleanup(self.cn.close)
        self.c = self.cn.cursor(buffered=True)
        self.addCleanup(self.c.close)
        self.addCleanup(self.c.execute, f'DROP DATABASE IF EXISTS {self.nombre}')
        schema = (Path(__file__).resolve().parents[1] / 'sql/schema.sql').read_text(encoding='utf-8-sig')
        self.c.execute(schema.replace('prestamos_escuela', self.nombre))
        while self.c.nextset():
            pass
        personas = [('98000001', 'Admin'), ('98000002', 'Encargado'), ('99000001', 'Responsable'),
                    ('99000002', 'Integrante'), ('99000003', 'Otra persona')]
        self.c.executemany('INSERT INTO persona(dni,nombres,apellidos,correo) VALUES(%s,%s,%s,%s)',
                          [(dni, nombre, 'Prueba', dni + '@ejemplo.com') for dni, nombre in personas])
        self.c.executemany('INSERT INTO administrativo(dni,codigo_empleado,area) VALUES(%s,%s,%s)',
                          [(dni, dni, 'Préstamos') for dni, _ in personas[:2]])
        self.c.executemany('INSERT INTO estudiante(dni,cui) VALUES(%s,%s)',
                          [(dni, dni) for dni, _ in personas[2:]])
        roles = ['ADMINISTRADOR', 'ENCARGADO_PRESTAMOS', 'USUARIO', 'USUARIO', 'USUARIO']
        self.clave = 'ClavePrueba2026!'
        clave_hash = generate_password_hash(self.clave, method='scrypt')
        self.c.executemany('''INSERT INTO usuario_sistema(id_usuario,dni_persona,nombre_usuario,contrasena_hash,rol)
            VALUES(%s,%s,%s,%s,%s)''', [(i, dni, 'cuenta' + str(i), clave_hash, rol)
                for i, ((dni, _), rol) in enumerate(zip(personas, roles), 1)])
        permisos = [(rol, permiso) for rol in set(roles)
                    for permiso in ('PRESTAMOS_PROPIOS_CONSULTAR', 'AMPLIACIONES_SOLICITAR')]
        permisos += [(rol, 'PRESTAMOS_GESTIONAR') for rol in roles[:2]]
        self.c.executemany('INSERT INTO rol_permiso(rol,permiso) VALUES(%s,%s)', permisos)
        self.c.execute("INSERT INTO categoria_recurso(id_categoria,nombre) VALUES(1,'Libros')")
        self.c.execute("INSERT INTO recurso(id_recurso,id_categoria,nombre) VALUES(1,1,'Libro de práctica')")
        self.c.execute("INSERT INTO bien_material(id_bien,id_recurso,codigo_inventario,estado) VALUES(1,1,'LIB-001','PRESTADO')")
        self.c.execute("INSERT INTO politica_prestamo(id_politica,tipo_persona,id_categoria,plazo_maximo,unidad_plazo) VALUES(1,'ESTUDIANTE',1,2,'DIAS')")
        self.c.execute("INSERT INTO configuracion_general VALUES(1,'08:00','16:00',2,'DIAS',24,'HORAS')")
        self.c.execute("""INSERT INTO prestamo(id_prestamo,dni_persona,dni_encargado,tipo_prestamo,fecha_solicitud,fecha_entrega)
            VALUES(1,'99000001','98000002','GRUPAL',UTC_TIMESTAMP(),UTC_TIMESTAMP())""")
        self.c.execute("INSERT INTO participante_prestamo(id_prestamo,dni_persona,responsable) VALUES(1,'99000001',TRUE),(1,'99000002',FALSE)")
        self.c.execute("""INSERT INTO detalle_prestamo(id_detalle,id_prestamo,id_bien,id_politica,fecha_limite_devolucion)
            VALUES(1,1,1,1,DATE_FORMAT(DATE_ADD(UTC_TIMESTAMP(),INTERVAL 1 DAY),'%Y-%m-%d %H:%i:00'))""")
        self.cn.commit()
        self.db = MySQLConnection(dict(cfg, database=self.nombre))
        self.app = create_app({'TESTING': True, 'MYSQL_CONFIG': self.db.config, 'INICIAR_PROCESADOR_VENCIMIENTOS': False})
        self.servicio = self.app.extensions['ampliaciones']
        self.anterior = self.detalle()['fecha_limite_devolucion']
        self.nueva = self.anterior + timedelta(days=1)

    def detalle(self):
        with self.db.sesion() as cursor:
            cursor.execute('SELECT * FROM detalle_prestamo WHERE id_detalle=1')
            return cursor.fetchone()

    def fecha_formulario(self, fecha=None):
        from datetime import timezone
        return (fecha or self.nueva).replace(tzinfo=timezone.utc).astimezone(ZONA_INSTITUCION).strftime('%Y-%m-%dT%H:%M')

    def solicitar(self, dni='99000001', fecha=None):
        return self.servicio.solicitar_ampliacion(1, 1, self.fecha_formulario(fecha), 'Completar la práctica', dni)

    def cuenta(self, numero):
        client = self.app.test_client()
        client.get('/login')
        with client.session_transaction() as session:
            token = session['csrf_token']
        response = client.post('/login', data=dict(usuario='cuenta' + str(numero), clave=self.clave, csrf_token=token))
        self.assertEqual(response.status_code, 302)
        client.get('/')
        with client.session_transaction() as session:
            token = session['csrf_token']
        return client, token

    def test_solicitar_y_aprobar_cambia_solo_el_detalle_y_guarda_al_encargado(self):
        solicitud = self.solicitar()
        self.assertEqual(self.detalle()['fecha_limite_devolucion'], self.anterior)
        aprobada = self.servicio.aprobar_ampliacion(1, solicitud.id_ampliacion, 2, 'Uso académico')
        self.assertEqual(self.detalle()['fecha_limite_devolucion'], self.nueva)
        self.assertEqual(aprobada.estado, 'APROBADA')
        fila = self.servicio.consultar_ampliaciones(1)[0]
        self.assertEqual(fila['id_usuario_resolucion'], 2)
        self.assertEqual(fila['observacion_resolucion'], 'Uso académico')
        self.assertNotIn('dni_solicitante', fila)
        with self.db.sesion() as cursor:
            cursor.execute("SELECT COUNT(*) AS n FROM historial_estado WHERE entidad='PRESTAMO' AND id_entidad=1")
            self.assertEqual(cursor.fetchone()['n'], 2)

    def test_integrante_y_otro_usuario_no_pueden_solicitar(self):
        for dni in ('99000002', '99000003'):
            with self.subTest(dni=dni), self.assertRaises(PermissionError):
                self.solicitar(dni)

    def test_fecha_limite_duplicados_y_resolucion_repetida(self):
        with self.assertRaises(ValueError):
            self.solicitar(fecha=self.anterior + timedelta(days=2, minutes=1))
        solicitud = self.solicitar()
        with self.assertRaises(ConflictoAmpliacionError):
            self.solicitar()
        self.servicio.aprobar_ampliacion(1, solicitud.id_ampliacion, 1)
        with self.assertRaises(ConflictoAmpliacionError):
            self.servicio.aprobar_ampliacion(1, solicitud.id_ampliacion, 2)

    def test_rechazar_no_cambia_la_fecha_y_permite_otra_solicitud(self):
        solicitud = self.solicitar()
        with self.assertRaises(ValueError):
            self.servicio.rechazar_ampliacion(1, solicitud.id_ampliacion, 2, '')
        rechazada = self.servicio.rechazar_ampliacion(1, solicitud.id_ampliacion, 2, 'Otra persona necesita el bien')
        self.assertEqual(rechazada.estado, 'RECHAZADA')
        self.assertEqual(self.detalle()['fecha_limite_devolucion'], self.anterior)
        self.assertNotEqual(self.solicitar().id_ampliacion, solicitud.id_ampliacion)

    def test_aprobacion_revalida_permiso_estado_y_fecha_vigentes(self):
        solicitud = self.solicitar()
        with self.assertRaises(PermissionError):
            self.servicio.aprobar_ampliacion(1, solicitud.id_ampliacion, 3)
        with self.db.sesion(escritura=True) as cursor:
            cursor.execute('UPDATE detalle_prestamo SET fecha_limite_devolucion=DATE_SUB(UTC_TIMESTAMP(),INTERVAL 1 MINUTE) WHERE id_detalle=1')
        with self.assertRaises(ConflictoAmpliacionError):
            self.servicio.aprobar_ampliacion(1, solicitud.id_ampliacion, 2)
        self.assertEqual(self.servicio.consultar_ampliaciones(1)[0]['estado'], 'PENDIENTE')

    def test_devolucion_o_perdida_impiden_aprobar(self):
        solicitud = self.solicitar()
        with self.db.sesion(escritura=True) as cursor:
            cursor.execute("UPDATE bien_material SET estado='PERDIDO' WHERE id_bien=1")
        with self.assertRaises(ConflictoAmpliacionError):
            self.servicio.aprobar_ampliacion(1, solicitud.id_ampliacion, 2)
        with self.db.sesion(escritura=True) as cursor:
            cursor.execute("UPDATE bien_material SET estado='DISPONIBLE' WHERE id_bien=1")
            cursor.execute("UPDATE detalle_prestamo SET fecha_devolucion=UTC_TIMESTAMP(),dni_encargado_devolucion='98000002',condicion_devolucion='BUENO' WHERE id_detalle=1")
        with self.assertRaises(ConflictoAmpliacionError):
            self.servicio.aprobar_ampliacion(1, solicitud.id_ampliacion, 2)

    def test_error_al_guardar_historial_revierte_toda_la_aprobacion(self):
        solicitud = self.solicitar()
        with patch.object(self.servicio.repositorio, '_historial', side_effect=RuntimeError('Fallo simulado')):
            with self.assertRaises(RuntimeError):
                self.servicio.aprobar_ampliacion(1, solicitud.id_ampliacion, 2)
        self.assertEqual(self.detalle()['fecha_limite_devolucion'], self.anterior)
        self.assertEqual(self.servicio.consultar_ampliaciones(1)[0]['estado'], 'PENDIENTE')

    def test_web_responsable_solicita_encargado_aprueba_y_grupo_consulta(self):
        responsable, token = self.cuenta(3)
        pagina = responsable.get('/prestamos/1')
        self.assertEqual(pagina.status_code, 200)
        self.assertIn(b'Solicitar ampliaci', pagina.data)
        ruta = '/prestamos/1/detalles/1/ampliaciones'
        self.assertEqual(responsable.post(ruta, data={'motivo': 'Sin CSRF'}).status_code, 400)
        respuesta = responsable.post(ruta, data=dict(csrf_token=token, motivo='Completar práctica', fecha_limite_nueva=self.fecha_formulario()))
        self.assertEqual(respuesta.status_code, 302)
        identificador = self.servicio.consultar_ampliaciones(1)[0]['id_ampliacion']
        integrante, token_integrante = self.cuenta(4)
        self.assertEqual(integrante.get('/prestamos/1').status_code, 200)
        self.assertNotIn(b'<summary>Solicitar ampliaci', integrante.get('/prestamos/1').data)
        self.assertEqual(integrante.post(ruta, data=dict(csrf_token=token_integrante, motivo='No responsable', fecha_limite_nueva=self.fecha_formulario())).status_code, 403)
        encargado, token_encargado = self.cuenta(2)
        self.assertIn(b'Aprobar ampliaci', encargado.get('/prestamos/1').data)
        respuesta = encargado.post(f'/prestamos/1/ampliaciones/{identificador}/aprobar', data=dict(csrf_token=token_encargado))
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.detalle()['fecha_limite_devolucion'], self.nueva)

    def test_web_permiso_revocado_fecha_invalida_y_prestamo_ajeno(self):
        responsable, token = self.cuenta(3)
        ruta = '/prestamos/1/detalles/1/ampliaciones'
        self.assertEqual(responsable.post(ruta, data=dict(csrf_token=token, motivo='Prueba', fecha_limite_nueva='no-es-fecha')).status_code, 400)
        self.assertEqual(responsable.post('/prestamos/2/detalles/1/ampliaciones', data=dict(csrf_token=token, motivo='Prueba', fecha_limite_nueva=self.fecha_formulario())).status_code, 404)
        with self.db.sesion(escritura=True) as cursor:
            cursor.execute("DELETE FROM rol_permiso WHERE rol='USUARIO' AND permiso='AMPLIACIONES_SOLICITAR'")
        self.assertEqual(responsable.post(ruta, data=dict(csrf_token=token, motivo='Prueba', fecha_limite_nueva=self.fecha_formulario())).status_code, 403)
