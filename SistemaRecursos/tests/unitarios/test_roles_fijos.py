"""Permisos efectivos fijos y asignación de roles protegida, sin MySQL."""

from contextlib import nullcontext
import unittest
from unittest.mock import Mock, patch

from dominio.compartido.validacion import Conflicto
from dominio.gestion_personas_usuarios.cuenta import version_cuenta
from dominio.gestion_personas_usuarios.rol import permisos_del_rol
from repositorio.base_datos.base_sql import RepositorioSQL
from repositorio.personas_usuarios.repositorio_acceso_sql import RepositorioAccesoSQL
from servicios.personas_usuarios.servicio_cuenta import ServicioAplicacionCuenta
from tests.soporte_roles import crear_cuenta_de_prueba


class PermisosFijosTest(unittest.TestCase):
    def test_roles_fijos_tienen_los_permisos_definidos(self):
        usuario = {
            'CATALOGO_CONSULTAR', 'RESERVAS_PROPIAS_GESTIONAR',
            'PRESTAMOS_PROPIOS_CONSULTAR',
        }
        encargado = usuario | {
            'PRESTAMOS_GESTIONAR', 'PERSONAS_CONSULTAR',
            'PERSONAS_GESTIONAR', 'REPORTES_CONSULTAR',
        }
        administrador = encargado | {
            'USUARIOS_GESTIONAR', 'ROLES_CONSULTAR', 'ROLES_GESTIONAR',
            'RECURSOS_GESTIONAR', 'POLITICAS_GESTIONAR',
        }
        for rol, permisos in (
            ('USUARIO', usuario), ('ENCARGADO_PRESTAMOS', encargado),
            ('ADMINISTRADOR', administrador),
        ):
            with self.subTest(rol=rol):
                self.assertEqual(permisos_del_rol(rol), permisos)
        self.assertFalse(permisos_del_rol('OTRO'))

    def test_autenticacion_no_consulta_permisos_editables_en_sql(self):
        for rol in ('USUARIO', 'ENCARGADO_PRESTAMOS', 'ADMINISTRADOR'):
            with self.subTest(rol=rol):
                acceso = crear_cuenta_de_prueba(rol)
                fila = dict(
                    id_usuario=acceso.id_usuario, dni=acceso.dni,
                    nombre_usuario=acceso.nombre_usuario, nombres=acceso.nombres,
                    apellidos=acceso.apellidos, rol=rol, contrasena_hash='pruebas',
                    estado_cuenta='ACTIVA', estado_persona='ACTIVA', debe_cambiar_clave=False,
                )
                repo = RepositorioAccesoSQL(conexion=Mock())
                with patch.object(repo, 'consultar_sql', side_effect=[fila]) as consulta:
                    resultado = repo.consultar_cuenta_por_id(1)
                self.assertEqual(resultado.permisos, acceso.permisos)
                consulta.assert_called_once()

    def test_operaciones_usan_los_mismos_permisos_que_la_sesion(self):
        for rol in ('USUARIO', 'ENCARGADO_PRESTAMOS', 'ADMINISTRADOR'):
            with self.subTest(rol=rol):
                repo = RepositorioSQL(conexion=Mock())
                with patch.object(repo, 'consultar_sql', side_effect=[dict(rol=rol)]):
                    actor = repo.consultar_cuenta_actor(1)
                self.assertEqual(actor['permisos'], crear_cuenta_de_prueba(rol).permisos)

    def test_asignacion_conserva_validacion_y_ultimo_administrador(self):
        repo = Mock()
        repo.transaccion.side_effect = lambda: nullcontext(repo)
        admin = dict(
            id_usuario=1, dni_persona='20000001', rol='ADMINISTRADOR', estado_cuenta='ACTIVA',
            estado_persona='ACTIVA', debe_cambiar_clave=False,
            nombre_usuario='admin', contrasena_hash='hash-de-prueba',
            permisos=permisos_del_rol('ADMINISTRADOR'),
        )
        usuario = dict(admin, id_usuario=2, dni_persona='20000002', rol='USUARIO', nombre_usuario='usuario')
        repo.consultar_cuenta_actor.return_value = admin
        repo.consultar_cuentas_para_actualizar.return_value = [admin, usuario]
        servicio = ServicioAplicacionCuenta(repo)
        datos = dict(rol='ENCARGADO_PRESTAMOS', version=version_cuenta(usuario))
        servicio.actualizar_cuenta('20000002', datos, 1)
        repo.actualizar_cuenta.assert_called_once_with(2, {'rol': 'ENCARGADO_PRESTAMOS'})
        repo.actualizar_cuenta.reset_mock()
        with self.assertRaisesRegex(ValueError, 'Rol inexistente'):
            servicio.actualizar_cuenta('20000002', dict(datos, rol='OTRO'), 1)
        with self.assertRaises(Conflicto):
            servicio.actualizar_cuenta('20000002', dict(datos, version='anterior'), 1)
        with self.assertRaisesRegex(ValueError, 'al menos una cuenta administradora'):
            servicio.actualizar_cuenta('20000001', dict(rol='USUARIO', version=version_cuenta(admin)), 1)
        repo.actualizar_cuenta.assert_not_called()
        repo.consultar_cuenta_actor.return_value = dict(
            admin, rol='ENCARGADO_PRESTAMOS', permisos=permisos_del_rol('ENCARGADO_PRESTAMOS')
        )
        with self.assertRaises(PermissionError):
            servicio.actualizar_cuenta('20000002', dict(datos, rol='ADMINISTRADOR'), 1)
