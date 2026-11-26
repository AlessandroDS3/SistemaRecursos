"""Reglas de gravedad, cumplimiento y plazos de sanciones."""

from datetime import datetime, timedelta
import unittest

from dominio.compartido.validacion import Conflicto
from dominio.gestion_control.incidencia import TipoIncidencia
from dominio.gestion_control.sancion import (
    ConfiguracionSanciones, FaltaAutomatica, calcular_alertas_de_sancion, evaluar_danio_nuevo, determinar_falta_por_retraso,
    puede_marcarse_sancion_cumplida, determinar_regularizacion_por_devolucion, validar_levantamiento_de_sancion,
)


class ReglasSancionTest(unittest.TestCase):
    def setUp(self):
        self.ahora = datetime(2026, 11, 22, 15)
        self.sancion = dict(
            estado='ACTIVA', gravedad='LEVE', fecha_fin=self.ahora + timedelta(days=14),
            fecha_regularizacion=None, fecha_revision=self.ahora + timedelta(days=21),
            fecha_limite_devolucion=self.ahora, fecha_devolucion=None, permite_salida=False,
        )

    def test_configuracion_valida_plazos_positivos(self):
        for campo in ('dias_leve', 'dias_grave', 'dias_espera_perdida'):
            for valor in (0, -1, True, '1.5'):
                with self.subTest(campo=campo, valor=valor), self.assertRaises(ValueError):
                    ConfiguracionSanciones(**{campo: valor})

    def test_retraso_aplica_leve_desde_el_vencimiento(self):
        detalle = dict(fecha_limite_devolucion=self.ahora, fecha_devolucion=None)
        self.assertIsNone(determinar_falta_por_retraso(detalle, self.ahora))
        despues = self.ahora + timedelta(seconds=1)
        falta = determinar_falta_por_retraso(detalle, despues)
        self.assertEqual(falta, FaltaAutomatica(TipoIncidencia.RETRASO, 'LEVE', 'Devolución fuera de plazo', self.ahora))
        self.assertIsNone(determinar_falta_por_retraso(dict(detalle, fecha_regularizacion=despues), despues))

    def test_danio_nuevo_conserva_nivel_grave_y_respeta_anulacion(self):
        for gravedad in ('GRAVE', 'MUY_GRAVE'):
            sancion = dict(self.sancion, tipo='PERDIDA', gravedad=gravedad)
            self.assertEqual(evaluar_danio_nuevo(sancion, 'Daño comprobado', self.ahora), 'CONSERVAR_GRAVEDAD_Y_PLAZO')
        anulada = dict(sancion, estado='ANULADA')
        self.assertIsNone(evaluar_danio_nuevo(dict(anulada, tipo='DANIO'), 'Daño', self.ahora))
        grave = FaltaAutomatica(TipoIncidencia.DANIO, 'GRAVE', 'Daño', self.ahora)
        self.assertEqual(evaluar_danio_nuevo(anulada, 'Daño', self.ahora), grave)
        self.assertEqual(evaluar_danio_nuevo(dict(self.sancion, tipo='RETRASO'), 'Daño', self.ahora), grave)

    def test_regularizacion_automatica_depende_de_causa_condicion_y_estado(self):
        perdida = dict(self.sancion, tipo='PERDIDA')
        self.assertEqual(determinar_regularizacion_por_devolucion(perdida, 'BUENO'), 'RECUPERACION')
        self.assertEqual(determinar_regularizacion_por_devolucion(dict(perdida, tipo='RETRASO'), 'BUENO'), 'DEVOLUCION')
        self.assertIsNone(determinar_regularizacion_por_devolucion(perdida, 'DANADO'))
        self.assertIsNone(determinar_regularizacion_por_devolucion(dict(perdida, estado='ANULADA'), 'BUENO'))
        self.assertIsNone(determinar_regularizacion_por_devolucion(dict(perdida, fecha_regularizacion=self.ahora), 'BUENO'))

    def test_cumplir_exige_tiempo_y_regularizacion(self):
        self.assertFalse(puede_marcarse_sancion_cumplida(self.sancion, self.ahora + timedelta(days=40)))
        self.sancion['fecha_regularizacion'] = self.ahora
        self.assertFalse(puede_marcarse_sancion_cumplida(self.sancion, self.ahora))
        self.assertTrue(puede_marcarse_sancion_cumplida(self.sancion, self.ahora + timedelta(days=14)))
        self.sancion.update(gravedad='MUY_GRAVE', fecha_fin=None)
        self.assertFalse(puede_marcarse_sancion_cumplida(self.sancion, self.ahora + timedelta(days=999)))

    def test_encargado_puede_perdonar_leve_regularizada_sin_limite_de_minutos(self):
        cuenta = dict(rol='ENCARGADO_PRESTAMOS')
        with self.assertRaises(Conflicto):
            validar_levantamiento_de_sancion(self.sancion, 'Recepción demorada por el encargado', self.ahora, cuenta)
        self.sancion['fecha_regularizacion'] = self.ahora
        self.assertTrue(validar_levantamiento_de_sancion(self.sancion, 'Demora de recepción', self.ahora, cuenta))
        self.sancion['gravedad'] = 'GRAVE'
        with self.assertRaises(Conflicto):
            validar_levantamiento_de_sancion(self.sancion, 'Reparación aceptada', self.ahora, cuenta)

    def test_alerta_perdida_no_modifica_estado_y_cuenta_plazos_de_la_sancion(self):
        resultado = calcular_alertas_de_sancion(self.sancion, self.ahora + timedelta(days=20))
        self.assertFalse(resultado['posible_perdida'])
        self.assertTrue(calcular_alertas_de_sancion(self.sancion, self.ahora + timedelta(days=21))['posible_perdida'])
        self.assertEqual(self.sancion['gravedad'], 'LEVE')
        self.sancion['fecha_devolucion'] = self.ahora
        self.assertFalse(calcular_alertas_de_sancion(self.sancion, self.ahora + timedelta(days=30))['posible_perdida'])

    def test_alertas_omiten_plazos_sin_fecha(self):
        ahora = self.ahora + timedelta(days=30)
        self.sancion['fecha_revision'] = None
        resultado = calcular_alertas_de_sancion(self.sancion, ahora)
        self.assertFalse(resultado['posible_perdida'])
        self.assertTrue(resultado['revisar_custodia'])

        self.sancion.update(gravedad='GRAVE', fecha_fin=None)
        self.assertFalse(calcular_alertas_de_sancion(self.sancion, ahora)['revision_administrador'])

    def test_custodia_usa_fecha_de_lima(self):
        self.sancion['fecha_limite_devolucion'] = datetime(2026, 11, 22, 21)  # 16:00 Lima
        self.assertFalse(calcular_alertas_de_sancion(self.sancion, datetime(2026, 11, 23, 1))['revisar_custodia'])
        self.assertTrue(calcular_alertas_de_sancion(self.sancion, datetime(2026, 11, 23, 5))['revisar_custodia'])
        self.sancion['fecha_devolucion'] = datetime(2026, 11, 23, 14)
        self.assertTrue(calcular_alertas_de_sancion(self.sancion, datetime(2026, 11, 23, 15))['revisar_custodia'])
        self.sancion['tipo'] = 'CUSTODIA'
        self.assertFalse(calcular_alertas_de_sancion(self.sancion, datetime(2026, 11, 23, 15))['revisar_custodia'])
