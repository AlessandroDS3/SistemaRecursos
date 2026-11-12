import os
from pathlib import Path
import unittest
from uuid import uuid4

import mysql.connector
from werkzeug.datastructures import MultiDict
from app import create_app
from repositorio.conexion_mysql import MySQLConnection
from repositorio.repositorio_sancion_sql import RepositorioSancionSQL


@unittest.skipUnless(os.environ.get("TEST_MYSQL_PORT"), "Configura MySQL de pruebas.")
class DevolucionIntegradaTest(unittest.TestCase):
    def setUp(self):
        cfg = dict(host="127.0.0.1", port=int(os.environ["TEST_MYSQL_PORT"]),
                   user=os.environ.get("TEST_MYSQL_USER", "root"),
                   password=os.environ.get("TEST_MYSQL_PASSWORD", ""), connection_timeout=5, use_pure=True)
        nombre = "test_devolucion_" + uuid4().hex
        cn = mysql.connector.connect(**cfg)
        self.addCleanup(cn.close)
        c = cn.cursor()
        self.addCleanup(c.close)
        c.execute(f"CREATE DATABASE {nombre} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        self.addCleanup(c.execute, f"DROP DATABASE {nombre}")
        sql = Path(__file__).resolve().parents[1] / "sql/datos_prueba.sql"
        c.execute(sql.read_text(encoding="utf-8").replace("prestamos_escuela_pruebas", nombre))
        while c.nextset():
            pass
        cn.commit()
        self.db = MySQLConnection(dict(cfg, database=nombre))
        self.app = create_app({"TESTING": True, "MYSQL_CONFIG": self.db.config})
        self.servicio = self.app.extensions["prestamos"]
        self.repo = self.servicio.repositorio

    def detalle(self, identificador=1):
        with self.db.sesion() as c:
            c.execute("SELECT * FROM detalle_prestamo WHERE id_detalle=%s", (identificador,))
            return c.fetchone()

    def recibir(self, detalles, condiciones):
        datos = MultiDict([("detalles", str(d)) for d in detalles])
        datos.update(condiciones)
        self.servicio.registrar_devolucion(1, datos, "98000002")

    def test_devolucion_parcial_completa_y_condiciones_en_la_vista(self):
        with self.db.sesion(escritura=True) as c:
            c.execute("""INSERT INTO detalle_prestamo
                (id_prestamo,id_bien,id_politica,fecha_limite_devolucion)
                VALUES (1,2,24,DATE_ADD(UTC_TIMESTAMP(),INTERVAL 1 DAY))""")
            segundo = c.lastrowid
            c.execute("UPDATE bien_material SET estado='PRESTADO' WHERE id_bien=2")
        self.recibir([1], {"condicion_1": "BUENO"})
        self.assertEqual(self.repo.consultar_prestamo(1)["estado"], "PARCIALMENTE_DEVUELTO")
        self.assertIsNotNone(self.detalle()["fecha_devolucion"])
        self.assertIsNone(self.detalle(segundo)["fecha_devolucion"])
        self.recibir([segundo], {f"condicion_{segundo}": "DANADO", f"observacion_{segundo}": "Pantalla dañada"})
        self.assertEqual(self.repo.consultar_prestamo(1)["estado"], "DEVUELTO")
        self.assertEqual(self.detalle(segundo)["dni_encargado_devolucion"], "98000002")
        with self.db.sesion() as c:
            c.execute("SELECT estado FROM bien_material WHERE id_bien=2")
            self.assertEqual(c.fetchone()["estado"], "DANADO")
            c.execute("SELECT COUNT(*) AS n FROM sancion s JOIN incidencia i ON i.id_incidencia=s.id_incidencia_ref WHERE i.id_detalle=1 AND i.tipo='RETRASO'")
            self.assertEqual(c.fetchone()["n"], 1)
        anterior = self.detalle()
        with self.assertRaises(ValueError):
            self.recibir([1], {"condicion_1": "DANADO", "observacion_1": "Cambio indebido"})
        self.assertEqual(self.detalle(), anterior)
        client = self.app.test_client()
        client.get("/login")
        with client.session_transaction() as s:
            token = s["csrf_token"]
        client.post("/login", data=dict(usuario="admin", clave="AdminPrueba2026!", csrf_token=token))
        respuesta = client.get("/prestamos/1")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("Recibido".encode(), respuesta.data)
        self.assertIn("Pantalla dañada".encode(), respuesta.data)

    def test_perdido_sigue_pendiente_y_puede_recuperarse(self):
        self.servicio.reportar_perdida(1, 1, "No localizado", "98000002")
        self.assertIsNone(self.detalle()["fecha_devolucion"])
        self.assertEqual(self.repo.consultar_prestamo(1)["estado"], "VENCIDO")
        with self.assertRaises(ValueError):
            self.recibir([1], {"condicion_1": "PERDIDO"})
        self.recibir([1], {"condicion_1": "BUENO"})
        self.assertEqual(self.repo.consultar_prestamo(1)["estado"], "DEVUELTO")

    def test_historial_unificado_separa_entidades_y_prestamos(self):
        with self.db.sesion() as c:
            c.execute("SHOW TABLES LIKE 'historial_prestamo'")
            self.assertIsNone(c.fetchone())
        historial = self.repo.consultar_prestamo(2)["historial"]
        self.assertEqual(len(historial), 2)
        self.assertEqual([h["estado_nuevo"] for h in historial], ["DEVUELTO", "ACTIVO"])
        self.recibir([1], {"condicion_1": "BUENO"})
        historial = self.repo.consultar_prestamo(1)["historial"]
        self.assertEqual(len(historial), 2)
        self.assertTrue(all(h["entidad"] == "PRESTAMO" and h["id_entidad"] == 1 for h in historial))
        self.assertEqual(historial[0]["estado_nuevo"], "DEVUELTO")
        with self.db.sesion() as c:
            c.execute("SELECT COUNT(*) AS n FROM historial_estado WHERE entidad='BIEN_MATERIAL' AND id_entidad=1")
            self.assertEqual(c.fetchone()["n"], 2)
        self.assertEqual(len(self.repo.consultar_prestamo(2)["historial"]), 2)

    def test_rechaza_lotes_invalidos_y_datos_incompletos(self):
        with self.assertRaises(ValueError):
            self.recibir([1, 99999], {"condicion_1": "BUENO", "condicion_99999": "BUENO"})
        self.assertIsNone(self.detalle()["fecha_devolucion"])
        with self.assertRaises(ValueError):
            self.recibir([1], {"condicion_1": "DANADO"})
        with self.assertRaises(mysql.connector.Error):
            with self.db.sesion(escritura=True) as c:
                c.execute("UPDATE detalle_prestamo SET fecha_devolucion=UTC_TIMESTAMP() WHERE id_detalle=1")
        with self.assertRaises(mysql.connector.Error):
            with self.db.sesion(escritura=True) as c:
                c.execute("""INSERT INTO detalle_prestamo (id_prestamo,id_bien,id_politica,fecha_limite_devolucion)
                    VALUES (1,1,24,UTC_TIMESTAMP())""")

    def test_sancion_por_incidencia_no_se_duplica_ni_reactiva(self):
        sanciones = RepositorioSancionSQL(self.db)
        self.assertEqual(sanciones.aplicar_sanciones_vencidas(), 1)
        self.assertEqual(sanciones.aplicar_sanciones_vencidas(), 0)
        with self.db.sesion() as c:
            c.execute("SELECT tipo,dni_registrador FROM incidencia WHERE id_detalle=1")
            self.assertEqual(c.fetchone(), {"tipo": "RETRASO", "dni_registrador": None})
        sanciones.levantar_sancion_vencimiento(1, 1, "Caso justificado", "98000002")
        self.assertEqual(sanciones.aplicar_sanciones_vencidas(), 0)
        self.assertEqual(self.repo.consultar_prestamo(1)["detalles"][0]["estado_sancion_vencimiento"], "LEVANTADA")
        with self.assertRaises(ValueError):
            sanciones.levantar_sancion_vencimiento(1, 1, "Repetido", "98000002")
        self.recibir([1], {"condicion_1": "BUENO"})
        with self.db.sesion() as c:
            c.execute("SELECT s.estado,i.estado AS estado_incidencia FROM sancion s JOIN incidencia i ON i.id_incidencia=s.id_incidencia_ref")
            self.assertEqual(c.fetchall(), [{"estado": "LEVANTADA", "estado_incidencia": "RESUELTA"}])

    def test_reutiliza_incidencia_y_separa_danio_del_retraso(self):
        with self.db.sesion(escritura=True) as c:
            c.execute("INSERT INTO incidencia(id_detalle,tipo,fecha) VALUES (1,'RETRASO',UTC_TIMESTAMP())")
            incidencia = c.lastrowid
            c.execute("INSERT INTO incidencia(id_detalle,tipo,dni_registrador,fecha) VALUES (1,'DANIO','98000002',UTC_TIMESTAMP())")
            c.execute("INSERT INTO sancion(dni_persona,id_incidencia_ref,motivo,fecha) VALUES ('99000001',%s,'Daño',UTC_TIMESTAMP())", (c.lastrowid,))
        with self.assertRaises(mysql.connector.Error):
            with self.db.sesion(escritura=True) as c:
                c.execute("INSERT INTO incidencia(id_detalle,tipo,fecha) VALUES (1,'RETRASO',UTC_TIMESTAMP())")
        with self.assertRaises(mysql.connector.Error):
            with self.db.sesion(escritura=True) as c:
                c.execute("INSERT INTO incidencia(id_detalle,tipo,dni_registrador,fecha) VALUES (1,'PERDIDA','00000000',UTC_TIMESTAMP())")
        sanciones = RepositorioSancionSQL(self.db)
        self.assertEqual(sanciones.aplicar_sanciones_vencidas(), 1)
        self.assertEqual(sanciones.aplicar_sanciones_vencidas(), 0)
        with self.db.sesion() as c:
            c.execute("SELECT COUNT(*) AS n FROM sancion WHERE id_incidencia_ref=%s", (incidencia,))
            self.assertEqual(c.fetchone()["n"], 1)
        self.assertEqual(len(self.repo.consultar_prestamo(1)["detalles"]), 1)


if __name__ == "__main__":
    unittest.main()
