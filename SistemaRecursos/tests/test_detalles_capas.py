import unittest
from caso_mysql import CasoMySQL
from dominio.compartido.validacion import NoEncontrado
from dominio.gestion_control.catalogo_reportes import REPORTES
from dominio.gestion_control.reporte import FiltroReporte
from presentacion.formatos_reportes import presentar_reporte


class ContratosReportes(unittest.TestCase):
    def test_filtro_desde_formulario_descarta_campos_ajenos(self):
        filtro = FiltroReporte.desde_datos(
            {'tipo': 'inventario', 'pagina': '2', 'csrf_token': 'ajeno'}
        )
        self.assertFalse(hasattr(filtro, 'pagina'))
        self.assertEqual(filtro.tipo, 'inventario')

    def test_presentacion_no_modifica_las_columnas_que_exporta_el_dominio(self):
        for tipo, original in REPORTES.items():
            vista = presentar_reporte(tipo)
            self.assertEqual(
                [c.nombre for c in vista.columnas], [c.nombre for c in original.columnas]
            )
            self.assertTrue(all(not hasattr(c, 'formato') for c in original.columnas))
            self.assertTrue(all(not hasattr(c, 'en_tabla') for c in original.columnas))
        columnas = {c.nombre: c for c in presentar_reporte('inventario').columnas}
        self.assertEqual(columnas['codigo_inventario'].formato, 'inventario')
        self.assertFalse(columnas['id_bien'].en_tabla)


class ContextoAmpliacionConNombres(CasoMySQL):
    def test_repositorio_devuelve_ausencia_y_servicio_decide_el_error(self):
        servicio = self.servicios['ampliaciones']
        datos = dict(
            cantidad='1', unidad='HORAS', fecha_actual=self.consultar_fecha_actual.isoformat()
        )
        with servicio.repositorio.transaccion() as operacion:
            contexto = operacion.consultar_contexto_ampliacion_prestamo(99999, 99999)
            self.assertIsNone(contexto['prestamo'])
            self.assertIsNone(contexto['detalle'])
        with self.assertRaisesRegex(NoEncontrado, 'Préstamo inexistente'):
            servicio.ampliar_prestamo(99999, 99999, datos, 2)
        identificador = self.prestar()
        with servicio.repositorio.transaccion() as operacion:
            contexto = operacion.consultar_contexto_ampliacion_prestamo(identificador, 99999)
            self.assertEqual(contexto['prestamo']['id_prestamo'], identificador)
            self.assertIsNone(contexto['detalle'])
        with self.assertRaisesRegex(NoEncontrado, 'no pertenece'):
            servicio.ampliar_prestamo(identificador, 99999, datos, 2)
