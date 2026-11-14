"""Escenarios sobre bases desechables. Nunca utiliza DB_NAME de la aplicación."""

from datetime import datetime, timezone
import os
import unittest
from unittest.mock import patch
from soporte_mysql import preparar_base_integracion


@unittest.skipUnless(os.getenv('TEST_MYSQL_PORT'), 'Requiere MySQL de pruebas')
class CasoMySQL(unittest.TestCase):
    def setUp(self):
        preparar_base_integracion(self)
        self.servicios = self.app.extensions['servicios']
        self.cliente = self.app.test_client()
        self.consultar_fecha_actual = datetime.now(timezone.utc).replace(
            tzinfo=None, hour=15, minute=0, second=0, microsecond=0
        )
        reloj = patch(
            'repositorio.base_sql.RepositorioSQL.consultar_fecha_actual',
            return_value=self.consultar_fecha_actual,
        )
        reloj.start()
        self.addCleanup(reloj.stop)

    def ejecutar(self, sql, parametros=()):
        self.cn.commit()
        self.c.execute(sql, parametros)
        self.cn.commit()

    def fila(self, sql, parametros=()):
        self.cn.commit()
        self.c.execute(sql, parametros)
        return self.c.fetchone()

    def token(self):
        with self.cliente.session_transaction() as sesion:
            return sesion['csrf']

    def login(self, usuario='admin', clave='AdminPrueba2026!'):
        self.cliente.get('/login')
        return self.cliente.post(
            '/login', data=dict(usuario=usuario, clave=clave, csrf_token=self.token())
        )

    def post(self, url, datos=None):
        return self.cliente.post(url, data=dict(datos or {}, csrf_token=self.token()))

    def prestar(self, bienes=None, **cambios):
        datos = dict(dni_persona='02167885', bienes=bienes or [2], acepta_condiciones='1')
        datos.update(cambios)
        return self.servicios['prestamos'].registrar_prestamo(datos, 2)

    def prestamo(self, identificador):
        return self.servicios['prestamos'].consultar_prestamo(identificador, '02167885', True)

    def reservar(self, **cambios):
        datos = dict(id_recurso=1, tipo_gestion='PRESTAMO', acepta_condiciones='1')
        datos.update(cambios)
        return self.servicios['reservas'].registrar_reserva(datos, 3)
