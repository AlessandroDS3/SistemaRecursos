import csv
from datetime import timedelta, timezone
from html import unescape
from io import StringIO
import re
import unittest
from urllib.parse import parse_qs, urlsplit

from caso_mysql import CasoMySQL
from dominio.compartido.validacion import LIMA
from dominio.gestion_control.catalogo_reportes import REPORTES
from dominio.gestion_control.reporte import FiltroReporte


class FiltrosReportes(unittest.TestCase):
    def test_cada_reporte_valida_sus_estados_y_descarta_filtros_ajenos(self):
        for tipo, definicion in REPORTES.items():
            with self.subTest(tipo=tipo):
                for estado in definicion.estados:
                    self.assertEqual(FiltroReporte(tipo=tipo, estado=estado).estado, estado)
                if definicion.estados:
                    with self.assertRaises(ValueError):
                        FiltroReporte(tipo=tipo, estado='INEXISTENTE')
        filtro = FiltroReporte(
            tipo='inventario', desde='incorrecta', modalidad='AJENA', estado='DANADO'
        )
        self.assertIsNone(filtro.desde)
        self.assertEqual(filtro.modalidad, '')
        self.assertEqual(filtro.parametros, {'tipo': 'inventario', 'estado': 'DANADO'})
        for datos in (
            {'tipo': 'otro'},
            {'tipo': 'uso_recursos'},
            {'id_categoria': '-1'},
            {'tipo': 'devoluciones', 'cumplimiento': 'OTRO'},
        ):
            with self.subTest(datos=datos), self.assertRaises(ValueError):
                FiltroReporte(**datos)

    def test_fechas_y_enlaces_conservan_el_dia_local_y_los_filtros_activos(self):
        filtro = FiltroReporte(
            tipo='reservas',
            desde='2026-11-14',
            hasta='2026-11-14',
            id_categoria='1',
            tipo_gestion='RESERVA',
        )
        self.assertEqual(filtro.inicio.isoformat(), '2026-11-14T05:00:00')
        self.assertEqual(filtro.fin.isoformat(), '2026-11-15T05:00:00')
        self.assertEqual(filtro.parametros['desde'], '2026-11-14')
        self.assertEqual(filtro.parametros['id_categoria'], 1)
        self.assertNotIn('pagina', filtro.parametros)


