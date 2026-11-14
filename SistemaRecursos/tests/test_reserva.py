from datetime import timedelta
from unittest.mock import patch
from dominio.compartido.validacion import Conflicto
from caso_mysql import CasoMySQL


class OperacionesReserva(CasoMySQL):
    def test_filtros_y_vencimiento_manual_con_motivo(self):
        identificador = self.reservar()
        reservas = self.servicios['reservas']
        self.assertEqual(
            len(reservas.consultar_reservas('02167885', {'estado': 'EN_ESPERA', 'q': 'Equipo'})), 1
        )
        with self.assertRaises(ValueError):
            reservas.expirar_reserva(identificador, {}, 2)
        reservas.expirar_reserva(identificador, dict(motivo='No se presentará al retiro'), 2)
        self.assertEqual(reservas.consultar_reservas('02167885', {'estado': 'EN_ESPERA'}), [])
        self.assertEqual(
            reservas.consultar_reserva(identificador, '02167885')['estado'], 'EXPIRADA'
        )

    def test_preparar_y_entregar_crea_un_prestamo_con_mismas_reglas(self):
        identificador = self.reservar()
        reservas = self.servicios['reservas']
        reservas.preparar_reserva(identificador, {}, 2)
        reserva = reservas.consultar_reserva(identificador, '02167885')
        self.assertEqual(reserva['estado'], 'LISTA_PARA_RETIRO')
        self.assertEqual(reserva['recurso_bien'], reserva['id_recurso'])
        prestamo = reservas.entregar_reserva(identificador, {'acepta_condiciones': '1'}, 2)
        self.assertEqual(
            reservas.consultar_reserva(identificador, '02167885')['id_prestamo_ref'], prestamo
        )
        self.assertEqual(self.prestamo(prestamo)['detalles'][0]['id_bien'], reserva['id_bien'])

    def test_reserva_no_saltea_cola_y_cancelar_recalcula_posicion(self):
        primera = self.reservar()
        self.servicios['cuentas'].registrar_cuenta('99000001', 'segundo', 'UsuarioPrueba2026!', 1)
        segunda = self.servicios['reservas'].registrar_reserva(
            dict(id_recurso=1, tipo_gestion='PRESTAMO', acepta_condiciones='1'), 4
        )
        reservas = self.servicios['reservas']
        with self.assertRaises(Conflicto):
            reservas.preparar_reserva(segunda, {}, 2)
        reservas.cancelar_reserva(primera, {}, 3)
        filas = {r['id_reserva']: r for r in reservas.consultar_reservas()}
        self.assertEqual(filas[segunda]['posicion'], 1)
        reservas.preparar_reserva(segunda, {}, 2)

    def test_solicitud_duplicada_no_se_registra(self):
        self.reservar()
        with self.assertRaises(Conflicto):
            self.reservar()
        self.assertEqual(self.fila('SELECT COUNT(*) FROM reserva'), (1,))

    def test_preparacion_revalida_la_elegibilidad(self):
        identificador = self.reservar()
        self.ejecutar("UPDATE estudiante SET estado_matricula='NO_VIGENTE' WHERE dni='02167885'")
        with self.assertRaises(ValueError):
            self.servicios['reservas'].preparar_reserva(identificador, {}, 2)
        self.assertEqual(
            self.fila("SELECT COUNT(*) FROM bien_material WHERE estado='RESERVADO'"), (0,)
        )

    def test_cancelar_reserva_preparada_libera_bien(self):
        identificador = self.reservar()
        self.servicios['reservas'].preparar_reserva(identificador, {}, 2)
        bien = self.servicios['reservas'].consultar_reserva(identificador, '02167885')['id_bien']
        self.servicios['reservas'].cancelar_reserva(identificador, {}, 3)
        self.assertEqual(
            self.fila('SELECT estado FROM bien_material WHERE id_bien=%s', (bien,)), ('DISPONIBLE',)
        )

    def test_rechazar_preparada_exige_motivo_y_libera_bien(self):
        identificador = self.reservar()
        reservas = self.servicios['reservas']
        reservas.preparar_reserva(identificador, {}, 2)
        bien = reservas.consultar_reserva(identificador, '02167885')['id_bien']
        with self.assertRaises(ValueError):
            reservas.rechazar_reserva(identificador, {}, 2)
        self.assertEqual(
            self.fila('SELECT estado FROM bien_material WHERE id_bien=%s', (bien,)), ('RESERVADO',)
        )
        reservas.rechazar_reserva(identificador, {'motivo': 'Solicitud no autorizada'}, 2)
        reserva = reservas.consultar_reserva(identificador, '02167885')
        self.assertEqual(reserva['estado'], 'RECHAZADA')
        self.assertIsNone(reserva['id_bien'])
        self.assertEqual(reserva['historial'][0]['observacion'], 'Solicitud no autorizada')
        self.assertEqual(
            self.fila('SELECT estado FROM bien_material WHERE id_bien=%s', (bien,)), ('DISPONIBLE',)
        )

    def test_sancion_posterior_a_preparacion_impide_ambos_caminos_de_entrega(self):
        prestamo = self.prestar([3])
        identificador = self.reservar()
        reservas = self.servicios['reservas']
        reservas.preparar_reserva(identificador, {}, 2)
        self.ejecutar(
            'UPDATE detalle_prestamo SET fecha_limite_devolucion=DATE_SUB(UTC_TIMESTAMP(),INTERVAL 2 DAY)'
        )
        self.assertEqual(self.servicios['sanciones'].aplicar_sanciones_por_vencimiento(), 1)
        # Aísla la sanción: el préstamo deja de estar vencido, la sanción sigue activa.
        self.ejecutar(
            'UPDATE detalle_prestamo SET fecha_limite_devolucion=DATE_ADD(UTC_TIMESTAMP(),INTERVAL 2 DAY)'
        )
        with self.assertRaisesRegex(Conflicto, 'sanción activa'):
            reservas.entregar_reserva(identificador, {'acepta_condiciones': '1'}, 2)
        with self.assertRaisesRegex(Conflicto, 'sanción activa'):
            self.prestar([2])
        reserva = reservas.consultar_reserva(identificador, '02167885')
        self.assertEqual(reserva['estado'], 'LISTA_PARA_RETIRO')
        self.assertEqual(reserva['estado_bien'], 'RESERVADO')
        self.assertIsNone(reserva['id_prestamo_ref'])
        self.assertEqual(self.fila('SELECT id_prestamo FROM prestamo'), (prestamo,))

    def test_error_despues_de_entregar_revierte_prestamo_y_conserva_reserva(self):
        identificador = self.reservar()
        reservas = self.servicios['reservas']
        reservas.preparar_reserva(identificador, {}, 2)
        with patch(
            'repositorio.repositorio_reserva_sql.RepositorioReservaSQL.actualizar_reserva',
            side_effect=RuntimeError('Fallo al cerrar reserva'),
        ):
            with self.assertRaises(RuntimeError):
                reservas.entregar_reserva(identificador, {'acepta_condiciones': '1'}, 2)
        self.assertEqual(self.fila('SELECT COUNT(*) FROM prestamo'), (0,))
        self.assertEqual(
            reservas.consultar_reserva(identificador, '02167885')['estado_bien'], 'RESERVADO'
        )

    def test_plazo_vencido_expira_y_libera_sin_escrituras_en_get(self):
        identificador = self.reservar()
        reservas = self.servicios['reservas']
        reservas.preparar_reserva(identificador, {}, 2)
        self.ejecutar(
            'UPDATE reserva SET fecha_limite_vencimiento=DATE_SUB(UTC_TIMESTAMP(),INTERVAL 2 DAY)'
        )
        self.login()
        self.assertEqual(self.cliente.get('/reservas').status_code, 200)
        self.assertEqual(
            reservas.consultar_reserva(identificador, '02167885')['estado'], 'LISTA_PARA_RETIRO'
        )
        self.assertEqual(reservas.expirar_reservas_vencidas(), 1)
        self.assertEqual(
            reservas.consultar_reserva(identificador, '02167885')['estado'], 'EXPIRADA'
        )
        self.assertEqual(reservas.expirar_reservas_vencidas(), 0)

    def test_reserva_futura_y_privacidad(self):
        fecha = (self.consultar_fecha_actual + timedelta(days=1, hours=-5)).isoformat(
            timespec='minutes'
        )
        identificador = self.reservar(tipo_gestion='RESERVA', fecha_requerida=fecha)
        with self.assertRaises(Conflicto):
            self.servicios['reservas'].preparar_reserva(identificador, {}, 2)
        with self.assertRaises(PermissionError):
            self.servicios['reservas'].consultar_reserva(identificador, '99000001')
        with self.assertRaises(PermissionError):
            self.servicios['reservas'].preparar_reserva(identificador, {}, 3)

    def test_no_entregar_bien_ajeno_al_recurso_reservado(self):
        identificador = self.reservar()
        reservas = self.servicios['reservas']
        reservas.preparar_reserva(identificador, {}, 2)
        self.ejecutar(
            'UPDATE bien_material SET id_recurso=2 WHERE id_bien=(SELECT id_bien FROM reserva WHERE id_reserva=%s)',
            (identificador,),
        )
        with self.assertRaises(Conflicto):
            reservas.entregar_reserva(identificador, {'acepta_condiciones': '1'}, 2)
        self.assertEqual(self.fila('SELECT COUNT(*) FROM prestamo'), (0,))
