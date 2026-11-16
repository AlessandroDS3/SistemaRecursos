from contextlib import contextmanager
from datetime import datetime
import unittest
from werkzeug.security import generate_password_hash
from dominio.compartido.validacion import Conflicto
from dominio.gestion_control.politica_prestamo import HorarioAtencion
from dominio.gestion_personas_usuarios.acceso import CuentaAcceso
from servicios.servicio_acceso import ServicioAplicacionAcceso
from servicios.servicio_prestamo import ServicioAplicacionPrestamo


class CuentaEnMemoria:
    def __init__(self, activa=True):
        self.accesos = []
        self.cuenta = CuentaAcceso(
            id_usuario=1,
            dni='12345678',
            nombre_usuario='prueba',
            nombres='Persona',
            apellidos='Prueba',
            rol='USUARIO',
            estado_cuenta='ACTIVA' if activa else 'BLOQUEADA',
            estado_persona='ACTIVA',
            contrasena_hash=generate_password_hash('ClavePrueba2026!'),
        )

    def consultar_cuenta_por_usuario(self, nombre):
        return self.cuenta if nombre == 'prueba' else None

    def consultar_cuenta_por_id(self, identificador):
        return self.cuenta if identificador == self.cuenta.id_usuario else None

    def registrar_acceso(self, identificador):
        self.accesos.append(identificador)


class EntregaEnMemoria:
    def __init__(self, limite):
        self.limite, self.guardado, self.confirmada = limite, None, False

    @contextmanager
    def transaccion(self):
        yield self
        self.confirmada = True

    def consultar_cuenta_actor(self, identificador):
        return dict(
            dni_persona='87654321',
            estado_cuenta='ACTIVA',
            estado_persona='ACTIVA',
            permisos={'PRESTAMOS_GESTIONAR'},
        )

    def consultar_contexto_entrega_prestamo(self, solicitud):
        return dict(
            personas={
                '12345678': dict(tipo='ESTUDIANTE', estado='ACTIVA', estado_matricula='VIGENTE')
            },
            sancion=False,
            vencido=False,
            limite=self.limite,
            pendientes=1,
            entregas_pendientes=False,
            bienes=[dict(id_bien=1, id_categoria=1, estado='DISPONIBLE')],
            politicas={
                1: dict(
                    id_politica=1,
                    tipo_persona='ESTUDIANTE',
                    id_categoria=1,
                    plazo_maximo=2,
                    unidad_plazo='DIAS',
                )
            },
            horario=HorarioAtencion(),
            ahora=datetime(2026, 11, 14, 15),
        )

    def registrar_entrega_prestamo(self, solicitud, plan, fecha):
        self.guardado = plan
        return 73


class ServiciosSinMySQL(unittest.TestCase):
    def test_recuperar_sesion_solo_devuelve_cuentas_activas_y_no_registra_otro_login(self):
        for activa in (True, False):
            with self.subTest(activa=activa):
                repo = CuentaEnMemoria(activa=activa)
                acceso = ServicioAplicacionAcceso(repo)
                self.assertIs(acceso.consultar_cuenta_activa(1), repo.cuenta if activa else None)
                for identificador in (2, 0, -1, None, True, 'incorrecto'):
                    self.assertIsNone(acceso.consultar_cuenta_activa(identificador))
                self.assertEqual(repo.accesos, [])

    def test_autenticacion_se_prueba_sin_flask_ni_base(self):
        repo = CuentaEnMemoria()
        acceso = ServicioAplicacionAcceso(repo)
        self.assertIsNotNone(acceso.autenticar_cuenta('prueba', 'ClavePrueba2026!'))
        self.assertIsNone(acceso.autenticar_cuenta('prueba', 'Incorrecta'))
        self.assertIsNone(acceso.autenticar_cuenta('ausente', 'ClavePrueba2026!'))
        self.assertEqual(repo.accesos, [1])

    def test_cuenta_bloqueada_no_se_autentica_con_clave_correcta(self):
        repo = CuentaEnMemoria(activa=False)
        self.assertIsNone(
            ServicioAplicacionAcceso(repo).autenticar_cuenta('prueba', 'ClavePrueba2026!')
        )
        self.assertEqual(repo.accesos, [])

    def test_caso_entrega_se_prueba_con_solo_hechos_del_repositorio(self):
        repo = EntregaEnMemoria(limite=2)
        resultado = ServicioAplicacionPrestamo(repo).registrar_prestamo(
            dict(dni_persona='12345678', bienes=[1], acepta_condiciones='1'), 2
        )
        self.assertEqual(resultado, 73)
        self.assertTrue(repo.confirmada)
        self.assertEqual(repo.guardado[0]['fecha_limite_devolucion'], datetime(2026, 11, 16, 15))

    def test_cupo_rechazado_no_llega_a_guardar(self):
        repo = EntregaEnMemoria(limite=1)
        with self.assertRaises(Conflicto):
            ServicioAplicacionPrestamo(repo).registrar_prestamo(
                dict(dni_persona='12345678', bienes=[1], acepta_condiciones='1'), 2
            )
        self.assertIsNone(repo.guardado)
        self.assertFalse(repo.confirmada)
