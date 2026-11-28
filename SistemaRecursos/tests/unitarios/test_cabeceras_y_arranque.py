"""Cabeceras de seguridad HTTP, gráficos del reporte en pantalla y arranque del servidor web."""

import re
import unittest
from unittest.mock import MagicMock, patch

import app as modulo_app
from app import ManejadorSinVersion, create_app, iniciar_servidor_web
from servicios.reportes.filtro_reporte import FiltroReporte
from tests.soporte_roles import crear_cliente_con_sesion_simulada, crear_cuenta_de_prueba
from tests.unitarios.test_presentacion_reportes import fila_de_ejemplo


class CabecerasSeguridadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch('app.obtener_clave_de_sesion_flask', return_value='pruebas-cabeceras'):
            cls.app = create_app(dict(TESTING=True))

    def test_login_envia_cabeceras_de_seguridad(self):
        respuesta = self.app.test_client().get('/login')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.headers['X-Frame-Options'], 'DENY')
        self.assertEqual(respuesta.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(respuesta.headers['Referrer-Policy'], 'same-origin')
        self.assertIn('max-age=', respuesta.headers['Strict-Transport-Security'])
        politica = respuesta.headers['Content-Security-Policy']
        self.assertIn("frame-ancestors 'none'", politica)
        self.assertNotIn('unsafe-inline', politica)

    def test_nonce_de_la_csp_coincide_con_el_script_y_cambia_en_cada_peticion(self):
        cliente = self.app.test_client()
        primera, segunda = cliente.get('/login'), cliente.get('/login')
        nonce = re.search(r"'nonce-([^']+)'", primera.headers['Content-Security-Policy']).group(1)
        self.assertIn(f'nonce="{nonce}"', primera.get_data(as_text=True))
        self.assertNotEqual(primera.headers['Content-Security-Policy'], segunda.headers['Content-Security-Policy'])

    def test_archivos_estaticos_tambien_llevan_cabeceras(self):
        respuesta = self.app.test_client().get('/static/estilos.css')
        self.assertEqual(respuesta.headers['X-Content-Type-Options'], 'nosniff')
        respuesta.close()

    def test_reporte_muestra_graficos_como_imagen_sin_html_del_usuario(self):
        cliente = crear_cliente_con_sesion_simulada(self, self.app, crear_cuenta_de_prueba('ADMINISTRADOR'))
        filtro = FiltroReporte(tipo='inventario')
        filas = [dict(fila_de_ejemplo('inventario', i), recurso='<script>alert(1)</script>') for i in range(4)]
        servicios = self.app.extensions['servicios']
        resultado = dict(filtro=filtro, reporte=filtro.definicion, parametros=filtro.parametros, filas=filas)
        self.enterContext(patch.object(servicios['reportes'], 'consultar_reporte_filtrado', return_value=resultado))
        self.enterContext(patch.object(servicios['recursos'], 'consultar_categorias', return_value=[]))
        respuesta = cliente.get('/reportes?tipo=inventario')
        self.assertEqual(respuesta.status_code, 200)
        html = respuesta.get_data(as_text=True)
        self.assertEqual(html.count('<img src="data:image/svg+xml;base64,'), 2)
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertNotIn('style="', html)


class ArranqueServidorTest(unittest.TestCase):
    def test_manejador_no_revela_versiones(self):
        self.assertEqual(ManejadorSinVersion.version_string(None), 'SistemaRecursos')

    def iniciar_con(self, argumentos):
        aplicacion = MagicMock()
        detener = MagicMock()
        with patch.object(modulo_app, 'create_app', return_value=aplicacion), \
                patch.object(modulo_app, 'iniciar_procesador_vencimientos', return_value=detener) as procesador, \
                patch.object(modulo_app.logging, 'basicConfig'):
            iniciar_servidor_web(argumentos)
        return aplicacion, procesador, detener

    def test_inicia_web_y_procesador_con_el_manejador_sin_version(self):
        aplicacion, procesador, detener = self.iniciar_con([])
        procesador.assert_called_once()
        self.assertIs(aplicacion.run.call_args.kwargs['request_handler'], ManejadorSinVersion)
        self.assertEqual(aplicacion.run.call_args.kwargs['host'], '127.0.0.1')
        detener.set.assert_called_once()

    def test_sin_procesador_solo_inicia_la_web(self):
        aplicacion, procesador, _ = self.iniciar_con(['--sin-procesador'])
        procesador.assert_not_called()
        aplicacion.run.assert_called_once()


if __name__ == '__main__':
    unittest.main()
