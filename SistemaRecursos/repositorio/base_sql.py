"""Mecánica SQL compartida. Cada transacción entrega una instancia independiente."""

from contextlib import contextmanager
import re

from repositorio.conexion_mysql import MySQLConnection


class RepositorioSQL:
    def __init__(self, conexion=None, cursor=None):
        self.conexion = conexion or MySQLConnection()
        self._cursor = cursor

    @contextmanager
    def transaccion(self):
        if self._cursor is not None:
            yield self
        else:
            with self.conexion.sesion(escritura=True) as cursor:
                yield type(self)(self.conexion, cursor)

    def consultar_sql(self, sql, parametros=(), una=False):
        def leer(cursor):
            cursor.execute(sql, parametros)
            return cursor.fetchone() if una else cursor.fetchall()

        if self._cursor is not None:
            return leer(self._cursor)
        with self.conexion.sesion() as cursor:
            return leer(cursor)

    def ejecutar(self, sql, parametros=()):
        if self._cursor is None:
            raise RuntimeError('Una escritura requiere una transacción del servicio.')
        self._cursor.execute(sql, parametros)
        return self._cursor.lastrowid

    def insertar(self, tabla, datos):
        # Tabla y columnas solo se suministran desde métodos del repositorio.
        nombres = [tabla, *datos]
        if not all(re.fullmatch(r'[a-z_]+', n) for n in nombres):
            raise ValueError('Identificador SQL inválido.')
        columnas = ','.join(datos)
        marcas = ','.join(['%s'] * len(datos))
        return self.ejecutar(
            f'INSERT INTO {tabla} ({columnas}) VALUES ({marcas})', tuple(datos.values())
        )

    def consultar_fecha_actual(self):
        return self.consultar_sql('SELECT UTC_TIMESTAMP() AS fecha', una=True)['fecha']

    def consultar_cuenta_actor(self, identificador):
        cuenta = self.consultar_sql(
            '''SELECT u.id_usuario,u.dni_persona,u.rol,u.estado_cuenta,
            p.estado AS estado_persona FROM usuario_sistema u JOIN persona p ON p.dni=u.dni_persona
            WHERE u.id_usuario=%s''',
            (identificador,),
            una=True,
        )
        if cuenta:
            cuenta['permisos'] = {
                p['permiso']
                for p in self.consultar_sql(
                    'SELECT permiso FROM rol_permiso WHERE rol=%s', (cuenta['rol'],)
                )
            }
        return cuenta

    def registrar_historial_estado(
        self, entidad, identificador, anterior, nuevo, actor, observacion
    ):
        self.insertar(
            'historial_estado',
            dict(
                entidad=entidad,
                id_entidad=identificador,
                estado_anterior=anterior,
                estado_nuevo=nuevo,
                fecha=self.consultar_fecha_actual(),
                dni_responsable=actor,
                observacion=observacion,
            ),
        )

    def consultar_historial_estado(self, entidad, identificador):
        return self.consultar_sql(
            '''SELECT h.*,CONCAT(p.nombres,' ',p.apellidos) AS responsable
            FROM historial_estado h LEFT JOIN persona p ON p.dni=h.dni_responsable
            WHERE h.entidad=%s AND h.id_entidad=%s ORDER BY h.fecha DESC,h.id_historial_estado DESC''',
            (entidad, identificador),
        )
