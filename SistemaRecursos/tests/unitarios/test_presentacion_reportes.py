"""Exportaciones y formatos de reportes: CSV, PDF, gráficos vectoriales y textos de la vista."""

from base64 import b64decode
from datetime import date, datetime
import unittest

from reportlab.graphics import renderSVG

from presentacion.controladores.reportes.controlador_reporte import svg_como_data_uri
from presentacion.reportes.csv_reportes import _sanear_valor_para_csv, generar_csv_reporte
from presentacion.reportes.dibujos_reportes import (
    calcular_segmentos_del_sector,
    circular_3d,
    columnas,
    dibujar_graficos_de_reporte,
)
from presentacion.reportes.formatos_reportes import (
    etiqueta_cierre_sancion,
    etiqueta_reporte,
    presentar_reporte,
    valor_reporte,
)
from presentacion.reportes.graficos_reportes import preparar_graficos
from presentacion.reportes.pdf_reportes import generar_pdf_reporte
from servicios.reportes.catalogo_reportes import REPORTES
from servicios.reportes.filtro_reporte import FiltroReporte

TIPOS_GENERALES = [tipo for tipo in REPORTES if not tipo.startswith('historial_')]


def fila_de_ejemplo(tipo, indice=0):
    """Fila con todas las columnas del reporte y valores del tipo que espera cada formato."""
    fila = {}
    for columna in REPORTES[tipo].columnas:
        nombre = columna.nombre
        if nombre.startswith('fecha_adquisicion'):
            fila[nombre] = date(2026, 1, 10)
        elif nombre.startswith('fecha'):
            fila[nombre] = datetime(2026, 1, 10, 15, 30)
        elif nombre == 'retraso_minutos':
            fila[nombre] = 30 + indice * 900
        elif nombre.startswith('id_'):
            fila[nombre] = indice + 1
        elif nombre == 'dni_persona':
            fila[nombre] = '7000000' + str(indice % 10)
        else:
            fila[nombre] = f'{nombre} {indice % 3}'
    fila.update(tipo_prestamo='GRUPAL', integrantes='Ana Prueba', recurso=f'Recurso {indice % 4}')
    return fila


class SvgComoDataUriTest(unittest.TestCase):
    def test_codifica_el_svg_en_base64_sin_perder_caracteres_escapados(self):
        svg = '<svg><text>&lt;script&gt; Préstamo</text></svg>'
        uri = svg_como_data_uri(svg)
        self.assertTrue(uri.startswith('data:image/svg+xml;base64,'))
        self.assertEqual(b64decode(uri.split(',', 1)[1]).decode('utf-8'), svg)


class CsvReportesTest(unittest.TestCase):
    def test_neutraliza_formulas_para_hojas_de_calculo(self):
        for peligroso in ('=SUMA(A1)', '+1', '-2', '@cmd', '  =1', '\tdato', '\rdato', '\ndato'):
            with self.subTest(peligroso=peligroso):
                self.assertEqual(_sanear_valor_para_csv(peligroso), "'" + peligroso)

    def test_conserva_valores_seguros_y_vacios(self):
        self.assertEqual(_sanear_valor_para_csv('Laptop'), 'Laptop')
        self.assertEqual(_sanear_valor_para_csv(None), '')
        self.assertEqual(_sanear_valor_para_csv(5), '5')

    def test_genera_cabecera_bom_y_fechas_en_hora_de_lima(self):
        filtro = FiltroReporte(tipo='prestamos')
        fila = fila_de_ejemplo('prestamos')
        texto = generar_csv_reporte(filtro, [fila])
        self.assertTrue(texto.startswith('﻿'))
        lineas = texto[1:].split('\r\n')
        self.assertEqual(lineas[0].split(';'), [c.nombre for c in REPORTES['prestamos'].columnas])
        # 15:30 UTC son las 10:30 en Lima (UTC-5).
        self.assertIn('2026-01-10 10:30:00', lineas[1])

    def test_sin_filas_solo_escribe_la_cabecera(self):
        texto = generar_csv_reporte(FiltroReporte(tipo='inventario'), [])
        self.assertEqual(texto.count('\r\n'), 1)


