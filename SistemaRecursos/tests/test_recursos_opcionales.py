import os
import unittest



@unittest.skipUnless(os.environ.get("TEST_MYSQL_PORT"), "Configura MySQL de pruebas.")
class RecursosOpcionalesTest(unittest.TestCase):
    def setUp(self):
        from soporte_mysql import preparar_base_integracion
        preparar_base_integracion(self)

    def test_registro_edicion_y_vistas_sin_fecha_ni_descripciones(self):
        recursos, bienes = self.app.extensions["recursos"], self.app.extensions["bienes"]
        recurso = recursos.registrar_recurso(dict(
            nombre="Equipo sin fecha conocida", id_categoria="1", codigo_inventario="OPCIONAL-001",
            fecha_adquisicion="", descripcion="", descripcion_bien="",
        ))
        self.assertIsNone(recursos.consultar_recurso(recurso.id_recurso).descripcion)
        filas = bienes.consultar_bienes_materiales({"id_recurso": recurso.id_recurso})["bienes"]
        self.assertEqual(len(filas), 1)
        self.assertIsNone(filas[0]["fecha_adquisicion"])
        self.assertIsNone(filas[0]["descripcion_bien"])
        id_bien = filas[0]["id_bien"]
        bien = bienes.actualizar_bien_material(dict(
            id_bien=id_bien, codigo_inventario="OPCIONAL-001", fecha_adquisicion="", descripcion_bien="",
        ))
        self.assertIsNone(bien.fecha_adquisicion)
        self.assertIsNone(bien.descripcion_bien)
        client = self.app.test_client()
        client.get("/login")
        with client.session_transaction() as sesion:
            token = sesion["csrf_token"]
        self.assertEqual(client.post("/login", data=dict(
            usuario="admin", clave="AdminPrueba2026!", csrf_token=token,
        )).status_code, 302)
        detalle = client.get(f"/bienes/{id_bien}")
        self.assertEqual(detalle.status_code, 200)
        self.assertIn(b"Sin fecha conocida", detalle.data)
        for url in (f"/bienes/{id_bien}/editar", f"/recursos/{recurso.id_recurso}/editar"):
            respuesta = client.get(url)
            self.assertEqual(respuesta.status_code, 200)
            self.assertNotIn(b">None<", respuesta.data)
        self.assertIn(b'name="id_categoria"', client.get(f"/recursos/{recurso.id_recurso}/editar").data)


if __name__ == "__main__":
    unittest.main()
