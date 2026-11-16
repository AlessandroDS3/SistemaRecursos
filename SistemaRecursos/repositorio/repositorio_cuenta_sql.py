"""Persistencia de cuentas; los permisos y estados se deciden en servicios/dominio."""

from repositorio.base_sql import RepositorioSQL


def cargar_cuentas_para_actualizar(repo) -> list[dict]:
    """Bloquea cuentas y personas en orden de cuenta hasta terminar la transacción."""
    return repo.consultar_sql('''SELECT u.id_usuario,u.dni_persona,u.nombre_usuario,
        u.contrasena_hash,u.rol,u.estado_cuenta,
        p.estado AS estado_persona FROM usuario_sistema u JOIN persona p ON p.dni=u.dni_persona
        ORDER BY u.id_usuario FOR UPDATE''')


class RepositorioCuentaSQL(RepositorioSQL):
    def consultar_cuenta_para_cambiar_clave(self, identificador: int) -> dict | None:
        return self.consultar_sql(
            '''SELECT u.id_usuario,u.contrasena_hash,u.estado_cuenta,p.estado AS estado_persona
            FROM usuario_sistema u JOIN persona p ON p.dni=u.dni_persona
            WHERE u.id_usuario=%s FOR UPDATE''',
            (identificador,),
            una=True,
        )

    def consultar_cuenta(self, documento: str) -> dict | None:
        return self.consultar_sql(
            '''SELECT u.id_usuario,u.dni_persona,u.nombre_usuario,u.contrasena_hash,
            u.rol,u.estado_cuenta,u.ultimo_acceso,p.estado AS estado_persona
            FROM usuario_sistema u JOIN persona p ON p.dni=u.dni_persona WHERE u.dni_persona=%s''',
            (documento,),
            una=True,
        )

    def consultar_cuentas_para_actualizar(self) -> list[dict]:
        return cargar_cuentas_para_actualizar(self)

    def consultar_estado_persona(self, documento: str) -> str | None:
        fila = self.consultar_sql(
            'SELECT estado FROM persona WHERE dni=%s FOR UPDATE', (documento,), una=True
        )
        return fila['estado'] if fila else None

    def registrar_cuenta(self, documento: str, nombre: str, hash_clave: str) -> int:
        return self.insertar(
            'usuario_sistema',
            dict(
                dni_persona=documento,
                nombre_usuario=nombre,
                contrasena_hash=hash_clave,
                rol='USUARIO',
                estado_cuenta='ACTIVA',
            ),
        )

    def actualizar_cuenta(self, identificador: int, datos: dict) -> None:
        permitidos = {'nombre_usuario', 'contrasena_hash', 'rol', 'estado_cuenta'}
        if set(datos) - permitidos:
            raise ValueError('Campo de cuenta desconocido.')
        if datos:
            columnas = ','.join(campo + '=%s' for campo in datos)
            self.ejecutar(
                'UPDATE usuario_sistema SET ' + columnas + ' WHERE id_usuario=%s',
                (*datos.values(), identificador),
            )

    def buscar_cuentas(self, termino: str) -> list[dict]:
        return self.consultar_sql(
            '''SELECT u.id_usuario,u.dni_persona,u.nombre_usuario,u.rol,u.estado_cuenta,
            CONCAT(p.nombres,' ',p.apellidos) AS persona FROM usuario_sistema u
            JOIN persona p ON p.dni=u.dni_persona
            WHERE p.dni LIKE %s OR p.apellidos LIKE %s OR u.nombre_usuario LIKE %s
            ORDER BY p.apellidos,p.nombres LIMIT 50''',
            (f'%{termino}%',) * 3,
        )
