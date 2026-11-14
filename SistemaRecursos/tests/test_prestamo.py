from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch
from mysql.connector import DatabaseError
from dominio.compartido.validacion import Conflicto
from caso_mysql import CasoMySQL


class OperacionesPrestamo(CasoMySQL):
    def test_entrega_grupal_guarda_detalles_integrantes_inventario_e_historial(self):
        identificador = self.prestar([2, 3], tipo_prestamo='GRUPAL', participantes=['99000001'])
        prestamo = self.prestamo(identificador)
        self.assertEqual(len(prestamo['detalles']), 2)
        self.assertEqual(
            {p['dni_persona'] for p in prestamo['participantes']}, {'02167885', '99000001'}
        )
        self.assertEqual(
            self.fila(
                "SELECT COUNT(*) FROM bien_material WHERE id_bien IN (2,3) AND estado='PRESTADO'"
            ),
            (2,),
        )
        self.assertEqual(len(prestamo['historial']), 1)

    def test_no_entregar_bien_dos_veces_aunque_estado_este_mal(self):
        self.prestar()
        self.ejecutar("UPDATE bien_material SET estado='DISPONIBLE' WHERE id_bien=2")
        with self.assertRaises(Conflicto):
            self.prestar()
        self.assertEqual(self.fila('SELECT COUNT(*) FROM prestamo'), (1,))

    def test_error_al_guardar_historial_revierte_entrega_completa(self):
        with patch(
            'repositorio.base_sql.RepositorioSQL.registrar_historial_estado',
            side_effect=RuntimeError('Fallo simulado'),
        ):
            with self.assertRaises(RuntimeError):
                self.prestar([2, 3], tipo_prestamo='GRUPAL', participantes=['99000001'])
        self.assertEqual(self.fila('SELECT COUNT(*) FROM prestamo'), (0,))
        self.assertEqual(self.fila('SELECT COUNT(*) FROM detalle_prestamo'), (0,))
        self.assertEqual(
            self.fila(
                "SELECT COUNT(*) FROM bien_material WHERE id_bien IN (2,3) AND estado='DISPONIBLE'"
            ),
            (2,),
        )

    def test_devolucion_parcial_y_final(self):
        identificador = self.prestar([2, 3])
        primero, segundo = [d['id_detalle'] for d in self.prestamo(identificador)['detalles']]
        self.servicios['prestamos'].registrar_devolucion(
            identificador, dict(detalles=[primero], **{f'condicion_{primero}': 'BUENO'}), 2
        )
        self.assertEqual(self.prestamo(identificador)['estado_actual'], 'PARCIALMENTE_DEVUELTO')
        self.servicios['prestamos'].registrar_devolucion(
            identificador,
            dict(
                detalles=[segundo],
                **{f'condicion_{segundo}': 'DANADO', f'observacion_{segundo}': 'Cable roto'},
            ),
            2,
        )
        self.assertEqual(self.prestamo(identificador)['estado_actual'], 'DEVUELTO')
        self.assertEqual(self.fila('SELECT estado FROM bien_material WHERE id_bien=3'), ('DANADO',))
        self.assertEqual(self.fila('SELECT COUNT(*) FROM incidencia'), (0,))

    def test_devolucion_ajena_o_danada_sin_detalle_no_hace_escrituras(self):
        identificador = self.prestar([2, 3])
        primero = self.prestamo(identificador)['detalles'][0]['id_detalle']
        with self.assertRaises(LookupError):
            self.servicios['prestamos'].registrar_devolucion(
                identificador,
                dict(
                    detalles=[primero, 999],
                    **{f'condicion_{primero}': 'BUENO', 'condicion_999': 'BUENO'},
                ),
                2,
            )
        with self.assertRaises(ValueError):
            self.servicios['prestamos'].registrar_devolucion(
                identificador, dict(detalles=[primero], **{f'condicion_{primero}': 'DANADO'}), 2
            )
        self.assertEqual(
            self.fila('SELECT COUNT(*) FROM detalle_prestamo WHERE fecha_devolucion IS NOT NULL'),
            (0,),
        )

    def test_perdida_sigue_pendiente_y_admite_recuperacion(self):
        identificador = self.prestar()
        detalle = self.prestamo(identificador)['detalles'][0]['id_detalle']
        self.servicios['prestamos'].registrar_perdida_bien_material(
            identificador, detalle, 'No se encuentra', 2
        )
        self.assertEqual(
            len(self.servicios['prestamos'].consultar_prestamos({'estado': 'PERDIDOS'})), 1
        )
        self.assertEqual(
            len(self.servicios['prestamos'].consultar_prestamos({'estado': 'PENDIENTES'})), 1
        )
        self.assertIsNone(self.prestamo(identificador)['detalles'][0]['fecha_devolucion'])
        self.assertEqual(
            self.fila('SELECT estado FROM bien_material WHERE id_bien=2'), ('PERDIDO',)
        )
        self.servicios['prestamos'].registrar_devolucion(
            identificador, dict(detalles=[detalle], **{f'condicion_{detalle}': 'BUENO'}), 2
        )
        self.assertEqual(
            self.fila('SELECT estado FROM bien_material WHERE id_bien=2'), ('DISPONIBLE',)
        )
        self.assertEqual(self.prestamo(identificador)['estado_actual'], 'DEVUELTO')

    def test_ampliacion_directa_actualiza_detalle_e_historial(self):
        identificador = self.prestar()
        detalle = self.prestamo(identificador)['detalles'][0]
        datos = dict(
            cantidad=1,
            unidad='DIAS',
            fecha_actual=detalle['fecha_limite_devolucion'].isoformat(),
            motivo='Trabajo de clase',
        )
        nueva = self.servicios['ampliaciones'].ampliar_prestamo(
            identificador, detalle['id_detalle'], datos, 2
        )
        self.assertEqual(nueva, detalle['fecha_limite_devolucion'] + timedelta(days=1))
        with self.assertRaises(Conflicto):
            self.servicios['ampliaciones'].ampliar_prestamo(
                identificador, detalle['id_detalle'], datos, 2
            )
        self.assertEqual(len(self.prestamo(identificador)['historial']), 2)

    def test_sancion_por_retraso_afecta_todos_y_no_se_reactiva(self):
        identificador = self.prestar(tipo_prestamo='GRUPAL', participantes=['99000001'])
        self.ejecutar(
            'UPDATE detalle_prestamo SET fecha_limite_devolucion=DATE_SUB(UTC_TIMESTAMP(),INTERVAL 2 DAY)'
        )
        self.assertEqual(self.servicios['sanciones'].aplicar_sanciones_por_vencimiento(), 1)
        sancion = self.servicios['sanciones'].consultar_sanciones()[0]['id_sancion']
        with self.servicios['prestamos'].repositorio.transaccion() as op:
            for persona in ('02167885', '99000001'):
                self.assertTrue(op.sanciones.existen_sanciones_activas([persona]))
        self.servicios['sanciones'].levantar_sancion(sancion, 'Regularizado con el grupo', 2)
        self.assertEqual(self.servicios['sanciones'].aplicar_sanciones_por_vencimiento(), 0)
        detalle = self.prestamo(identificador)['detalles'][0]['id_detalle']
        self.servicios['prestamos'].registrar_devolucion(
            identificador, dict(detalles=[detalle], **{f'condicion_{detalle}': 'BUENO'}), 2
        )
        self.assertEqual(self.fila('SELECT estado FROM sancion'), ('LEVANTADA',))
        self.assertEqual(self.fila('SELECT COUNT(*) FROM sancion'), (1,))

    def test_usuario_solo_ve_prestamos_en_los_que_participa(self):
        identificador = self.prestar(tipo_prestamo='GRUPAL', participantes=['99000001'])
        self.assertEqual(
            self.servicios['prestamos'].consultar_prestamo(identificador, '99000001')[
                'id_prestamo'
            ],
            identificador,
        )
        with self.assertRaises(PermissionError):
            self.servicios['prestamos'].consultar_prestamo(identificador, '99000002')

    def test_dos_entregas_concurrentes_solo_confirman_una(self):
        barrera = Barrier(2)

        def entregar(documento):
            barrera.wait(timeout=10)
            try:
                return ('confirmada', self.prestar(dni_persona=documento))
            except Conflicto as error:
                return ('rechazada', type(error).__name__)
            except DatabaseError as error:
                if error.errno not in (1205, 1213):
                    raise
                return ('rechazada', type(error).__name__)

        with ThreadPoolExecutor(max_workers=2) as hilos:
            resultados = list(hilos.map(entregar, ['02167885', '99000001']))
        self.assertEqual([r[0] for r in resultados].count('confirmada'), 1, resultados)
        self.assertEqual(
            self.fila(
                'SELECT COUNT(*) FROM detalle_prestamo WHERE id_bien=2 AND fecha_devolucion IS NULL'
            ),
            (1,),
        )
