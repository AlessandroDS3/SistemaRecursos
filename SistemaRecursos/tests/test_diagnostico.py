import csv
from io import StringIO
from unittest.mock import patch

from caso_mysql import CasoMySQL
from dominio.compartido.validacion import Conflicto
from dominio.gestion_prestamos.prestamo import estado_prestamo
from repositorio.base_sql import RepositorioSQL


class CorreccionesDiagnostico(CasoMySQL):
    def test_politica_identica_no_crea_version_y_no_admite_version_obsoleta_ni_id_cero(self):
        servicio = self.servicios['politicas']
        fila, version = servicio.consultar_politica_prestamo(24)
        datos = dict(fila, version=version)
        self.assertEqual(servicio.guardar_politica_prestamo(datos, 1, 24), 24)
        self.assertEqual(self.fila('SELECT COUNT(*) FROM politica_prestamo'), (1,))
        with self.assertRaises(Conflicto):
            servicio.guardar_politica_prestamo(dict(datos, version='obsoleta'), 1, 24)
        with self.assertRaises(ValueError):
            servicio.guardar_politica_prestamo(datos, 1, 0)

    def test_configuracion_incompleta_no_reinicia_los_plazos(self):
        servicio = self.servicios['politicas']
        antes = servicio.consultar_configuracion_general()
        with self.assertRaises(ValueError):
            servicio.guardar_configuracion_general(
                dict(hora_apertura='09:00', hora_cierre='17:00'), 1
            )
        self.assertEqual(servicio.consultar_configuracion_general(), antes)

    def test_permisos_identicos_no_escriben(self):
        servicio = self.servicios['roles']
        matriz, version = servicio.consultar_matriz_permisos()
        with patch.object(
            RepositorioSQL, 'ejecutar', side_effect=AssertionError('Escritura innecesaria')
        ):
            servicio.guardar_matriz_permisos(matriz, version, 1)

    def test_historial_inserta_sin_consultar_la_hora_por_separado(self):
        with self.servicios['recursos'].repositorio.transaccion() as operacion:
            with patch.object(
                operacion, 'consultar_fecha_actual', side_effect=AssertionError('SELECT extra')
            ):
                operacion.registrar_historial_estado(
                    'BIEN_MATERIAL', 2, 'DISPONIBLE', 'DANADO', '98000001', 'Prueba'
                )
        self.assertEqual(self.fila('SELECT COUNT(*) FROM historial_estado'), (1,))

    def test_inicio_resumen_respeta_integrantes_y_no_muestra_prestamos_ajenos(self):
        self.prestar([2, 3], tipo_prestamo='GRUPAL', participantes=['99000001'])
        servicio = self.servicios['prestamos']
        for documento in (None, '02167885', '99000001', '99000003'):
            filas = servicio.consultar_prestamos({}, documento)
            resumen = servicio.consultar_resumen_prestamos(documento)
            self.assertEqual(
                resumen['prestamos_pendientes'],
                sum(f['estado_actual'] != 'DEVUELTO' for f in filas),
            )
            self.assertEqual(
                resumen['prestamos_vencidos'], sum(f['estado_actual'] == 'VENCIDO' for f in filas)
            )
        self.assertEqual(self.servicios['recursos'].consultar_disponibilidad(), 0)

    def test_csv_individual_usa_una_consulta_grupal_dos_y_conserva_integrantes(self):
        self.prestar()
        original = RepositorioSQL.consultar_sql
        consultas = []

        def registrar(repo, sql, parametros=(), una=False):
            consultas.append(sql)
            return original(repo, sql, parametros, una)

        with patch.object(RepositorioSQL, 'consultar_sql', registrar):
            contenido, _ = self.servicios['reportes'].exportar_reportes_csv({})
        self.assertEqual(len(consultas), 1)
        filas = list(csv.DictReader(StringIO(contenido.lstrip('\ufeff')), delimiter=';'))
        self.assertEqual(filas[0]['integrantes'], '')
        self.prestar([3], tipo_prestamo='GRUPAL', participantes=['99000001'])
        consultas.clear()
        with patch.object(RepositorioSQL, 'consultar_sql', registrar):
            contenido, _ = self.servicios['reportes'].exportar_reportes_csv({})
        self.assertEqual(len(consultas), 2)
        self.assertIn('99000001', contenido)

    def test_estado_sql_coincide_con_dominio_en_los_cuatro_estados(self):
        identificador = self.prestar([2, 3])
        for estado in ('ACTIVO', 'VENCIDO', 'PARCIALMENTE_DEVUELTO', 'DEVUELTO'):
            self.ejecutar(
                '''UPDATE detalle_prestamo SET fecha_devolucion=NULL,
                condicion_devolucion=NULL,observaciones_devolucion=NULL,
                fecha_limite_devolucion=DATE_ADD(UTC_TIMESTAMP(),INTERVAL 1 DAY)
                WHERE id_prestamo=%s''',
                (identificador,),
            )
            if estado == 'VENCIDO':
                self.ejecutar(
                    'UPDATE detalle_prestamo SET fecha_limite_devolucion=DATE_SUB(UTC_TIMESTAMP(),INTERVAL 1 DAY) WHERE id_prestamo=%s',
                    (identificador,),
                )
            if estado in ('PARCIALMENTE_DEVUELTO', 'DEVUELTO'):
                self.ejecutar(
                    '''UPDATE detalle_prestamo SET fecha_devolucion=UTC_TIMESTAMP(),
                    condicion_devolucion='BUENO' WHERE id_prestamo=%s'''
                    + (' AND id_bien=2' if estado == 'PARCIALMENTE_DEVUELTO' else ''),
                    (identificador,),
                )
            prestamo = self.prestamo(identificador)
            self.assertEqual(prestamo['estado_actual'], estado)
            self.assertEqual(
                estado_prestamo(prestamo['detalles'], self.consultar_fecha_actual), estado
            )
