import csv
from io import StringIO
from caso_mysql import CasoMySQL


class Reportes(CasoMySQL):
    def test_grupo_no_multiplica_filas_y_reportes_no_escriben(self):
        self.prestar([2, 3], tipo_prestamo='GRUPAL', participantes=['99000001', '99000002'])
        antes = self.fila('SELECT COUNT(*) FROM historial_estado')
        resultado = self.servicios['reportes'].consultar_reportes({})
        self.assertEqual(
            resultado['resumen'],
            dict(detalles=2, prestamos=1, devueltos=0, pendientes=2, vencidos=0),
        )
        self.assertEqual(len(resultado['filas']), 2)
        self.assertEqual(self.fila('SELECT COUNT(*) FROM historial_estado'), antes)

    def test_filtros_incluyen_integrante_inventario_modalidad_y_tipo(self):
        self.prestar([2, 3], tipo_prestamo='GRUPAL', participantes=['99000001'])
        resultado = self.servicios['reportes'].consultar_reportes(
            dict(q='99000001', modalidad='GRUPAL', tipo_persona='ESTUDIANTE')
        )
        self.assertEqual(len(resultado['filas']), 2)
        self.assertIn('99000001', resultado['filas'][0]['integrantes'])
        self.assertEqual(
            len(self.servicios['reportes'].consultar_reportes(dict(q='INV-2'))['filas']), 1
        )
        self.assertEqual(
            len(
                self.servicios['reportes'].consultar_reportes(dict(tipo_persona='DOCENTE'))['filas']
            ),
            0,
        )

    def test_csv_usa_bom_punto_y_coma_lima_y_protege_formulas(self):
        self.ejecutar("UPDATE persona SET nombres='=CMD()' WHERE dni='02167885'")
        self.prestar()
        texto, tipo = self.servicios['reportes'].exportar_reportes_csv({})
        self.assertTrue(texto.startswith('\ufeff'))
        filas = list(csv.DictReader(StringIO(texto.lstrip('\ufeff')), delimiter=';'))
        self.assertEqual(tipo, 'prestamos')
        self.assertTrue(filas[0]['solicitante'].startswith("'="))
        self.assertTrue(filas[0]['fecha_entrega'].endswith('10:00:00'))

    def test_filtro_devoluciones_y_fechas(self):
        prestamo = self.prestar([2, 3])
        detalle = self.prestamo(prestamo)['detalles'][0]['id_detalle']
        self.servicios['prestamos'].registrar_devolucion(
            prestamo, dict(detalles=[detalle], **{f'condicion_{detalle}': 'BUENO'}), 2
        )
        datos = dict(
            tipo='devoluciones',
            desde=self.consultar_fecha_actual.date().isoformat(),
            hasta=self.consultar_fecha_actual.date().isoformat(),
        )
        resultado = self.servicios['reportes'].consultar_reportes(datos)
        self.assertEqual(resultado['resumen']['detalles'], 1)
        self.assertEqual(resultado['filas'][0]['id_prestamo'], prestamo)
        self.assertEqual(resultado['filas'][0]['codigo_inventario'], 'INV-2')

    def test_pantalla_y_exportacion_incluyen_todos_los_resultados(self):
        self.prestar()
        self.ejecutar(
            '''INSERT INTO detalle_prestamo(id_prestamo,id_bien,id_politica,fecha_limite_devolucion)
            SELECT p.id_prestamo,b.id_bien,24,DATE_ADD(UTC_TIMESTAMP(),INTERVAL 2 DAY)
            FROM prestamo p JOIN bien_material b ON b.id_bien=3'''
        )
        # Se fabrican préstamos históricos sin afectar el inventario, solo para probar la consulta.
        for _ in range(26):
            self.ejecutar(
                '''INSERT INTO prestamo(dni_persona,dni_encargado,fecha_solicitud,fecha_entrega,estado)
                VALUES('99000003','98000002',UTC_TIMESTAMP(),UTC_TIMESTAMP(),'DEVUELTO')'''
            )
            identificador = self.fila('SELECT MAX(id_prestamo) FROM prestamo')[0]
            for bien in (2, 3):
                self.ejecutar(
                    '''INSERT INTO detalle_prestamo(id_prestamo,id_bien,id_politica,fecha_limite_devolucion,
                    fecha_devolucion,dni_encargado_devolucion,condicion_devolucion)
                    VALUES(%s,%s,24,UTC_TIMESTAMP(),UTC_TIMESTAMP(),'98000002','BUENO')''',
                    (identificador, bien),
                )
        resultado = self.servicios['reportes'].consultar_reportes({})
        self.assertEqual(len(resultado['filas']), 54)
        self.assertEqual(resultado['resumen']['detalles'], 54)
        texto, _ = self.servicios['reportes'].exportar_reportes_csv({})
        self.assertEqual(len(list(csv.reader(StringIO(texto), delimiter=';'))), 55)
