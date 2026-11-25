"""Estado del procesador automático y exclusión entre procesos (OPE-01)."""

from contextlib import contextmanager

from repositorio.base_datos.base_sql import RepositorioSQL


class RepositorioProcesadorSQL(RepositorioSQL):
    @contextmanager
    def bloqueo_exclusivo(self):
        """Candado con nombre de MySQL: solo un proceso por base revisa vencimientos a la vez.

        Se libera al salir o si la conexión se corta, así que un proceso caído no lo retiene.
        """
        with self.conexion.sesion() as cursor:
            cursor.execute(
                "SELECT GET_LOCK(CONCAT('vencimientos_', DATABASE()), 0) AS obtenido"
            )
            obtenido = cursor.fetchone()['obtenido'] == 1
            try:
                yield obtenido
            finally:
                if obtenido:
                    cursor.execute("SELECT RELEASE_LOCK(CONCAT('vencimientos_', DATABASE()))")
                    cursor.fetchall()

    def registrar_ejecucion_correcta(self):
        with self.transaccion() as operacion:
            operacion.ejecutar('INSERT IGNORE INTO estado_procesador(id_procesador) VALUES (1)')
            operacion.ejecutar(
                '''UPDATE estado_procesador SET ultima_ejecucion_correcta=UTC_TIMESTAMP(),
                fallos_consecutivos=0 WHERE id_procesador=1'''
            )

    def registrar_error(self, mensaje):
        with self.transaccion() as operacion:
            operacion.ejecutar('INSERT IGNORE INTO estado_procesador(id_procesador) VALUES (1)')
            operacion.ejecutar(
                '''UPDATE estado_procesador SET ultimo_error_fecha=UTC_TIMESTAMP(),ultimo_error=%s,
                fallos_consecutivos=fallos_consecutivos+1 WHERE id_procesador=1''',
                (mensaje[:500],),
            )

    def consultar_estado(self):
        return self.consultar_sql(
            'SELECT * FROM estado_procesador WHERE id_procesador=1', una=True
        )
