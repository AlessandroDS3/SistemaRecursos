from dominio.gestion_personas_usuarios.acceso import CuentaAcceso
from dominio.gestion_personas_usuarios.rol import Rol, permisos_del_rol
from repositorio.base_datos.base_sql import RepositorioSQL


class RepositorioAccesoSQL(RepositorioSQL):
    def _consultar_cuenta(self, columna, valor):
        """Convierte la fila SQL y los permisos del rol en una CuentaAcceso, o devuelve None."""
        # La columna procede únicamente de los dos métodos públicos siguientes.
        fila_cuenta = self.consultar_sql(
            f'''SELECT u.id_usuario,p.dni,u.nombre_usuario,u.contrasena_hash,
            u.rol,u.estado_cuenta,u.debe_cambiar_clave,p.estado AS estado_persona,p.nombres,p.apellidos
            FROM usuario_sistema u JOIN persona p ON p.dni=u.dni_persona WHERE {columna}=%s''',
            (valor,),
            una=True,
        )
        if fila_cuenta is None:
            return None
        fila_cuenta['rol'] = Rol(fila_cuenta['rol'])
        return CuentaAcceso(**fila_cuenta, permisos=permisos_del_rol(fila_cuenta['rol']))

    def consultar_cuenta_por_usuario(self, nombre):
        return self._consultar_cuenta('u.nombre_usuario', nombre)

    def consultar_cuenta_por_id(self, identificador):
        return self._consultar_cuenta('u.id_usuario', identificador)

    def registrar_ultimo_inicio_de_sesion(self, identificador):
        with self.transaccion() as operacion:
            operacion.ejecutar_escritura_sql(
                'UPDATE usuario_sistema SET ultimo_acceso=UTC_TIMESTAMP() WHERE id_usuario=%s',
                (identificador,),
            )

    def crear_sesion(self, huella, id_usuario):
        with self.transaccion() as operacion:
            operacion.ejecutar_escritura_sql(
                '''INSERT INTO sesion_usuario(id_sesion,id_usuario,fecha_inicio,ultima_actividad)
                VALUES(%s,%s,UTC_TIMESTAMP(),UTC_TIMESTAMP())''',
                (huella, id_usuario),
            )

    def consultar_sesion(self, huella):
        return self.consultar_sql(
            '''SELECT id_usuario,fecha_inicio,ultima_actividad,fecha_cierre
            FROM sesion_usuario WHERE id_sesion=%s''',
            (huella,),
            una=True,
        )

    def registrar_actividad_sesion(self, huella):
        with self.transaccion() as operacion:
            operacion.ejecutar_escritura_sql(
                '''UPDATE sesion_usuario SET ultima_actividad=UTC_TIMESTAMP()
                WHERE id_sesion=%s AND fecha_cierre IS NULL''',
                (huella,),
            )

    def cerrar_sesion(self, huella):
        with self.transaccion() as operacion:
            operacion.ejecutar_escritura_sql(
                '''UPDATE sesion_usuario SET fecha_cierre=UTC_TIMESTAMP()
                WHERE id_sesion=%s AND fecha_cierre IS NULL''',
                (huella,),
            )
