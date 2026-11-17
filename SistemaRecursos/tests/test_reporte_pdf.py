import csv
from datetime import datetime, timezone
from html import unescape
from io import BytesIO, StringIO
import re
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

from flask import Flask, g
from pypdf import PdfReader

from dominio.gestion_control.catalogo_reportes import REPORTES
from dominio.gestion_control.reporte import FiltroReporte, IRepositorioReporte
from presentacion.controladores.controlador_reporte import ControladorReporte
from presentacion.pdf_reportes import generar_pdf_reporte
from servicios.servicio_reporte import ServicioAplicacionReporte


def fila_reporte(tipo, numero=1):
    valores = dict(
        dni_persona='02167885',
        solicitante='María Núñez',
        tipo_prestamo='GRUPAL',
        integrantes='José Pérez (99000001)',
        codigo_inventario=f'INV-{numero:04}',
        recurso='Proyector & pantalla',
        categoria='Equipos',
        situacion='PENDIENTE',
        cumplimiento='A_TIEMPO',
        condicion_devolucion='BUENO',
        retraso_minutos=90,
        tipo_gestion='RESERVA',
        estado='DISPONIBLE',
        ubicacion='Sala A',
        marca='Marca',
        modelo='Modelo',
        numero_serie='SER-123',
        motivo='Retraso',
        descripcion='Descripción',
        justificacion_levantamiento='Justificación',
        tipo_evento='DANADO',
        estado_actual='DISPONIBLE',
        dni_registrador='98000001',
        registrador='Operador Prueba',
        observacion='Daño registrado',
    )
    fila = {}
    for campo in REPORTES[tipo].columnas:
        if campo.nombre.startswith('id_'):
            fila[campo.nombre] = numero
        elif campo.nombre.startswith('fecha'):
            fila[campo.nombre] = datetime(2026, 11, 17, 15)
        else:
            fila[campo.nombre] = valores[campo.nombre]
    return fila


class ReportePDF(unittest.TestCase):
    def test_siete_reportes_contienen_titulo_fecha_tabla_y_valores_legibles(self):
        for tipo, definicion in REPORTES.items():
            with self.subTest(tipo=tipo):
                contenido = generar_pdf_reporte(
                    FiltroReporte(tipo=tipo),
                    [fila_reporte(tipo)],
                    generado_en=datetime(2026, 11, 17, 15, 30, tzinfo=timezone.utc),
                )
                pdf = PdfReader(BytesIO(contenido))
                texto = '\n'.join(p.extract_text() for p in pdf.pages)
                titulo = 'Bienes prestados' if tipo == 'prestamos' else definicion.titulo
                self.assertIn(titulo, texto)
                self.assertIn('Fecha: 17/11/2026 10:30 (Lima)', texto)
                self.assertIn('Proyector & pantalla', ' '.join(texto.split()))
                self.assertIn('17/11/2026', texto)
                self.assertNotIn('fecha_entrega', texto)
                self.assertGreater(pdf.pages[0].mediabox.width, pdf.pages[0].mediabox.height)

    def test_tabla_continua_con_encabezados_y_conserva_la_ultima_fila(self):
        filas = [fila_reporte('prestamos', n) for n in range(1, 81)]
        pdf = PdfReader(BytesIO(generar_pdf_reporte(FiltroReporte(), filas)))
        self.assertGreater(len(pdf.pages), 1)
        for pagina in pdf.pages:
            self.assertIn('Solicitante', pagina.extract_text())
        texto = '\n'.join(p.extract_text() for p in pdf.pages)
        self.assertIn('INV-0001', texto)
        self.assertIn('INV-0080', texto)
        self.assertIn('10:00', texto)
        self.assertIn('Pendiente', texto)

    def test_resultado_vacio_y_texto_largo_con_simbolos_no_rompen_el_pdf(self):
        vacio = PdfReader(BytesIO(generar_pdf_reporte(FiltroReporte(), [])))
        self.assertIn('No hay resultados para estos filtros.', vacio.pages[0].extract_text())
        fila = fila_reporte('danos_perdidas')
        fila['observacion'] = (
            '<b>Ñandú & equipo</b> ' + 'Detalle de revisión. ' * 500 + 'FIN_EVENTO'
        )
        pdf = PdfReader(
            BytesIO(
                generar_pdf_reporte(
                    FiltroReporte(tipo='danos_perdidas'),
                    [fila],
                )
            )
        )
        texto = '\n'.join(p.extract_text() for p in pdf.pages)
        self.assertIn('<b>Ñandú & equipo</b>', texto)
        self.assertIn('FIN_EVENTO', texto)


