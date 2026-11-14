import re
from unittest.mock import patch
from mysql.connector import DatabaseError
from dominio.gestion_prestamos.reserva import ESTADOS_RESERVA
from caso_mysql import CasoMySQL


class RecorridosWeb(CasoMySQL):
    def test_filtro_y_botones_reserva_reflejan_estados_del_dominio(self):
        identificador = self.reservar()
        self.login('encargado1', 'EncargadoPrueba2026!')
        pagina = self.cliente.get('/reservas?estado=EN_ESPERA').get_data(as_text=True)
        filtro = re.search(r'<select name="estado">(.*?)</select>', pagina, re.DOTALL).group(1)
        opciones = re.findall(r'<option[^>]*>([^<]*)</option>', filtro)
        self.assertEqual(opciones, ['Todos', *ESTADOS_RESERVA])
        url = f'/reservas/{identificador}'
        pagina = self.cliente.get(url).get_data(as_text=True)
        self.assertIn(f'action="{url}/preparar"', pagina)
        self.assertNotIn(f'action="{url}/entregar"', pagina)
        self.post(url + '/preparar')
        pagina = self.cliente.get(url).get_data(as_text=True)
        self.assertNotIn(f'action="{url}/preparar"', pagina)
        self.assertIn(f'action="{url}/entregar"', pagina)
        self.assertIn(f'action="{url}/cancelar"', pagina)
        self.post(url + '/cancelar')
        pagina = self.cliente.get(url).get_data(as_text=True)
        for accion in ('preparar', 'entregar', 'cancelar', 'expirar'):
            self.assertNotIn(f'action="{url}/{accion}"', pagina)

    def test_consultar_condiciones_no_escribe_y_respeta_permiso(self):
        self.login('encargado1', 'EncargadoPrueba2026!')
        respuesta = self.cliente.get('/prestamos/condiciones?dni_persona=02167885')
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.get_json()
        self.assertEqual(datos['limite'], 4)
        self.assertEqual(datos['politicas'][0]['plazo_maximo'], 2)
        self.assertEqual(datos['horario'], dict(apertura='08:00', cierre='16:00'))
        self.assertEqual(self.fila('SELECT COUNT(*) FROM historial_estado'), (0,))
        self.post('/logout')
        self.login('usuario1', 'UsuarioPrueba2026!')
        self.assertEqual(
            self.cliente.get('/prestamos/condiciones?dni_persona=02167885').status_code, 403
        )
        pagina = self.cliente.get('/reservas/nueva').get_data(as_text=True)
        self.assertIn('Plazo máximo: 2 dias', pagina)

    def test_entrega_ampliacion_y_devolucion_desde_formularios(self):
        self.login('encargado1', 'EncargadoPrueba2026!')
        respuesta = self.post(
            '/prestamos/nuevo',
            dict(
                dni_persona='02167885',
                bienes=['2'],
                acepta_condiciones='1',
                tipo_prestamo='GRUPAL',
                participantes='99000001',
            ),
        )
        self.assertEqual(respuesta.status_code, 302)
        pagina = self.cliente.get(respuesta.location)
        self.assertEqual(pagina.status_code, 200)
        identificador = int(respuesta.location.rsplit('/', 1)[1])
        detalle = self.prestamo(identificador)['detalles'][0]['id_detalle']
        fecha = re.search(
            r'name="fecha_actual"\s+value="([^"]+)"', pagina.get_data(as_text=True)
        ).group(1)
        respuesta = self.post(
            f'/prestamos/{identificador}/detalles/{detalle}/ampliar',
            dict(cantidad='1', unidad='DIAS', fecha_actual=fecha),
        )
        self.assertEqual(respuesta.status_code, 302)
        url_devolucion = f'/prestamos/{identificador}/devolver'
        self.assertEqual(
            self.cliente.post(url_devolucion, data={'detalles': [str(detalle)]}).status_code, 400
        )
        respuesta = self.post(
            url_devolucion, dict(detalles=[str(detalle)], **{f'condicion_{detalle}': 'BUENO'})
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.prestamo(identificador)['estado_actual'], 'DEVUELTO')

    def test_reserva_del_usuario_y_atencion_del_encargado(self):
        self.login('usuario1', 'UsuarioPrueba2026!')
        respuesta = self.post(
            '/reservas/nueva', dict(id_recurso='1', tipo_gestion='PRESTAMO', acepta_condiciones='1')
        )
        self.assertEqual(respuesta.status_code, 302)
        url_reserva = respuesta.location
        self.assertEqual(self.cliente.get(url_reserva).status_code, 200)
        self.post('/logout')
        self.login('encargado1', 'EncargadoPrueba2026!')
        self.assertEqual(self.post(url_reserva + '/preparar').status_code, 302)
        respuesta = self.post(url_reserva + '/entregar', dict(acepta_condiciones='1'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/prestamos/', respuesta.location)
        self.assertEqual(self.cliente.get(respuesta.location).status_code, 200)

    def test_altas_persona_cuenta_recurso_y_bien(self):
        self.login()
        respuesta = self.post(
            '/personas/nueva',
            dict(
                dni='77777777',
                nombres='Persona',
                apellidos='Nueva',
                correo='nueva@ejemplo.com',
                tipo='ESTUDIANTE',
                cui='77777777',
                ciclo='1',
                estado_matricula='VIGENTE',
            ),
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(
            self.post(
                '/cuentas/77777777/nueva', dict(nombre_usuario='nueva', clave='NuevaClave2026!')
            ).status_code,
            302,
        )
        respuesta = self.post(
            '/recursos/nuevo',
            dict(nombre='Recurso nuevo', id_categoria='1', codigo_inventario='INV-NUEVO'),
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.cliente.get(respuesta.location).status_code, 200)
        bien = self.fila("SELECT id_bien FROM bien_material WHERE codigo_inventario='INV-NUEVO'")[0]
        respuesta = self.post(
            f'/bienes/{bien}/estado',
            dict(estado='MANTENIMIENTO', estado_esperado='DISPONIBLE', motivo='Revisión inicial'),
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.cliente.get(respuesta.location).status_code, 200)

    def test_error_mysql_no_expone_detalle_interno(self):
        self.login()
        with patch(
            'repositorio.repositorio_recurso_sql.RepositorioRecursoSQL.consultar_recursos',
            side_effect=DatabaseError('DETALLE_INTERNO_PRIVADO'),
        ):
            respuesta = self.cliente.get('/recursos')
        self.assertEqual(respuesta.status_code, 503)
        self.assertNotIn('DETALLE_INTERNO_PRIVADO', respuesta.get_data(as_text=True))
