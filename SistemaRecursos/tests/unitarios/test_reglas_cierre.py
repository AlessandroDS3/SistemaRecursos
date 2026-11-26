"""Reglas sin base de datos de SEG-01, SEG-02, AUT-01, AUT-02, MAN-01, AMP-01 y REP-01."""

from datetime import datetime, timedelta
import unittest

from dominio.compartido.validacion import LIMA, Conflicto, NoEncontrado
from dominio.gestion_personas_usuarios.sesion import (
    DURACION_MAXIMA,
    INACTIVIDAD_MAXIMA,
    AccesoBloqueado,
    LimitadorIntentos,
    calcular_huella_del_token_de_sesion,
    sesion_vigente,
)
from dominio.gestion_prestamos.solicitud_ampliacion import (
    SolicitudAmpliacion,
    exigir_solicitud_ampliacion_pendiente,
    exigir_titular_del_prestamo_para_ampliacion,
)
from dominio.gestion_recursos.bien_material import BienMaterial, generar_identificador_sistema
from dominio.gestion_recursos.mantenimiento import (
    AperturaMantenimiento,
    CierreMantenimiento,
    validar_apertura_mantenimiento,
)
from presentacion.reportes.csv_reportes import _sanear_valor_para_csv


class Reloj:
    def __init__(self):
        self.ahora = datetime(2026, 11, 24, 10, 0)

    def __call__(self):
        return self.ahora


class LimitadorIntentosTest(unittest.TestCase):
    def test_bloquea_tras_el_maximo_y_libera_despues_del_tiempo(self):
        reloj = Reloj()
        limitador = LimitadorIntentos(maximo=5, reloj=reloj)
        for _ in range(4):
            limitador.registrar_intento_de_acceso_fallido('ana')
        self.assertEqual(limitador.calcular_minutos_de_bloqueo_restantes('ana'), 0)
        limitador.registrar_intento_de_acceso_fallido('ana')
        self.assertEqual(limitador.calcular_minutos_de_bloqueo_restantes('ana'), 15)
        reloj.ahora += timedelta(minutes=15, seconds=1)
        self.assertEqual(limitador.calcular_minutos_de_bloqueo_restantes('ana'), 0)

    def test_claves_independientes_y_limpieza_tras_acceso_correcto(self):
        limitador = LimitadorIntentos(maximo=2, reloj=Reloj())
        limitador.registrar_intento_de_acceso_fallido('ana')
        limitador.registrar_intento_de_acceso_fallido('ana')
        self.assertGreater(limitador.calcular_minutos_de_bloqueo_restantes('ana'), 0)
        self.assertEqual(limitador.calcular_minutos_de_bloqueo_restantes('luis'), 0)
        limitador.borrar_intentos_y_bloqueo('ana')
        self.assertEqual(limitador.calcular_minutos_de_bloqueo_restantes('ana'), 0)

    def test_fallos_fuera_de_la_ventana_no_se_acumulan(self):
        reloj = Reloj()
        limitador = LimitadorIntentos(maximo=3, reloj=reloj)
        limitador.registrar_intento_de_acceso_fallido('ana')
        limitador.registrar_intento_de_acceso_fallido('ana')
        reloj.ahora += timedelta(minutes=16)
        limitador.registrar_intento_de_acceso_fallido('ana')
        self.assertEqual(limitador.calcular_minutos_de_bloqueo_restantes('ana'), 0)

    def test_mensaje_no_revela_si_la_cuenta_existe(self):
        mensaje = str(AccesoBloqueado(3))
        self.assertIn('3 minutos', mensaje)
        self.assertNotIn('usuario', mensaje.lower())


class SesionVigenteTest(unittest.TestCase):
    def setUp(self):
        self.ahora = datetime(2026, 11, 24, 12, 0)
        self.fila = dict(id_usuario=7, fecha_inicio=self.ahora - timedelta(hours=1),
                         ultima_actividad=self.ahora - timedelta(minutes=5), fecha_cierre=None)

    def test_sesion_activa_y_propia(self):
        self.assertTrue(sesion_vigente(self.fila, 7, self.ahora))

    def test_rechaza_otra_cuenta_cerrada_inactiva_o_demasiado_larga(self):
        self.assertFalse(sesion_vigente(self.fila, 8, self.ahora))
        self.assertFalse(sesion_vigente(None, 7, self.ahora))
        self.assertFalse(sesion_vigente(dict(self.fila, fecha_cierre=self.ahora), 7, self.ahora))
        inactiva = dict(self.fila, ultima_actividad=self.ahora - INACTIVIDAD_MAXIMA - timedelta(seconds=1))
        self.assertFalse(sesion_vigente(inactiva, 7, self.ahora))
        larga = dict(self.fila, fecha_inicio=self.ahora - DURACION_MAXIMA - timedelta(seconds=1))
        self.assertFalse(sesion_vigente(larga, 7, self.ahora))

    def test_huella_de_sesion_no_expone_el_token(self):
        self.assertNotEqual(calcular_huella_del_token_de_sesion('abc'), 'abc')
        self.assertEqual(len(calcular_huella_del_token_de_sesion('abc')), 64)


