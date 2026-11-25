"""Mecánica SQL compartida. Cada transacción entrega una instancia independiente."""

from contextlib import contextmanager
import json
import re
from mysql.connector import IntegrityError

from dominio.compartido.validacion import Conflicto
from dominio.gestion_personas_usuarios.rol import permisos_del_rol

from repositorio.base_datos.conexion_mysql import MySQLConnection

MENSAJES_DUPLICADOS = {
    'persona.PRIMARY': 'Ya existe una persona con ese DNI.',
    'persona.uq_persona_correo': 'Ese correo ya está registrado.',
    'estudiante.uq_estudiante_cui': 'Ese CUI ya está registrado.',
    'docente.codigo_docente': 'Ese código docente ya está registrado.',
    'administrativo.codigo_empleado': 'Ese código de empleado ya está registrado.',
    'usuario_sistema.dni_persona': 'La persona ya tiene una cuenta de acceso.',
    'usuario_sistema.nombre_usuario': 'Ese nombre de usuario ya está registrado.',
    'bien_material.codigo_inventario': 'Ya existe un bien con ese código de inventario.',
    'categoria_recurso.nombre': 'Ya existe una categoría con ese nombre.',
    'politica_prestamo.uq_politica_persona_categoria_vigente': 'Ya existe una política vigente para ese tipo de persona y categoría.',
    'mantenimiento_bien.uq_mantenimiento_abierto': 'El bien ya tiene un mantenimiento abierto.',
    'solicitud_ampliacion.uq_solicitud_pendiente': 'Ya existe una solicitud de ampliación pendiente para ese bien.',
}


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
        try:
            self._cursor.execute(sql, parametros)
        except IntegrityError as error:
            # MySQL identifica el índice al final del error; no mostramos valores ni SQL.
            indice = (error.msg or '').rsplit('for key ', 1)[-1].strip("'`")
            if error.errno == 1062 and indice in MENSAJES_DUPLICADOS:
                raise Conflicto(MENSAJES_DUPLICADOS[indice]) from None
            raise
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
        """Devuelve el diccionario del actor con sus permisos, o None si no existe."""
        cuenta_actor = self.consultar_sql(
            '''SELECT u.id_usuario,u.dni_persona,u.rol,u.estado_cuenta,u.debe_cambiar_clave,
            p.estado AS estado_persona FROM usuario_sistema u JOIN persona p ON p.dni=u.dni_persona
            WHERE u.id_usuario=%s''',
            (identificador,),
            una=True,
        )
        if cuenta_actor:
            cuenta_actor['permisos'] = permisos_del_rol(cuenta_actor['rol'])
        return cuenta_actor

    def registrar_historial_estado(
        self, entidad, identificador, anterior, nuevo, actor, observacion, *, dni_objetivo=None, datos=None
    ):
        columnas = dict(entidad=entidad, id_entidad=identificador, estado_anterior=anterior,
                        estado_nuevo=nuevo, dni_responsable=actor, observacion=observacion)
        if dni_objetivo is not None:
            columnas['dni_objetivo'] = dni_objetivo
        if datos is not None:
            columnas['datos'] = json.dumps(datos, ensure_ascii=False)
        campos = ','.join(columnas)
        marcas = ','.join(['%s'] * len(columnas))
        return self.ejecutar(f'INSERT INTO historial_estado(fecha,{campos}) VALUES(UTC_TIMESTAMP(),{marcas})',
                             tuple(columnas.values()))

    def consultar_historial_estado(self, entidad, identificador):
        return self.consultar_sql(
            '''SELECT h.*,CONCAT(p.nombres,' ',p.apellidos) AS responsable
            FROM historial_estado h LEFT JOIN persona p ON p.dni=h.dni_responsable
            WHERE h.entidad=%s AND h.id_entidad=%s ORDER BY h.fecha DESC,h.id_historial_estado DESC''',
            (entidad, identificador),
        )
