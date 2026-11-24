"""Reglas de gravedad, cumplimiento y plazos de sanciones."""

from datetime import datetime, timedelta
import unittest

from dominio.compartido.validacion import Conflicto
from dominio.gestion_control.sancion import (
    ConfiguracionSanciones, alertas_revision, puede_cumplirse, validar_levantamiento,
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

    def test_cumplir_exige_tiempo_y_regularizacion(self):
        self.assertFalse(puede_cumplirse(self.sancion, self.ahora + timedelta(days=40)))
        self.sancion['fecha_regularizacion'] = self.ahora
        self.assertFalse(puede_cumplirse(self.sancion, self.ahora))
        self.assertTrue(puede_cumplirse(self.sancion, self.ahora + timedelta(days=14)))
        self.sancion.update(gravedad='MUY_GRAVE', fecha_fin=None)
        self.assertFalse(puede_cumplirse(self.sancion, self.ahora + timedelta(days=999)))

    def test_encargado_puede_perdonar_leve_regularizada_sin_limite_de_minutos(self):
        cuenta = dict(rol='ENCARGADO_PRESTAMOS')
        with self.assertRaises(Conflicto):
            validar_levantamiento(self.sancion, 'Recepción demorada por el encargado', self.ahora, cuenta)
        self.sancion['fecha_regularizacion'] = self.ahora
        self.assertTrue(validar_levantamiento(self.sancion, 'Demora de recepción', self.ahora, cuenta))
        self.sancion['gravedad'] = 'GRAVE'
        with self.assertRaises(Conflicto):
            validar_levantamiento(self.sancion, 'Reparación aceptada', self.ahora, cuenta)

    def test_alerta_perdida_no_modifica_estado_y_cuenta_plazos_de_la_sancion(self):
        resultado = alertas_revision(self.sancion, self.ahora + timedelta(days=20))
        self.assertFalse(resultado['posible_perdida'])
        self.assertTrue(alertas_revision(self.sancion, self.ahora + timedelta(days=21))['posible_perdida'])
        self.assertEqual(self.sancion['gravedad'], 'LEVE')
        self.sancion['fecha_devolucion'] = self.ahora
        self.assertFalse(alertas_revision(self.sancion, self.ahora + timedelta(days=30))['posible_perdida'])

    def test_custodia_usa_fecha_de_lima(self):
        self.sancion['fecha_limite_devolucion'] = datetime(2026, 11, 22, 21)  # 16:00 Lima
        self.assertFalse(alertas_revision(self.sancion, datetime(2026, 11, 23, 1))['revisar_custodia'])
        self.assertTrue(alertas_revision(self.sancion, datetime(2026, 11, 23, 5))['revisar_custodia'])
        self.sancion['fecha_devolucion'] = datetime(2026, 11, 23, 14)
        self.assertTrue(alertas_revision(self.sancion, datetime(2026, 11, 23, 15))['revisar_custodia'])
        self.sancion['tipo'] = 'CUSTODIA'
        self.assertFalse(alertas_revision(self.sancion, datetime(2026, 11, 23, 15))['revisar_custodia'])
