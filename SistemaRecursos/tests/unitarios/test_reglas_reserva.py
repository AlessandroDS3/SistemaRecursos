"""Cierre de reservas y validación de fechas en los límites admitidos."""

from datetime import datetime, timedelta
import unittest
from unittest.mock import MagicMock

from dominio.compartido.validacion import fecha_local
from dominio.gestion_control.politica_prestamo import ConfiguracionReservas, HorarioAtencion, PoliticaPrestamo
from servicios.prestamos.servicio_reserva import ServicioAplicacionReserva


class CierreReservaTest(unittest.TestCase):
    def setUp(self):
        self.ahora = datetime(2026, 11, 23, 15)
        self.reserva = dict(
            id_reserva=3, id_recurso=1, id_bien=7, dni_persona='20000001',
            estado='LISTA_PARA_RETIRO', fecha_requerida=self.ahora - timedelta(days=1),
            fecha_limite_vencimiento=self.ahora - timedelta(seconds=1),
        )
        self.repo = MagicMock()
        self.repo.transaccion.return_value.__enter__.return_value = self.repo
        self.repo.consultar_reserva.side_effect = lambda *args, **kwargs: dict(self.reserva)
        self.repo.consultar_fecha_actual.return_value = self.ahora
        self.repo.consultar_cuenta_actor.return_value = dict(
            dni_persona='10000002', estado_cuenta='ACTIVA', estado_persona='ACTIVA',
            permisos={'PRESTAMOS_GESTIONAR'},
        )
        self.repo.actualizar_reserva.side_effect = lambda identificador, cambios: self.reserva.update(cambios)
        self.servicio = ServicioAplicacionReserva(self.repo)

    def test_cierre_manual_libera_bien_y_conserva_vinculo_historico(self):
        for accion, estado in (('cancelar', 'CANCELADA'), ('rechazar', 'RECHAZADA'),
                               ('expirar', 'EXPIRADA')):
            with self.subTest(accion=accion):
                self.reserva.update(estado='LISTA_PARA_RETIRO', id_bien=7)
                self.repo.cambiar_estado_bien_reservado.reset_mock()
                getattr(self.servicio, accion + '_reserva')(3, {'motivo': 'Cierre solicitado'}, 2)
                self.assertEqual(self.reserva['estado'], estado)
                self.assertEqual(self.reserva['id_bien'], 7)
                self.repo.cambiar_estado_bien_reservado.assert_called_once_with(
                    7, 'DISPONIBLE', 'RESERVADO', '10000002', 3,
                )

    def test_expiracion_automatica_conserva_vinculo_y_no_libera_dos_veces(self):
        self.repo.consultar_reservas_vencidas.return_value = [dict(id_reserva=3)]
        self.assertEqual(self.servicio.expirar_reservas_vencidas(), 1)
        self.assertEqual(self.reserva['estado'], 'EXPIRADA')
        self.assertEqual(self.reserva['id_bien'], 7)
        self.assertEqual(self.servicio.expirar_reservas_vencidas(), 0)
        self.repo.cambiar_estado_bien_reservado.assert_called_once_with(
            7, 'DISPONIBLE', 'RESERVADO', None, 3,
        )

    def test_cierre_sin_bien_no_modifica_inventario(self):
        self.reserva.update(estado='EN_ESPERA', id_bien=None)
        self.servicio.cancelar_reserva(3, {}, 2)
        self.assertEqual(self.reserva['estado'], 'CANCELADA')
        self.assertIsNone(self.reserva['id_bien'])
        self.repo.cambiar_estado_bien_reservado.assert_not_called()


class FechasReservaTest(unittest.TestCase):
    def test_plazo_en_dias_vence_el_siguiente_dia_de_atencion(self):
        politica = PoliticaPrestamo(tipo_persona='ESTUDIANTE', id_categoria=1, plazo_maximo=1, unidad_plazo='DIAS')
        entrega = fecha_local('2026-11-27T10:00')
        self.assertEqual(politica.vencimiento(entrega, HorarioAtencion()), fecha_local('2026-11-30T10:00'))

    def test_horario_valida_el_dia_y_las_horas_en_lima(self):
        horario = HorarioAtencion()
        for fecha in ('2026-11-28T10:00', '2026-11-27T16:00', '2026-11-27T07:59'):
            with self.subTest(fecha=fecha), self.assertRaises(ValueError):
                horario.cierre(fecha_local(fecha))
        self.assertEqual(horario.cierre(fecha_local('2026-11-27T08:00')), datetime(2026, 11, 27, 21))
        con_sabado = HorarioAtencion(dias_atencion=0b0111111)
        self.assertEqual(con_sabado.cierre(fecha_local('2026-11-28T10:00')), datetime(2026, 11, 28, 21))

    def test_conversion_local_fuera_de_rango_es_error_de_validacion(self):
        with self.assertRaises(ValueError):
            fecha_local('9999-12-31T23:59')

    def test_vencimiento_fuera_de_rango_es_error_de_validacion(self):
        configuracion = ConfiguracionReservas()
        for etapa, fecha in (('espera', '9999-12-30T10:00'),
                             ('retiro', '9999-12-31T10:00')):
            with self.subTest(etapa=etapa), self.assertRaises(ValueError):
                configuracion.vencimiento(fecha_local(fecha), etapa)

    def test_fechas_validas_conservan_zona_y_plazo(self):
        fecha = fecha_local('2026-11-23T10:00')
        self.assertEqual(fecha, datetime(2026, 11, 23, 15))
        configuracion = ConfiguracionReservas()
        self.assertEqual(configuracion.vencimiento(fecha, 'espera'), fecha + timedelta(days=2))
        self.assertEqual(configuracion.vencimiento(fecha, 'retiro'), fecha + timedelta(hours=24))

    def test_fecha_limite_representable_sigue_siendo_valida(self):
        fecha = fecha_local('9999-12-29T10:00')
        self.assertEqual(
            ConfiguracionReservas().vencimiento(fecha, 'espera'), datetime(9999, 12, 31, 15),
        )
