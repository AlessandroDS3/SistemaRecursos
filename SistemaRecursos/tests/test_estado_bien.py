from datetime import date
import unittest
from unittest.mock import MagicMock

from repositorio.repositorio_bien_material_sql import RepositorioBienMaterialSQL


class EstadoBienTest(unittest.TestCase):
    def test_cambio_guarda_estado_y_motivo_en_historial(self):
        for anterior, nuevo in (("DISPONIBLE", "MANTENIMIENTO"), ("MANTENIMIENTO", "DISPONIBLE")):
            with self.subTest(anterior=anterior, nuevo=nuevo):
                fila = dict(id_bien=1, id_recurso=1, codigo_inventario="INV-1",
                            fecha_adquisicion=date(2025, 1, 1), estado=anterior)
                conexion = MagicMock()
                cursor = conexion.sesion.return_value.__enter__.return_value
                cursor.fetchone.side_effect = [fila, None, dict(fila, estado=nuevo)]
                repo = RepositorioBienMaterialSQL(conexion)
                bien = repo.cambiar_estado_bien_material(1, nuevo, "Revision del equipo", "98000002", anterior)
                self.assertEqual(bien.estado.value, nuevo)
                consultas = [llamada.args[0] for llamada in cursor.execute.call_args_list]
                self.assertTrue(any("UPDATE bien_material" in sql for sql in consultas))
                historial = next(llamada for llamada in cursor.execute.call_args_list
                                 if "INSERT INTO historial_estado" in llamada.args[0])
                self.assertEqual(historial.args[1], (1, anterior, nuevo, "Revision del equipo", "98000002"))
                self.assertFalse(any("registro_fuera_servicio" in sql for sql in consultas))


if __name__ == "__main__":
    unittest.main()
