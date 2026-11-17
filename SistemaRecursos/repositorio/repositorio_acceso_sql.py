from dominio.gestion_personas_usuarios.acceso import CuentaAcceso
from repositorio.base_sql import RepositorioSQL


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
        permisos = self.consultar_sql(
            'SELECT permiso FROM rol_permiso WHERE rol=%s', (fila_cuenta['rol'],)
        )
        return CuentaAcceso(**fila_cuenta, permisos=frozenset(p['permiso'] for p in permisos))

    def consultar_cuenta_por_usuario(self, nombre):
        return self._consultar_cuenta('u.nombre_usuario', nombre)

    def consultar_cuenta_por_id(self, identificador):
        return self._consultar_cuenta('u.id_usuario', identificador)

    def registrar_acceso(self, identificador):
        with self.transaccion() as operacion:
            operacion.ejecutar(
                'UPDATE usuario_sistema SET ultimo_acceso=UTC_TIMESTAMP() WHERE id_usuario=%s',
                (identificador,),
            )
