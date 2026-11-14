import csv
import io
import os
import unittest
from unittest.mock import patch



@unittest.skipUnless(os.environ.get('TEST_MYSQL_PORT'), 'Configura MySQL de pruebas.')
class ReportesTest(unittest.TestCase):
    def setUp(self):
        from soporte_mysql import preparar_base_integracion
        preparar_base_integracion(self, prestamos=True)
        self.servicio = self.app.extensions["reportes"]

    def login(self, usuario='admin', clave='AdminPrueba2026!'):
        client = self.app.test_client()
        client.get('/login')
        with client.session_transaction() as s:
            token = s['csrf_token']
        respuesta = client.post('/login', data=dict(usuario=usuario, clave=clave, csrf_token=token))
        self.assertEqual(respuesta.status_code, 302)
        return client

    def preparar_grupo(self):
        with self.db.sesion(escritura=True) as c:
            c.execute("UPDATE prestamo SET tipo_prestamo='GRUPAL' WHERE id_prestamo=1")
            c.execute("""INSERT INTO participante_prestamo(id_prestamo,dni_persona,responsable)
                         VALUES (1,'02167885',TRUE),(1,'99000001',FALSE),(1,'99000002',FALSE)""")
            c.execute("""INSERT INTO detalle_prestamo(id_prestamo,id_bien,id_politica,fecha_limite_devolucion)
                         VALUES (1,2,24,DATE_ADD(UTC_TIMESTAMP(),INTERVAL 1 DAY))""")
            c.execute("UPDATE bien_material SET estado='PRESTADO' WHERE id_bien=2")

    def test_grupo_no_duplica_bienes_ni_totales_y_se_busca_por_integrante(self):
        self.preparar_grupo()
        resultado = self.servicio.consultar_prestamos({})
        self.assertEqual(resultado['resumen'], dict(prestamos=2, bienes=3, devueltos=1, pendientes=2, vencidos=1))
        self.assertEqual(len({f['id_detalle'] for f in resultado['filas']}), 3)
        grupo = [f for f in resultado['filas'] if f['id_prestamo'] == 1]
        self.assertEqual(len(grupo), 2)
        self.assertTrue(all(len(f['integrantes']) == 3 for f in grupo))
        buscado = self.servicio.consultar_prestamos({'q': '99000002'})
        self.assertEqual(buscado['resumen']['prestamos'], 1)
        self.assertEqual(buscado['resumen']['bienes'], 2)
        self.assertTrue(all(f['id_prestamo'] == 1 for f in buscado['filas']))
        self.assertEqual(self.servicio.consultar_prestamos({'modalidad': 'GRUPAL'})['resumen']['bienes'], 2)

    def test_fechas_inclusivas_en_lima_y_filtros_de_estado_y_persona(self):
        with self.db.sesion(escritura=True) as c:
            c.execute("UPDATE prestamo SET fecha_entrega='2026-11-13 04:59:59' WHERE id_prestamo=1")
            c.execute("UPDATE prestamo SET fecha_entrega='2026-11-13 05:00:00' WHERE id_prestamo=2")
        for dia, esperado in (('2026-11-12', 1), ('2026-11-13', 2)):
            resultado = self.servicio.consultar_prestamos(dict(desde=dia, hasta=dia))
            self.assertEqual([f['id_prestamo'] for f in resultado['filas']], [esperado])
        devueltos = self.servicio.consultar_prestamos({'estado': 'DEVUELTO'})
        self.assertEqual([f['id_prestamo'] for f in devueltos['filas']], [2])
        estudiantes = self.servicio.consultar_prestamos({'tipo_persona': 'ESTUDIANTE'})
        self.assertTrue(estudiantes['filas'])
        self.assertTrue(all(f['tipo_persona'] == 'ESTUDIANTE' for f in estudiantes['filas']))

    def test_paginacion_conserva_totales_y_csv_descarga_todas_las_paginas(self):
        with patch('repositorio.repositorio_reporte_sql.POR_PAGINA', 1):
            primera = self.servicio.consultar_prestamos({})
            segunda = self.servicio.consultar_prestamos({'pagina': '2'})
            self.assertEqual(len(primera['filas']), 1)
            self.assertEqual(primera['resumen']['bienes'], 2)
            self.assertEqual(primera['paginas'], 2)
            self.assertNotEqual(primera['filas'][0]['id_detalle'], segunda['filas'][0]['id_detalle'])
            self.assertEqual(self.servicio.consultar_prestamos({'pagina': '999'})['pagina'], 2)
            csv_completo = self.servicio.exportar_prestamos({'pagina': '2'})
            filas = list(csv.reader(io.StringIO(csv_completo.decode('utf-8-sig')), delimiter=';'))
            self.assertEqual(len(filas), 3)

    def test_permiso_obligatorio_y_revocado_en_pantalla_y_descarga(self):
        anonimo = self.app.test_client()
        usuario = self.login('usuario1', 'UsuarioPrueba2026!')
        encargado = self.login('encargado1', 'EncargadoPrueba2026!')
        admin = self.login()
        for ruta in ('/reportes', '/reportes/prestamos.csv'):
            self.assertEqual(anonimo.get(ruta).status_code, 302)
            self.assertEqual(usuario.get(ruta).status_code, 403)
            self.assertEqual(encargado.get(ruta).status_code, 200)
            self.assertEqual(admin.get(ruta).status_code, 200)
        self.assertIn(b'/reportes', admin.get('/').data)
        with self.db.sesion(escritura=True) as c:
            c.execute("DELETE FROM rol_permiso WHERE rol='ENCARGADO_PRESTAMOS' AND permiso='REPORTES_CONSULTAR'")
        self.assertEqual(encargado.get('/reportes/prestamos.csv').status_code, 403)
        self.assertNotIn(b'href="/reportes"', encargado.get('/').data)

    def test_csv_unicode_fechas_y_textos_que_parecen_formulas(self):
        with self.db.sesion(escritura=True) as c:
            c.execute("UPDATE persona SET nombres=%s WHERE dni='02167885'", ('=SUM(1;2)',))
            c.execute('''UPDATE recurso SET nombre=%s WHERE id_recurso=(
                SELECT b.id_recurso FROM bien_material b JOIN detalle_prestamo d ON d.id_bien=b.id_bien
                WHERE d.id_detalle=1)''', ('  +Libro; edición\nniñez',))
        client = self.login()
        respuesta = client.get('/reportes/prestamos.csv?q=02167885')
        self.assertEqual(respuesta.mimetype, 'text/csv')
        self.assertIn('attachment', respuesta.headers['Content-Disposition'])
        self.assertTrue(respuesta.data.startswith(b'\xef\xbb\xbf'))
        filas = list(csv.reader(io.StringIO(respuesta.data.decode('utf-8-sig')), delimiter=';'))
        self.assertEqual(len(filas), 2)
        self.assertEqual(filas[1][4], '02167885')
        self.assertTrue(filas[1][3].startswith("'="))
        self.assertEqual(filas[1][9], '30/10/2026 11:38')
        self.assertTrue(filas[1][8].startswith("'  +"))
        self.assertIn('niñez', filas[1][8])

    def test_filtros_invalidos_y_sin_resultados(self):
        client = self.login()
        invalidos = ('desde=2026-02-30', 'desde=2026-12-02&hasta=2026-11-01',
                     'hasta=9999-12-31', 'estado=INVENTADO', 'modalidad=OTRA',
                     'tipo_persona=OTRA', 'pagina=0', 'q=' + 'a' * 121)
        for filtro in invalidos:
            for ruta in ('/reportes?', '/reportes/prestamos.csv?'):
                with self.subTest(ruta=ruta, filtro=filtro):
                    self.assertEqual(client.get(ruta + filtro).status_code, 400)
        resultado = self.servicio.consultar_prestamos({'q': 'recurso_inexistente_987654'})
        self.assertEqual(resultado['resumen'], dict(prestamos=0, bienes=0, devueltos=0, pendientes=0, vencidos=0))
        self.assertEqual(resultado['filas'], [])
        csv_vacio = self.servicio.exportar_prestamos({'q': 'recurso_inexistente_987654'})
        self.assertEqual(len(list(csv.reader(io.StringIO(csv_vacio.decode('utf-8-sig')), delimiter=';'))), 1)

    def test_consultar_y_exportar_no_modifica_los_registros(self):
        client = self.login()

        def registros():
            resultado = {}
            with self.db.sesion() as c:
                for tabla in ('prestamo', 'detalle_prestamo', 'historial_estado', 'incidencia', 'sancion'):
                    c.execute('SELECT * FROM ' + tabla + ' ORDER BY 1')
                    resultado[tabla] = c.fetchall()
            return resultado

        antes = registros()
        self.assertEqual(client.get('/reportes').status_code, 200)
        self.assertEqual(client.get('/reportes/prestamos.csv').status_code, 200)
        self.assertEqual(registros(), antes)