class ReportesAmpliados(CasoMySQL):
    def reporte(self, tipo, **filtros):
        return self.servicios['reportes'].consultar_reportes(dict(tipo=tipo, **filtros))

    def test_devoluciones_clasifica_limite_exacto_tardia_y_calcula_porcentajes(self):
        prestamo = self.prestar([2, 3])
        detalles = self.prestamo(prestamo)['detalles']
        for detalle, devolucion in zip(detalles, ('2026-11-14 17:00:00', '2026-11-14 18:30:00')):
            self.ejecutar(
                """UPDATE detalle_prestamo SET fecha_limite_devolucion='2026-11-14 17:00:00',
                fecha_devolucion=%s,dni_encargado_devolucion='98000002',condicion_devolucion='BUENO'
                WHERE id_detalle=%s""",
                (devolucion, detalle['id_detalle']),
            )
        resultado = self.reporte('devoluciones', desde='2026-11-14', hasta='2026-11-14')
        self.assertEqual(resultado['resumen']['puntuales'], 1)
        self.assertEqual(resultado['resumen']['tardias'], 1)
        self.assertEqual(resultado['resumen']['porcentaje_puntual'], 50)
        self.assertEqual(resultado['resumen']['retraso_promedio'], 90)
        self.assertEqual({f['cumplimiento'] for f in resultado['filas']}, {'A_TIEMPO', 'TARDIA'})
        tardias = self.reporte('devoluciones', cumplimiento='TARDIA')
        self.assertEqual(tardias['resumen']['detalles'], 1)
        self.assertEqual(tardias['filas'][0]['retraso_minutos'], 90)

    def test_atrasados_excluye_bienes_vigentes_y_devueltos_del_mismo_prestamo(self):
        prestamo = self.prestar(
            [2, 3], tipo_prestamo='GRUPAL', participantes=['99000001', '99000002']
        )
        limite = self.consultar_fecha_actual - timedelta(days=2)
        self.ejecutar(
            'UPDATE detalle_prestamo SET fecha_limite_devolucion=%s WHERE id_prestamo=%s AND id_bien=2',
            (limite, prestamo),
        )
        self.ejecutar(
            'UPDATE detalle_prestamo SET fecha_limite_devolucion=DATE_ADD(UTC_TIMESTAMP(),INTERVAL 5 DAY) WHERE id_prestamo=%s AND id_bien=3',
            (prestamo,),
        )
        self.ejecutar(
            """INSERT INTO detalle_prestamo(id_prestamo,id_bien,id_politica,fecha_limite_devolucion,
            fecha_devolucion,dni_encargado_devolucion,condicion_devolucion)
            VALUES(%s,1,24,%s,UTC_TIMESTAMP(),'98000002','BUENO')""",
            (prestamo, limite),
        )
        dia = limite.replace(tzinfo=timezone.utc).astimezone(LIMA).date().isoformat()
        resultado = self.reporte('atrasados', q='99000001', desde=dia, hasta=dia)
        self.assertEqual(resultado['resumen']['detalles'], 1)
        self.assertEqual(resultado['filas'][0]['codigo_inventario'], 'INV-2')
        self.assertGreater(resultado['filas'][0]['retraso_minutos'], 0)
        texto, _ = self.servicios['reportes'].exportar_reportes_csv(
            dict(tipo='atrasados', q='99000001', desde=dia, hasta=dia)
        )
        csv_filas = list(csv.reader(StringIO(texto.lstrip('\ufeff')), delimiter=';'))
        self.assertEqual(
            csv_filas[0],
            [
                'id_prestamo',
                'dni_persona',
                'solicitante',
                'codigo_inventario',
                'recurso',
                'fecha_entrega',
                'fecha_limite_devolucion',
                'retraso_minutos',
            ],
        )
        self.assertEqual(len(csv_filas), 2)
        self.assertEqual(csv_filas[1][3], 'INV-2')

    def test_inventario_filtra_categoria_estado_ubicacion_y_marca(self):
        self.ejecutar("INSERT INTO categoria_recurso VALUES(2,'Otros',NULL)")
        self.ejecutar(
            "INSERT INTO recurso(id_recurso,id_categoria,nombre,marca) VALUES(3,2,'Otro equipo','Marca especial')"
        )
        self.ejecutar(
            "INSERT INTO bien_material(id_recurso,codigo_inventario,estado,ubicacion) VALUES(3,'OTRO-1','DANADO','Sala A')"
        )
        self.ejecutar("UPDATE bien_material SET ubicacion='Sala A' WHERE id_bien=2")
        resultado = self.reporte(
            'inventario', id_categoria='1', estado='DISPONIBLE', ubicacion='Sala A'
        )
        self.assertEqual(resultado['resumen']['detalles'], 1)
        self.assertEqual(resultado['resumen']['disponibles'], 1)
        self.assertEqual(resultado['filas'][0]['codigo_inventario'], 'INV-2')
        resultado = self.reporte('inventario', q='Marca especial')
        self.assertEqual(resultado['resumen']['danados'], 1)
        self.assertEqual(resultado['filas'][0]['codigo_inventario'], 'OTRO-1')

    def test_estado_filtra_el_prestamo_completo_y_no_la_situacion_de_cada_bien(self):
        prestamo = self.prestar([2, 3])
        self.ejecutar(
            '''UPDATE detalle_prestamo
            SET fecha_limite_devolucion=DATE_SUB(UTC_TIMESTAMP(),INTERVAL 1 DAY)
            WHERE id_prestamo=%s AND id_bien=2''',
            (prestamo,),
        )
        self.ejecutar(
            '''UPDATE detalle_prestamo SET fecha_devolucion=UTC_TIMESTAMP(),
            dni_encargado_devolucion='98000002',condicion_devolucion='BUENO'
            WHERE id_prestamo=%s AND id_bien=3''',
            (prestamo,),
        )
        filas = self.reporte('prestamos', estado='VENCIDO')['filas']
        self.assertEqual({f['situacion'] for f in filas}, {'VENCIDO', 'DEVUELTO'})
        self.assertEqual(self.reporte('prestamos', estado='DEVUELTO')['resumen']['detalles'], 0)
        filas = self.reporte('devoluciones', estado='VENCIDO')['filas']
        self.assertEqual([f['codigo_inventario'] for f in filas], ['INV-3'])

    def test_devolucion_tardia_de_segundos_conserva_clasificacion_con_minutos_enteros(self):
        prestamo = self.prestar()
        self.ejecutar(
            '''UPDATE detalle_prestamo SET fecha_limite_devolucion='2026-11-14 17:00:00',
            fecha_devolucion='2026-11-14 17:00:30',dni_encargado_devolucion='98000002',
            condicion_devolucion='BUENO' WHERE id_prestamo=%s''',
            (prestamo,),
        )
        resultado = self.reporte('devoluciones', cumplimiento='TARDIA')
        self.assertEqual(resultado['filas'][0]['cumplimiento'], 'TARDIA')
        self.assertEqual(resultado['filas'][0]['retraso_minutos'], 0)
        self.assertEqual(resultado['resumen']['tardias'], 1)
        self.assertEqual(resultado['resumen']['porcentaje_puntual'], 0)
        self.assertEqual(resultado['resumen']['retraso_promedio'], 0)

    def test_reservas_resume_estados_y_filtra_tipo_gestion(self):
        for indice, estado in enumerate(REPORTES['reservas'].estados):
            self.ejecutar(
                """INSERT INTO reserva(dni_persona,id_recurso,fecha_solicitud,fecha_requerida,tipo_gestion,estado)
                VALUES('02167885',1,'2026-11-14 15:00','2026-11-15 15:00',%s,%s)""",
                ('PRESTAMO' if indice % 2 == 0 else 'RESERVA', estado),
            )
        resultado = self.reporte('reservas', desde='2026-11-14', hasta='2026-11-14')
        self.assertEqual(
            resultado['resumen'],
            dict(detalles=6, pendientes=2, atendidas=1, canceladas=1, rechazadas=1, expiradas=1),
        )
        resultado = self.reporte(
            'reservas',
            estado='EXPIRADA',
            tipo_gestion='PRESTAMO',
            tipo_persona='ESTUDIANTE',
            id_categoria='1',
        )
        self.assertEqual(resultado['resumen']['detalles'], 1)
        self.assertEqual(resultado['filas'][0]['estado'], 'EXPIRADA')
        self.assertEqual(self.reporte('reservas', tipo_persona='DOCENTE')['resumen']['detalles'], 0)

    def test_sanciones_grupales_no_duplican_filas_y_muestran_levantamientos(self):
        prestamo = self.prestar(
            [2, 3], tipo_prestamo='GRUPAL', participantes=['99000001', '99000002']
        )
        self.ejecutar(
            'UPDATE detalle_prestamo SET fecha_limite_devolucion=%s WHERE id_prestamo=%s',
            (self.consultar_fecha_actual - timedelta(days=2), prestamo),
        )
        self.assertEqual(self.servicios['sanciones'].aplicar_sanciones_por_vencimiento(), 2)
        sancion = self.fila('SELECT MIN(id_sancion) FROM sancion')[0]
        self.servicios['sanciones'].levantar_sancion(sancion, 'Justificación de prueba', 1)
        resultado = self.reporte('sanciones', q='99000002', modalidad='GRUPAL')
        self.assertEqual(resultado['resumen']['detalles'], 2)
        self.assertEqual(resultado['resumen']['activas'], 1)
        self.assertEqual(resultado['resumen']['levantadas'], 1)
        self.assertTrue(all('99000001' in f['integrantes'] for f in resultado['filas']))
        resultado = self.reporte('sanciones', estado='LEVANTADA')
        self.assertEqual(
            resultado['filas'][0]['justificacion_levantamiento'], 'Justificación de prueba'
        )

    def test_danos_perdidas_conserva_eventos_de_bienes_recuperados(self):
        for bien, estado in ((2, 'DANADO'), (3, 'PERDIDO')):
            for anterior, nuevo in (('DISPONIBLE', estado), (estado, 'DISPONIBLE')):
                self.servicios['bienes'].cambiar_estado_bien_material(
                    bien, dict(estado=nuevo, estado_esperado=anterior, motivo='Evento de prueba'), 1
                )
        resultado = self.reporte('danos_perdidas', q='98000001')
        self.assertEqual(resultado['resumen'], dict(detalles=2, bienes=2, danos=1, perdidas=1))
        self.assertTrue(all(f['estado_actual'] == 'DISPONIBLE' for f in resultado['filas']))
        self.assertTrue(all(f['registrador'] == 'Administrador Prueba' for f in resultado['filas']))
        self.assertEqual(self.reporte('danos_perdidas', estado='PERDIDO')['resumen']['detalles'], 1)

    def test_pantallas_y_exportaciones_de_los_siete_reportes_son_solo_lectura(self):
        self.prestar()
        self.login()
        antes = self.fila('SELECT COUNT(*) FROM historial_estado')
        for tipo, definicion in REPORTES.items():
            with self.subTest(tipo=tipo):
                respuesta = self.cliente.get('/reportes', query_string={'tipo': tipo})
                self.assertEqual(respuesta.status_code, 200)
                pagina = respuesta.get_data(as_text=True)
                self.assertIn(definicion.titulo, pagina)
                self.assertEqual('name="desde"' in pagina, bool(definicion.fecha))
                csv_http = self.cliente.get('/reportes/exportar.csv', query_string={'tipo': tipo})
                self.assertEqual(csv_http.status_code, 200)
                filas = list(
                    csv.DictReader(
                        StringIO(csv_http.get_data(as_text=True).lstrip('\ufeff')), delimiter=';'
                    )
                )
                resultado = self.reporte(tipo)
                self.assertEqual(len(filas), resultado['resumen']['detalles'])
                pdf_http = self.cliente.get('/reportes/exportar.pdf', query_string={'tipo': tipo})
                self.assertEqual(pdf_http.status_code, 200)
                self.assertEqual(pdf_http.mimetype, 'application/pdf')
                self.assertTrue(pdf_http.data.startswith(b'%PDF-'))
        self.assertEqual(self.fila('SELECT COUNT(*) FROM historial_estado'), antes)
        pagina = self.cliente.get('/reportes?tipo=inventario').get_data(as_text=True)
        selector = re.search(r'<select name="tipo"[^>]*>(.*?)</select>', pagina, re.S).group(1)
        self.assertEqual(len(re.findall('<option ', selector)), 7)

    def test_pantalla_y_exportacion_conservan_filtros_y_muestran_inventario_completo(self):
        for numero in range(52):
            self.ejecutar(
                "INSERT INTO bien_material(id_recurso,codigo_inventario,ubicacion) VALUES(2,%s,'Sala B')",
                (f'PAG-{numero:03}',),
            )
        resultado = self.reporte('inventario', ubicacion='Sala B', id_categoria='1', pagina='999')
        self.assertEqual(len(resultado['filas']), 52)
        self.assertNotIn('paginas', resultado)
        texto, _ = self.servicios['reportes'].exportar_reportes_csv(
            dict(tipo='inventario', ubicacion='Sala B', id_categoria='1', pagina='2')
        )
        self.assertEqual(
            len(list(csv.DictReader(StringIO(texto.lstrip('\ufeff')), delimiter=';'))), 52
        )
        self.login()
        pagina = self.cliente.get(
            '/reportes?tipo=inventario&ubicacion=Sala+B&id_categoria=1'
        ).get_data(as_text=True)
        self.assertIn('PAG-000', pagina)
        self.assertIn('PAG-051', pagina)
        self.assertNotIn('acciones paginacion', pagina)
        enlaces = [urlsplit(unescape(e)) for e in re.findall(r'href="([^"]+)"', pagina)]
        exportacion = next(e for e in enlaces if e.path == '/reportes/exportar.csv')
        self.assertEqual(parse_qs(exportacion.query)['ubicacion'], ['Sala B'])
        self.assertEqual(parse_qs(exportacion.query)['id_categoria'], ['1'])

    def test_reportes_rechazan_usuario_sin_permiso_y_filtros_invalidos(self):
        self.login('usuario1', 'UsuarioPrueba2026!')
        for tipo in REPORTES:
            for ruta in ('/reportes', '/reportes/exportar.csv', '/reportes/exportar.pdf'):
                with self.subTest(tipo=tipo, ruta=ruta):
                    self.assertEqual(
                        self.cliente.get(ruta, query_string={'tipo': tipo}).status_code, 403
                    )
        self.post('/logout')
        self.login()
        for filtros in (
            {'tipo': 'ajeno'},
            {'tipo': 'uso_recursos'},
            {'tipo': 'sanciones', 'estado': 'VENCIDO'},
            {'tipo': 'inventario', 'id_categoria': '1 OR 1=1'},
            {'tipo': 'reservas', 'desde': 'mal'},
        ):
            for ruta in ('/reportes', '/reportes/exportar.csv', '/reportes/exportar.pdf'):
                with self.subTest(filtros=filtros, ruta=ruta):
                    self.assertEqual(
                        self.cliente.get(ruta, query_string=filtros).status_code, 400
                    )
