import unittest
from unittest.mock import Mock

from dominio.cuentas import validar_baja_persona, validar_conservacion_administrador
from repositorio.repositorio_acceso_sql import RepositorioAccesoSQL
from repositorio.repositorio_persona_sql import RepositorioPersonaSQL


class ProteccionAdministradorTest(unittest.TestCase):
    def setUp(self):
        self.admin = dict(id_usuario=1, dni_persona="12345678", rol="ADMINISTRADOR", estado_cuenta="ACTIVA", estado_persona="ACTIVA")

    def test_impide_desactivar_o_cambiar_rol_del_ultimo_admin(self):
        for cambios in ({"estado_cuenta": "INACTIVA"}, {"rol": "USUARIO"}):
            with self.subTest(cambios=cambios):
                with self.assertRaisesRegex(ValueError, "al menos una cuenta administradora"):
                    validar_conservacion_administrador(
                        self.admin, dict(self.admin, **cambios), [self.admin])

    def test_permite_el_cambio_si_otro_admin_conserva_acceso(self):
        otro = dict(self.admin, id_usuario=2, dni_persona="87654321")
        validar_conservacion_administrador(self.admin, dict(self.admin, estado_cuenta="INACTIVA"),
                                          [self.admin, otro])
        validar_baja_persona("12345678", 2, [self.admin, otro])

    def test_admin_inactivo_no_cuenta_como_alternativa(self):
        otro = dict(self.admin, id_usuario=2, dni_persona="87654321", estado_persona="INACTIVA")
        with self.assertRaises(ValueError):
            validar_conservacion_administrador(self.admin, dict(self.admin, estado_cuenta="INACTIVA"),
                                              [self.admin, otro])

    def test_protege_la_persona_del_ultimo_admin_y_la_propia(self):
        with self.assertRaisesRegex(ValueError, "al menos una cuenta administradora"):
            validar_baja_persona("12345678", 2, [self.admin])
        with self.assertRaisesRegex(ValueError, "con la que estás trabajando"):
            validar_baja_persona("12345678", 1, [self.admin])

    def test_repositorios_bloquean_cuentas_en_el_mismo_orden(self):
        for clase in (RepositorioAccesoSQL, RepositorioPersonaSQL):
            cursor = Mock()
            cursor.fetchall.return_value = [self.admin]
            self.assertEqual(clase._bloquear_cuentas(cursor), [self.admin])
            cursor.execute.assert_called_once()
            self.assertIn("ORDER BY u.id_usuario FOR UPDATE", cursor.execute.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
