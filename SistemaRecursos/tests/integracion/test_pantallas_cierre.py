"""Las pantallas nuevas del cierre se dibujan para cada rol sin base de datos."""

from datetime import date, datetime, timedelta
import unittest
from unittest.mock import patch

from app import create_app
from tests.soporte_roles import crear_cliente_con_sesion_simulada, crear_cuenta_de_prueba

AHORA = datetime(2026, 11, 24, 15, 0)


def crear_bien_de_prueba(**cambios):
    return dict(dict(
        id_bien=5, id_recurso=1, recurso='Laptop', codigo_inventario='LAP-5',
        identificador_sistema='SR-2026-7F3K9Q', numero_serie='PF3KX', fecha_adquisicion=date(2024, 3, 1),
        fecha_registro=AHORA, ubicacion='Lab 2', descripcion_bien=None, estado='DISPONIBLE',
        version='v', categoria='Equipos', id_categoria=1,
    ), **cambios)


def crear_ficha_de_bien_de_prueba(**cambios):
    return dict(dict(
        bien=crear_bien_de_prueba(), historial=[], prestamo_pendiente=None, danio_pendiente=None,
        mantenimiento_abierto=None, mantenimientos=[], permite_mantenimiento=True,
        permite_cambio_manual=True, permite_eliminar=False,
    ), **cambios)


def crear_solicitud_de_ampliacion_de_prueba(**cambios):
    return dict(dict(
        id_solicitud=9, id_prestamo=4, id_detalle=7, codigo_inventario='LAP-5', recurso='Laptop',
        solicitante='Lucía Quispe', cantidad=2, unidad='DIAS', motivo='Sustentación',
        fecha_solicitud=AHORA, fecha_limite_anterior=AHORA, fecha_limite_devolucion=AHORA + timedelta(days=1),
        fecha_devolucion=None, fecha_regularizacion=None, estado='PENDIENTE', fecha_resolucion=None,
        responsable_resolucion=None, fecha_limite_nueva=None, observacion_resolucion=None,
    ), **cambios)


def crear_prestamo_de_prueba():
    return dict(
        id_prestamo=4, tipo_prestamo='INDIVIDUAL', estado_actual='ACTIVO', estado='ACTIVO',
        solicitante='Ana Prueba', dni_persona='20000001', fecha_entrega=AHORA, dni_encargado='10000002',
        observaciones='', participantes=[], historial=[],
        detalles=[dict(
            id_detalle=7, codigo_inventario='LAP-5', recurso='Laptop', fecha_devolucion=None,
            fecha_regularizacion=None, estado_bien='PRESTADO', unidad_plazo='DIAS',
            fecha_limite_devolucion=datetime(2099, 1, 1), condicion_entrega='BUENO',
            condicion_devolucion=None, observaciones_devolucion=None, estado_sancion=None,
            gravedad=None, id_sancion=None,
        )],
    )


class PantallasCierreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch('app.obtener_clave_de_sesion_flask', return_value='pruebas-pantallas'):
            cls.app = create_app(dict(TESTING=True))
        cls.servicios = cls.app.extensions['servicios']

    def crear_cliente_para_rol(self, rol):
        return crear_cliente_con_sesion_simulada(self, self.app, crear_cuenta_de_prueba(rol))

    def test_ficha_del_bien_muestra_identificador_y_mantenimiento(self):
        cliente = self.crear_cliente_para_rol('ADMINISTRADOR')
        with patch.object(self.servicios['bienes'], 'consultar_detalle_bien_material',
                          return_value=crear_ficha_de_bien_de_prueba()):
            html = cliente.get('/bienes/5').get_data(as_text=True)
        self.assertIn('SR-2026-7F3K9Q', html)
        self.assertIn('Serie del fabricante', html)
        self.assertIn('Abrir mantenimiento', html)
        abierto = dict(id_mantenimiento=1, tipo='CORRECTIVO', fecha_inicio=AHORA, fecha_fin_estimada=None)
        registro = dict(abierto, motivo='Pantalla', fecha_fin_real=None, resultado=None,
                        observacion_cierre=None, responsable_apertura='Admin', responsable_cierre=None)
        with patch.object(self.servicios['bienes'], 'consultar_detalle_bien_material',
                          return_value=crear_ficha_de_bien_de_prueba(bien=crear_bien_de_prueba(estado='MANTENIMIENTO'), mantenimiento_abierto=abierto,
                                                    mantenimientos=[registro], permite_mantenimiento=False,
                                                    permite_cambio_manual=False)):
            html = cliente.get('/bienes/5').get_data(as_text=True)
        self.assertIn('Cerrar mantenimiento', html)
        self.assertIn('Registro de mantenimientos', html)

    def test_lista_de_solicitudes_para_el_encargado(self):
        cliente = self.crear_cliente_para_rol('ENCARGADO_PRESTAMOS')
        with patch.object(self.servicios['ampliaciones'], 'consultar_solicitudes_ampliacion',
                          return_value=[crear_solicitud_de_ampliacion_de_prueba(), crear_solicitud_de_ampliacion_de_prueba(id_solicitud=10, estado='APROBADA',
                                                              fecha_limite_nueva=AHORA)]):
            respuesta = cliente.get('/ampliaciones/solicitudes')
        html = respuesta.get_data(as_text=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('Aprobar', html)
        self.assertIn('Sustentación', html)

    def test_usuario_ve_el_formulario_para_pedir_mas_plazo(self):
        cliente = self.crear_cliente_para_rol('USUARIO')
        with patch.object(self.servicios['prestamos'], 'consultar_prestamo', return_value=crear_prestamo_de_prueba()), \
                patch.object(self.servicios['ampliaciones'], 'consultar_solicitudes_de_ampliacion_del_prestamo', return_value=[]):
            html = cliente.get('/prestamos/4').get_data(as_text=True)
        self.assertIn('Solicitar más plazo', html)
        self.assertIn('Enviar solicitud', html)
        self.assertNotIn('Ampliar plazo', html)

    def test_inicio_avisa_solicitudes_y_procesador_detenido(self):
        cliente = self.crear_cliente_para_rol('ADMINISTRADOR')
        with patch.object(self.servicios['prestamos'], 'consultar_resumen_prestamos', return_value={}), \
                patch.object(self.servicios['reservas'], 'contar_reservas_pendientes', return_value=2), \
                patch.object(self.servicios['recursos'], 'contar_bienes_disponibles', return_value=3), \
                patch.object(self.servicios['ampliaciones'], 'consultar_solicitudes_ampliacion',
                             return_value=[crear_solicitud_de_ampliacion_de_prueba()]), \
                patch.object(self.servicios['procesador'], 'consultar_estado_procesador', return_value=dict(
                    alerta=True, ultima_ejecucion_correcta=None, ultimo_error='sin conexión',
                    ultimo_error_fecha=AHORA, fallos_consecutivos=3)):
            html = cliente.get('/').get_data(as_text=True)
        self.assertIn('1 solicitud de ampliación', html)
        self.assertIn('Reservas pendientes', html)
        self.assertIn('/reservas?estado=PENDIENTES', html)
        self.assertIn('no se está ejecutando', html)
        self.assertIn('sin conexión', html)


if __name__ == '__main__':
    unittest.main()
