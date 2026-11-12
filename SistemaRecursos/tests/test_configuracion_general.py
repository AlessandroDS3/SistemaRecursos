"""Pruebas con MySQL en bases temporales independientes."""
import os
from pathlib import Path
import unittest
from uuid import uuid4

import mysql.connector
from dominio.gestion_control.horario_atencion import HorarioAtencion
from dominio.gestion_control.politica_vencimiento_reserva import PoliticaVencimientoReserva
from repositorio.conexion_mysql import MySQLConnection
from repositorio.repositorio_politica_prestamo_sql import RepositorioPoliticaPrestamoSQL
from repositorio.repositorio_reserva_sql import RepositorioReservaSQL
from dominio.gestion_prestamos.reserva import Reserva


@unittest.skipUnless(os.environ.get("TEST_MYSQL_PORT"), "Configura MySQL de pruebas.")
class ConfiguracionGeneralTest(unittest.TestCase):
    def setUp(self):
        self.nombre = "test_configuracion_" + uuid4().hex
        cfg = dict(host="127.0.0.1", port=int(os.environ["TEST_MYSQL_PORT"]),
                   user=os.environ.get("TEST_MYSQL_USER", "root"),
                   password=os.environ.get("TEST_MYSQL_PASSWORD", ""), connection_timeout=5, use_pure=True)
        self.cn = mysql.connector.connect(**cfg)
        self.addCleanup(self.cn.close)
        self.cursor = self.cn.cursor()
        self.addCleanup(self.cursor.close)
        self.cursor.execute(f"CREATE DATABASE {self.nombre} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        self.addCleanup(self.cursor.execute, f"DROP DATABASE {self.nombre}")
        self.sql = Path(__file__).resolve().parents[1] / "sql"
        self.ejecutar((self.sql / "datos_prueba.sql").read_text(encoding="utf-8").replace("prestamos_escuela_pruebas", self.nombre))
        self.repo = RepositorioPoliticaPrestamoSQL(MySQLConnection(dict(cfg, database=self.nombre)))

    def ejecutar(self, sql):
        self.cursor.execute(sql)
        while self.cursor.nextset():
            pass
        self.cn.commit()

    def tablas(self):
        self.cursor.execute("SHOW TABLES")
        return {fila[0] for fila in self.cursor.fetchall()}

    def test_esquema_y_actualizaciones_independientes(self):
        tablas = self.tablas()
        self.assertEqual(len(tablas), 20)
        self.assertIn("configuracion_general", tablas)
        for antigua in ("horario_atencion", "politica_vencimiento_reserva", "notificacion", "notificacion_danio"):
            self.assertNotIn(antigua, tablas)
        self.repo.actualizar_horario_atencion(HorarioAtencion(hora_apertura="09:00", hora_cierre="17:00"))
        plazos = self.repo.consultar_politica_vencimiento_reserva()
        self.assertEqual((plazos.plazo_espera, plazos.plazo_retiro), (2, 24))
        self.repo.actualizar_politica_vencimiento_reserva(PoliticaVencimientoReserva(
            plazo_espera=3, unidad_espera="DIAS", plazo_retiro=12, unidad_retiro="HORAS"))
        horario = self.repo.consultar_horario_atencion()
        self.assertEqual((horario.apertura_texto, horario.cierre_texto), ("09:00", "17:00"))

    def test_esquema_sin_datos_se_importa_desde_cero(self):
        nombre = self.nombre + "_estructura"
        self.addCleanup(self.cursor.execute, f"DROP DATABASE IF EXISTS {nombre}")
        self.ejecutar((self.sql / "schema.sql").read_text(encoding="utf-8").replace("prestamos_escuela", nombre))
        self.assertEqual(len(self.tablas()), 20)
        self.cursor.execute("SELECT COUNT(*) FROM persona")
        self.assertEqual(self.cursor.fetchone()[0], 0)

    def test_limites_de_reserva_segun_unidad_en_dominio_y_mysql(self):
        for unidad, limite in (("DIAS", 30), ("HORAS", 720)):
            for valido in (1, limite):
                politica = PoliticaVencimientoReserva(
                    plazo_espera=valido, unidad_espera=unidad,
                    plazo_retiro=valido, unidad_retiro=unidad)
                self.repo.actualizar_politica_vencimiento_reserva(politica)
                self.assertEqual(self.repo.consultar_politica_vencimiento_reserva(), politica)
            for campo, campo_unidad in (("plazo_espera", "unidad_espera"), ("plazo_retiro", "unidad_retiro")):
                for invalido in (0, limite + 1):
                    with self.subTest(unidad=unidad, campo=campo, valor=invalido):
                        with self.assertRaises(ValueError):
                            PoliticaVencimientoReserva(**{campo: invalido, campo_unidad: unidad})
                        with self.assertRaises(mysql.connector.Error):
                            with self.repo.conexion.sesion(escritura=True) as c:
                                c.execute(f"UPDATE configuracion_general SET {campo}=%s,{campo_unidad}=%s WHERE id_configuracion=1",
                                          (invalido, unidad))

    def test_cola_por_fecha_e_identificador_despues_de_cancelar(self):
        repo = RepositorioReservaSQL(self.repo.conexion)
        with self.repo.conexion.sesion(escritura=True) as c:
            c.execute("UPDATE reserva SET estado='CANCELADA'")
            c.execute("SELECT DATE_SUB(UTC_TIMESTAMP(),INTERVAL 1 MINUTE) AS fecha")
            fecha = c.fetchone()["fecha"]
            ids = [repo._insertar_reserva(c, Reserva(dni_persona="99000001", id_recurso=2,
                    fecha_requerida=fecha), PoliticaVencimientoReserva()) for _ in range(3)]
            for identificador in ids:
                c.execute("UPDATE reserva SET fecha_solicitud=%s WHERE id_reserva=%s", (fecha, identificador))
        with self.repo.conexion.sesion() as c:
            c.execute("SHOW COLUMNS FROM reserva LIKE 'posicion_en_cola'")
            self.assertIsNone(c.fetchone())
            self.assertEqual(repo._primera_solicitud_disponible(c, 2), ids[0])
        repo.cancelar_reserva(ids[0], "99000001", False, motivo="Ya no lo necesito")
        with self.repo.conexion.sesion() as c:
            self.assertEqual(repo._primera_solicitud_disponible(c, 2), ids[1])
        repo.cancelar_reserva(ids[1], "99000001", False, motivo="Ya no lo necesito")
        with self.repo.conexion.sesion() as c:
            self.assertEqual(repo._primera_solicitud_disponible(c, 2), ids[2])



if __name__ == "__main__":
    unittest.main()
