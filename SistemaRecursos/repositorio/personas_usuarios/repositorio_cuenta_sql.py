"""Persistencia de cuentas; los permisos y estados se deciden en servicios/dominio."""

from dominio.compartido.validacion import Conflicto
from repositorio.base_datos.base_sql import RepositorioSQL


def consultar_y_bloquear_cuentas_para_edicion(repo) -> list[dict]:
    """Bloquea cuentas y personas en orden de cuenta hasta terminar la transacción."""
    return repo.consultar_sql('''SELECT u.id_usuario,u.dni_persona,u.nombre_usuario,
        u.contrasena_hash,u.debe_cambiar_clave,u.rol,u.estado_cuenta,
        p.estado AS estado_persona FROM usuario_sistema u JOIN persona p ON p.dni=u.dni_persona
        ORDER BY u.id_usuario FOR UPDATE''')


class RepositorioCuentaSQL(RepositorioSQL):
    def consultar_persona_para_cuenta(self, documento: str, bloquear=False) -> dict | None:
        return self.consultar_sql(
            '''SELECT p.dni,p.correo,p.estado,e.cui FROM persona p
            LEFT JOIN estudiante e ON e.dni=p.dni WHERE p.dni=%s'''
            + (' FOR UPDATE' if bloquear else ''),
            (documento,),
            una=True,
        )

    def consultar_nombres_usuario(self, prefijo: str) -> list[str]:
        prefijo = prefijo.replace('!', '!!').replace('%', '!%').replace('_', '!_')
        filas = self.consultar_sql(
            "SELECT nombre_usuario FROM usuario_sistema WHERE nombre_usuario LIKE %s ESCAPE '!'",
            (prefijo + '%',),
        )
        return [fila['nombre_usuario'] for fila in filas]

    def consultar_id_por_nombre_usuario(self, nombre: str) -> int | None:
        fila = self.consultar_sql(
            'SELECT id_usuario FROM usuario_sistema WHERE nombre_usuario=%s',
            (nombre,),
            una=True,
        )
        return fila['id_usuario'] if fila else None

    def consultar_cuenta_para_cambiar_clave(self, identificador: int) -> dict | None:
        return self.consultar_sql(
            '''SELECT u.id_usuario,u.dni_persona,u.contrasena_hash,u.debe_cambiar_clave,u.estado_cuenta,p.estado AS estado_persona
            FROM usuario_sistema u JOIN persona p ON p.dni=u.dni_persona
            WHERE u.id_usuario=%s FOR UPDATE''',
            (identificador,),
            una=True,
        )

    def consultar_cuenta(self, documento: str) -> dict | None:
        return self.consultar_sql(
            '''SELECT u.id_usuario,u.dni_persona,u.nombre_usuario,u.contrasena_hash,
            u.rol,u.estado_cuenta,u.debe_cambiar_clave,u.ultimo_acceso,p.estado AS estado_persona
            FROM usuario_sistema u JOIN persona p ON p.dni=u.dni_persona WHERE u.dni_persona=%s''',
            (documento,),
            una=True,
        )

    def consultar_cuentas_para_actualizar(self) -> list[dict]:
        return consultar_y_bloquear_cuentas_para_edicion(self)

    def cerrar_sesiones_de_cuenta(self, identificador):
        cerrar_sesiones_de_cuenta(self, identificador)

    def registrar_cuenta(self, documento: str, nombre: str, hash_clave: str) -> int:
        return self._insertar_cuenta(documento, nombre, hash_clave, 'USUARIO')

    def registrar_primera_cuenta_administradora(self, persona, nombre: str, hash_clave: str) -> int:
        from repositorio.personas_usuarios.repositorio_persona_sql import RepositorioPersonaSQL

        # La sesión conserva el bloqueo hasta después del commit y lo libera al cerrarse.
        bloqueo = self.consultar_sql(
            "SELECT GET_LOCK(SHA2(CONCAT(DATABASE(), ':primer_administrador'), 256), 5) AS obtenido",
            una=True,
        )
        if bloqueo['obtenido'] != 1:
            raise Conflicto('Hay otra inicialización en curso. Inténtalo de nuevo.')
        if self.consultar_sql('SELECT id_usuario FROM usuario_sistema LIMIT 1', una=True):
            raise Conflicto('La base ya tiene cuentas. Gestiona los roles desde la aplicación.')
        RepositorioPersonaSQL(self.conexion, self._cursor).guardar_persona(persona)
        return self._insertar_cuenta(persona.dni, nombre, hash_clave, 'ADMINISTRADOR')

    def _insertar_cuenta(self, documento: str, nombre: str, hash_clave: str, rol: str) -> int:
        return self.insertar_fila_sql(
            'usuario_sistema',
            dict(
                dni_persona=documento,
                nombre_usuario=nombre,
                contrasena_hash=hash_clave,
                debe_cambiar_clave=True,
                rol=rol,
                estado_cuenta='ACTIVA',
            ),
        )

    def actualizar_cuenta(self, identificador: int, datos: dict) -> None:
        permitidos = {
            'nombre_usuario',
            'contrasena_hash',
            'debe_cambiar_clave',
            'rol',
            'estado_cuenta',
        }
        if set(datos) - permitidos:
            raise ValueError('Campo de cuenta desconocido.')
        if datos:
            columnas = ','.join(campo + '=%s' for campo in datos)
            self.ejecutar_escritura_sql(
                'UPDATE usuario_sistema SET ' + columnas + ' WHERE id_usuario=%s',
                (*datos.values(), identificador),
            )


def cerrar_sesiones_de_cuenta(repo, identificador):
    repo.ejecutar_escritura_sql('''UPDATE sesion_usuario SET fecha_cierre=UTC_TIMESTAMP()
        WHERE id_usuario=%s AND fecha_cierre IS NULL''', (identificador,))
