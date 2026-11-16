import re
from datetime import timedelta
from unittest.mock import patch
from mysql.connector import DatabaseError
from dominio.gestion_prestamos.reserva import ESTADOS_RESERVA
from caso_mysql import CasoMySQL


class RecorridosWeb(CasoMySQL):
    def test_personas_filtra_tipo_cuenta_y_muestra_totales_reales(self):
        personas = self.servicios['personas']
        resultado = personas.consultar_personas(
            {'tipo': 'ESTUDIANTE', 'cuenta': 'SIN_CUENTA', 'estado': 'ACTIVA'}
        )
        self.assertEqual(resultado['total'], 5)
        self.assertEqual(resultado['activas'], 5)
        self.assertEqual(resultado['inactivas'], 0)
        self.assertTrue(all(p['id_usuario'] is None for p in resultado['personas']))
        for filtros in ({'tipo': 'AJENO'}, {'estado': 'OTRO'}, {'cuenta': 'OTRA'}):
            with self.subTest(filtros=filtros), self.assertRaises(ValueError):
                personas.consultar_personas(filtros)
        self.login()
        self.assertEqual(
            self.cliente.get('/personas?tipo=ESTUDIANTE&cuenta=SIN_CUENTA').status_code, 200
        )

    def test_administracion_agrupa_inventario_y_recibe_los_formularios(self):
        self.login()
        pagina = self.cliente.get('/recursos/administracion?q=INV-2').get_data(as_text=True)
        self.assertIn('INV-2', pagina)
        self.assertNotIn('INV-3', pagina)
        respuesta = self.post(
            '/recursos/nuevo',
            {
                'nombre': 'Recurso desde administración',
                'id_categoria': '1',
                'codigo_inventario': 'ADM-1',
                'volver': 'administracion',
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.location.endswith('/recursos/administracion'))
        respuesta = self.post(
            '/recursos/categorias', {'nombre': 'Categoría desde panel', 'volver': 'administracion'}
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.location.endswith('/recursos/administracion#categorias'))
        self.assertEqual(
            self.fila("SELECT COUNT(*) FROM bien_material WHERE codigo_inventario='ADM-1'"), (1,)
        )

    def test_matriz_politicas_guarda_con_version_y_no_modifica_al_consultar(self):
        self.login()
        pagina = self.cliente.get('/politicas').get_data(as_text=True)
        self.assertEqual(self.fila('SELECT COUNT(*) FROM politica_prestamo'), (1,))
        formulario = re.search(
            r'<form[^>]*action="/politicas/24/editar"[^>]*>(.*?)</form>', pagina, re.S
        ).group(1)
        version = re.search(r'name="version"\s+value="([^"]+)"', formulario).group(1)
        respuesta = self.post(
            '/politicas/24/editar',
            {
                'id_categoria': '1',
                'tipo_persona': 'ESTUDIANTE',
                'plazo_maximo': '3',
                'unidad_plazo': 'DIAS',
                'permite_salida': '1',
                'version': version,
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(
            self.fila('SELECT vigente FROM politica_prestamo WHERE id_politica=24'), (0,)
        )
        self.assertEqual(
            self.fila('SELECT plazo_maximo FROM politica_prestamo WHERE vigente=TRUE'), (3,)
        )

    def test_filtro_y_botones_reserva_reflejan_estados_del_dominio(self):
        identificador = self.reservar()
        self.login('encargado1', 'EncargadoPrueba2026!')
        pagina = self.cliente.get('/reservas?estado=EN_ESPERA').get_data(as_text=True)
        filtro = re.search(r'<select name="estado">(.*?)</select>', pagina, re.DOTALL).group(1)
        opciones = re.findall(r'<option value="([^"]*)"', filtro)
        self.assertEqual(opciones, ['', *ESTADOS_RESERVA])
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
        pagina = self.cliente.get('/reservas/nueva').get_data(as_text=True)
        self.assertNotIn('name="tipo_gestion"', pagina)
        self.assertRegex(pagina, r'name="fecha_requerida"[^>]*required')
        fecha = (self.consultar_fecha_actual + timedelta(days=1, hours=-5)).isoformat(
            timespec='minutes'
        )
        respuesta = self.post(
            '/reservas/nueva', dict(id_recurso='1', fecha_requerida=fecha, acepta_condiciones='1')
        )
        self.assertEqual(respuesta.status_code, 302)
        url_reserva = respuesta.location
        self.assertEqual(self.cliente.get(url_reserva).status_code, 200)
        self.post('/logout')
        self.login('encargado1', 'EncargadoPrueba2026!')
        self.assertEqual(self.post(url_reserva + '/preparar').status_code, 409)
        # Llega la fecha de retiro; recién entonces se prepara y entrega presencialmente.
        self.ejecutar('UPDATE reserva SET fecha_requerida=%s', (self.consultar_fecha_actual,))
        self.assertEqual(self.post(url_reserva + '/preparar').status_code, 302)
        respuesta = self.post(url_reserva + '/entregar', dict(acepta_condiciones='1'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/prestamos/', respuesta.location)
        self.assertEqual(self.cliente.get(respuesta.location).status_code, 200)

    def test_formulario_rechaza_solicitud_inmediata_y_fecha_ausente(self):
        self.login('usuario1', 'UsuarioPrueba2026!')
        for datos in (
            dict(id_recurso='1', acepta_condiciones='1'),
            dict(id_recurso='1', acepta_condiciones='1', tipo_gestion='PRESTAMO'),
        ):
            with self.subTest(datos=datos):
                self.assertEqual(self.post('/reservas/nueva', datos).status_code, 400)
        self.assertEqual(self.fila('SELECT COUNT(*) FROM reserva'), (0,))

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