class FormatosReportesTest(unittest.TestCase):
    def test_etiquetas_conocidas_y_genericas(self):
        self.assertEqual(etiqueta_reporte('DANADO'), 'Dañado')
        self.assertEqual(etiqueta_reporte('EN_CURSO'), 'En curso')

    def test_valores_vacios_numeros_y_etiquetas(self):
        self.assertEqual(valor_reporte(None), '—')
        self.assertEqual(valor_reporte(''), '—')
        self.assertEqual(valor_reporte(7.0, 'numero'), '7')
        self.assertEqual(valor_reporte('TARDIA', 'etiqueta'), 'Tardía')
        self.assertEqual(valor_reporte('Texto libre'), 'Texto libre')

    def test_duraciones(self):
        self.assertEqual(valor_reporte(0.5, 'duracion'), 'Menos de 1 min')
        self.assertEqual(valor_reporte(0, 'duracion'), '0 min')
        self.assertEqual(valor_reporte(61, 'duracion'), '1 h 1 min')
        self.assertEqual(valor_reporte(1440 + 120, 'duracion'), '1 d 2 h')

    def test_cierre_de_sancion_solo_si_fue_levantada(self):
        self.assertIsNone(etiqueta_cierre_sancion({'estado': 'ACTIVA'}))
        self.assertIsNone(etiqueta_cierre_sancion({'estado': 'ACTIVA', 'fecha_levantamiento': datetime(2026, 1, 1)}))

    def test_presentar_reporte_oculta_columnas_internas(self):
        for tipo in REPORTES:
            with self.subTest(tipo=tipo):
                reporte = presentar_reporte(tipo)
                visibles = {c.nombre for c in reporte.columnas if c.en_tabla}
                self.assertNotIn('dni_persona', visibles)
                self.assertEqual(len(reporte.columnas), len(REPORTES[tipo].columnas))
        self.assertNotIn('recurso', {c.nombre for c in presentar_reporte('atrasados').columnas if c.en_tabla})
        formatos = {c.nombre: c.formato for c in presentar_reporte('inventario').columnas}
        self.assertEqual(formatos.get('codigo_inventario'), 'inventario')


class DibujosReportesTest(unittest.TestCase):
    def serie(self, cantidades):
        total = sum(cantidades)
        return {
            'total': total,
            'maximo': max(cantidades, default=0),
            'elementos': [
                {'cantidad': c, 'porcentaje': round(100 * c / total) if total else 0, 'color': '#7a0d2e', 'etiqueta': str(i)}
                for i, c in enumerate(cantidades)
            ],
        }

    def test_circular_con_y_sin_datos(self):
        self.assertEqual(len(circular_3d(self.serie([])).contents), 0)
        dibujo = circular_3d(self.serie([6, 3, 1]))
        self.assertGreater(len(dibujo.contents), 3)
        self.assertIn('<svg', renderSVG.drawToString(dibujo))

    def test_columnas_e_histograma(self):
        vacio = columnas(self.serie([]))
        self.assertEqual(len(vacio.contents), 10)  # Solo la cuadrícula: 5 líneas y 5 valores.
        normal = columnas(self.serie([4, 2]))
        histograma = columnas(self.serie([4, 2]), histograma=True)
        self.assertEqual(len(normal.contents), 10 + 2 * 3)
        self.assertGreater(histograma.contents[10].width, normal.contents[10].width)

    def test_segmentos_crecen_con_la_amplitud(self):
        self.assertEqual(calcular_segmentos_del_sector(0), 1)
        self.assertGreater(calcular_segmentos_del_sector(3), calcular_segmentos_del_sector(1))

    def test_dibuja_los_dos_graficos_de_un_reporte(self):
        filas = [fila_de_ejemplo('inventario', i) for i in range(5)]
        graficos = preparar_graficos('inventario', filas)
        self.assertEqual(len(dibujar_graficos_de_reporte(graficos)), 2)


class PdfReportesTest(unittest.TestCase):
    def test_genera_pdf_de_cada_reporte_con_y_sin_resultados(self):
        generado = datetime(2026, 1, 10, 15, 30)
        for tipo in TIPOS_GENERALES:
            filtro = FiltroReporte(tipo=tipo)
            for filas in ([], [fila_de_ejemplo(tipo, i) for i in range(4)]):
                with self.subTest(tipo=tipo, filas=len(filas)):
                    pdf = generar_pdf_reporte(filtro, filas, generado_en=generado)
                    self.assertTrue(pdf.startswith(b'%PDF'))


if __name__ == '__main__':
    unittest.main()