class DescargaReportePDF(unittest.TestCase):
    def setUp(self):
        self.repo = Mock(spec=IRepositorioReporte)
        self.fila = fila_reporte('prestamos')
        self.repo.consultar_filas_reporte.return_value = [self.fila]
        self.repo.consultar_reportes.return_value = (
            [self.fila],
            dict(detalles=1, prestamos=1, devueltos=0, pendientes=1, vencidos=0),
        )
        self.permitido = True
        self.app = Flask(__name__, template_folder='../presentacion/vistas')
        self.app.config.update(TESTING=True, SECRET_KEY='prueba-pdf')
        controlador = ControladorReporte(
            ServicioAplicacionReporte(self.repo),
            Mock(consultar_categorias=lambda: []),
        )
        self.app.register_blueprint(controlador.blueprint)
        for endpoint in ('inicio', 'cuentas.cambiar_clave_propia', 'auth.cerrar_sesion'):
            self.app.add_url_rule('/prueba/' + endpoint, endpoint, lambda: '')
        self.app.jinja_env.globals['csrf_token'] = lambda: 'prueba'
        self.app.jinja_env.filters['fecha'] = lambda valor: str(valor or '')

        @self.app.before_request
        def usuario_prueba():
            g.usuario = SimpleNamespace(
                nombres='Persona',
                apellidos='Prueba',
                nombre_completo='Persona Prueba',
                rol='USUARIO',
                permite=lambda p: self.permitido and p == 'REPORTES_CONSULTAR',
            )

        @self.app.errorhandler(ValueError)
        def error_filtro(error):
            return str(error), 400

        self.cliente = self.app.test_client()

    def test_descarga_pdf_usa_solo_filas_y_conserva_filtros_y_fechas_de_lima(self):
        respuesta = self.cliente.get(
            '/reportes/exportar.pdf',
            query_string=dict(
                tipo='prestamos',
                desde='2026-11-17',
                hasta='2026-11-17',
                modalidad='GRUPAL',
            ),
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.mimetype, 'application/pdf')
        self.assertIn('prestamos.pdf', respuesta.headers['Content-Disposition'])
        self.assertTrue(respuesta.data.startswith(b'%PDF-'))
        self.repo.consultar_filas_reporte.assert_called_once()
        self.repo.consultar_reportes.assert_not_called()
        filtro = self.repo.consultar_filas_reporte.call_args.args[0]
        self.assertEqual(filtro.modalidad, 'GRUPAL')
        self.assertEqual(filtro.inicio, datetime(2026, 11, 17, 5))
        self.assertEqual(filtro.fin, datetime(2026, 11, 18, 5))

    def test_sin_permiso_o_filtro_invalido_no_consulta_datos(self):
        self.permitido = False
        self.assertEqual(self.cliente.get('/reportes/exportar.pdf').status_code, 403)
        self.permitido = True
        self.assertEqual(self.cliente.get('/reportes/exportar.pdf?tipo=ajeno').status_code, 400)
        self.repo.consultar_filas_reporte.assert_not_called()

    def test_enlace_pdf_conserva_filtros_y_csv_sigue_disponible(self):
        pagina = self.cliente.get('/reportes?q=02167885&modalidad=GRUPAL').get_data(as_text=True)
        enlaces = [urlsplit(unescape(e)) for e in re.findall(r'href="([^"]+)"', pagina)]
        enlace = next(e for e in enlaces if e.path == '/reportes/exportar.pdf')
        self.assertEqual(parse_qs(enlace.query)['q'], ['02167885'])
        self.assertEqual(parse_qs(enlace.query)['modalidad'], ['GRUPAL'])
        respuesta = self.cliente.get('/reportes/exportar.csv')
        registros = list(
            csv.DictReader(
                StringIO(respuesta.get_data(as_text=True).lstrip('\ufeff')),
                delimiter=';',
            )
        )
        self.assertEqual(registros[0]['codigo_inventario'], 'INV-0001')