class BienMaterialCierreTest(unittest.TestCase):
    def test_identificador_con_formato_y_sin_caracteres_ambiguos(self):
        valores = {generar_identificador_sistema(2026) for _ in range(500)}
        self.assertGreater(len(valores), 495)
        for valor in valores:
            self.assertRegex(valor, r'^SR-2026-[2-9A-HJ-NP-Z]{6}$')

    def test_fecha_de_adquisicion_no_futura(self):
        manana = (datetime.now(LIMA) + timedelta(days=1)).date().isoformat()
        with self.assertRaisesRegex(ValueError, 'futura'):
            BienMaterial(id_recurso=1, codigo_inventario='X-1', fecha_adquisicion=manana)
        hoy = datetime.now(LIMA).date()
        self.assertEqual(
            BienMaterial(id_recurso=1, codigo_inventario='X-1', fecha_adquisicion=hoy).fecha_adquisicion,
            hoy,
        )
        self.assertIsNone(BienMaterial(id_recurso=1, codigo_inventario='X-1').fecha_adquisicion)


class MantenimientoTest(unittest.TestCase):
    def test_apertura_valida_tipo_motivo_y_fecha(self):
        with self.assertRaises(ValueError):
            AperturaMantenimiento(tipo='OTRO', motivo='Revisión')
        with self.assertRaises(ValueError):
            AperturaMantenimiento(tipo='PREVENTIVO', motivo='  ')
        ayer = (datetime.now(LIMA) - timedelta(days=1)).date().isoformat()
        with self.assertRaisesRegex(ValueError, 'anterior a hoy'):
            AperturaMantenimiento(tipo='PREVENTIVO', motivo='Limpieza', fecha_fin_estimada=ayer)
        apertura = AperturaMantenimiento(tipo='CORRECTIVO', motivo='Pantalla', fecha_fin_estimada='')
        self.assertIsNone(apertura.fecha_fin_estimada)

    def test_cierre_exige_resultado_y_observacion(self):
        with self.assertRaises(ValueError):
            CierreMantenimiento(resultado='PRESTADO', observacion='ok')
        with self.assertRaises(ValueError):
            CierreMantenimiento(resultado='DISPONIBLE', observacion='')

    def test_no_abre_con_prestamo_pendiente_ni_dos_veces(self):
        with self.assertRaises(Conflicto):
            validar_apertura_mantenimiento('DISPONIBLE', {'id_mantenimiento': 1}, None)
        with self.assertRaises(Conflicto):
            validar_apertura_mantenimiento('PRESTADO', None, {'id_prestamo': 3})
        with self.assertRaises(Conflicto):
            validar_apertura_mantenimiento('PERDIDO', None, None)
        validar_apertura_mantenimiento('DANADO', None, None)


class SolicitudAmpliacionTest(unittest.TestCase):
    def test_solicitud_de_ampliacion_valida_datos_estado_y_titular(self):
        with self.assertRaises(ValueError):
            SolicitudAmpliacion(cantidad='0', unidad='DIAS', motivo='Proyecto')
        with self.assertRaises(ValueError):
            SolicitudAmpliacion(cantidad='2', unidad='SEMANAS', motivo='Proyecto')
        with self.assertRaises(ValueError):
            SolicitudAmpliacion(cantidad='2', unidad='DIAS', motivo='')
        with self.assertRaises(NoEncontrado):
            exigir_solicitud_ampliacion_pendiente(None)
        with self.assertRaises(Conflicto):
            exigir_solicitud_ampliacion_pendiente({'estado': 'APROBADA'})
        with self.assertRaises(PermissionError):
            exigir_titular_del_prestamo_para_ampliacion('20000001', '20000002')
        exigir_titular_del_prestamo_para_ampliacion('20000001', '20000001')


class CeldasCsvTest(unittest.TestCase):
    def test_neutraliza_formulas_y_conserva_texto(self):
        for peligroso in ('=SUMA(A1)', '+1', '-2', '@x', ' =1', '\tA'):
            self.assertTrue(_sanear_valor_para_csv(peligroso).startswith("'"), peligroso)
        self.assertEqual(_sanear_valor_para_csv('Cámara ñandú'), 'Cámara ñandú')
        self.assertEqual(_sanear_valor_para_csv(None), '')


if __name__ == '__main__':
    unittest.main()
