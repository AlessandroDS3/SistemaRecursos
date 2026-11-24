import unittest

from presentacion.reportes.graficos_reportes import preparar_graficos


class GraficosReportesTest(unittest.TestCase):
    def test_recurso_con_nombre_de_grupo_no_pierde_registros(self):
        filas = [dict(recurso='Resto de recursos (agrupados)', estado='DISPONIBLE')] * 3
        filas.extend(dict(recurso=str(i), estado='DISPONIBLE') for i in range(7))
        barras = preparar_graficos('inventario', filas)['barras']
        self.assertEqual(barras['total'], 10)
        self.assertEqual(len({item['etiqueta'] for item in barras['elementos']}), 7)
        self.assertEqual([item['cantidad'] for item in barras['elementos']], [3, 1, 1, 1, 1, 1, 2])
