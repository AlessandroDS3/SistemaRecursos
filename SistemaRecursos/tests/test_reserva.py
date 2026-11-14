from datetime import timedelta
from unittest.mock import patch
from dominio.compartido.validacion import Conflicto
from caso_mysql import CasoMySQL


class OperacionesReserva(CasoMySQL):
    def test_filtros_y_vencimiento_manual_con_motivo(self):
        identificador = self.reservar()
        reservas = self.servicios['reservas']
        self.assertEqual(
            len(reservas.listar('02167885', {'estado': 'EN_ESPERA', 'q': 'Equipo'})), 1
        )
        with self.assertRaises(ValueError):
            reservas.actuar(identificador, 'expirar', {}, 2)
        reservas.actuar(identificador, 'expirar', dict(motivo='No se presentará al retiro'), 2)
        self.assertEqual(reservas.listar('02167885', {'estado': 'EN_ESPERA'}), [])
        self.assertEqual(reservas.consultar(identificador, '02167885')['estado'], 'EXPIRADA')

    def test_preparar_y_entregar_crea_un_prestamo_con_mismas_reglas(self):
        identificador = self.reservar()
        reservas = self.servicios['reservas']
        reservas.actuar(identificador, 'preparar', {}, 2)
        reserva = reservas.consultar(identificador, '02167885')
        self.assertEqual(reserva['estado'], 'LISTA_PARA_RETIRO')
        self.assertEqual(reserva['recurso_bien'], reserva['id_recurso'])
        prestamo = reservas.actuar(identificador, 'entregar', {'acepta_condiciones': '1'}, 2)
        self.assertEqual(reservas.consultar(identificador, '02167885')['id_prestamo_ref'], prestamo)
        self.assertEqual(self.prestamo(prestamo)['detalles'][0]['id_bien'], reserva['id_bien'])

    def test_reserva_no_saltea_cola_y_cancelar_recalcula_posicion(self):
        primera = self.reservar()
        self.servicios['cuentas'].crear('99000001', 'segundo', 'UsuarioPrueba2026!', 1)
        segunda = self.servicios['reservas'].registrar(
            dict(id_recurso=1, tipo_gestion='PRESTAMO', acepta_condiciones='1'), 4
        )
        reservas = self.servicios['reservas']
        with self.assertRaises(Conflicto):
            reservas.actuar(segunda, 'preparar', {}, 2)
        reservas.actuar(primera, 'cancelar', {}, 3)
        filas = {r['id_reserva']: r for r in reservas.listar()}
        self.assertEqual(filas[segunda]['posicion'], 1)
        reservas.actuar(segunda, 'preparar', {}, 2)

    def test_solicitud_duplicada_no_se_registra(self):
        self.reservar()
        with self.assertRaises(Conflicto):
            self.reservar()
        self.assertEqual(self.fila('SELECT COUNT(*) FROM reserva'), (1,))

    def test_preparacion_revalida_la_elegibilidad(self):
        identificador = self.reservar()
        self.ejecutar("UPDATE estudiante SET estado_matricula='NO_VIGENTE' WHERE dni='02167885'")
        with self.assertRaises(ValueError):
            self.servicios['reservas'].actuar(identificador, 'preparar', {}, 2)
        self.assertEqual(
            self.fila("SELECT COUNT(*) FROM bien_material WHERE estado='RESERVADO'"), (0,)
        )

    def test_cancelar_reserva_preparada_libera_bien(self):
        identificador = self.reservar()
        self.servicios['reservas'].actuar(identificador, 'preparar', {}, 2)
        bien = self.servicios['reservas'].consultar(identificador, '02167885')['id_bien']
        self.servicios['reservas'].actuar(identificador, 'cancelar', {}, 3)
        self.assertEqual(
            self.fila('SELECT estado FROM bien_material WHERE id_bien=%s', (bien,)), ('DISPONIBLE',)
        )

    def test_error_despues_de_entregar_revierte_prestamo_y_conserva_reserva(self):
        identificador = self.reservar()
        reservas = self.servicios['reservas']
        reservas.actuar(identificador, 'preparar', {}, 2)
        with patch(
            'repositorio.repositorio_reserva_sql.RepositorioReservaSQL.cambiar',
            side_effect=RuntimeError('Fallo al cerrar reserva'),
        ):
            with self.assertRaises(RuntimeError):
                reservas.actuar(identificador, 'entregar', {'acepta_condiciones': '1'}, 2)
        self.assertEqual(self.fila('SELECT COUNT(*) FROM prestamo'), (0,))
        self.assertEqual(reservas.consultar(identificador, '02167885')['estado_bien'], 'RESERVADO')

    def test_plazo_vencido_expira_y_libera_sin_escrituras_en_get(self):
        identificador = self.reservar()
        reservas = self.servicios['reservas']
        reservas.actuar(identificador, 'preparar', {}, 2)
        self.ejecutar(
            'UPDATE reserva SET fecha_limite_vencimiento=DATE_SUB(UTC_TIMESTAMP(),INTERVAL 2 DAY)'
        )
        self.login()
        self.assertEqual(self.cliente.get('/reservas').status_code, 200)
        self.assertEqual(
            reservas.consultar(identificador, '02167885')['estado'], 'LISTA_PARA_RETIRO'
        )
        self.assertEqual(reservas.procesar_vencimientos(), 1)
        self.assertEqual(reservas.consultar(identificador, '02167885')['estado'], 'EXPIRADA')
        self.assertEqual(reservas.procesar_vencimientos(), 0)

    def test_reserva_futura_y_privacidad(self):
        fecha = (self.ahora + timedelta(days=1, hours=-5)).isoformat(timespec='minutes')
        identificador = self.reservar(tipo_gestion='RESERVA', fecha_requerida=fecha)
        with self.assertRaises(Conflicto):
            self.servicios['reservas'].actuar(identificador, 'preparar', {}, 2)
        with self.assertRaises(PermissionError):
            self.servicios['reservas'].consultar(identificador, '99000001')
        with self.assertRaises(PermissionError):
            self.servicios['reservas'].actuar(identificador, 'preparar', {}, 3)

    def test_no_entregar_bien_ajeno_al_recurso_reservado(self):
        identificador = self.reservar()
        reservas = self.servicios['reservas']
        reservas.actuar(identificador, 'preparar', {}, 2)
        self.ejecutar(
            'UPDATE bien_material SET id_recurso=2 WHERE id_bien=(SELECT id_bien FROM reserva WHERE id_reserva=%s)',
            (identificador,),
        )
        with self.assertRaises(Conflicto):
            reservas.actuar(identificador, 'entregar', {'acepta_condiciones': '1'}, 2)
        self.assertEqual(self.fila('SELECT COUNT(*) FROM prestamo'), (0,))
