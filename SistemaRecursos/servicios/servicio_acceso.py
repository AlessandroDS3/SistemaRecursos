from werkzeug.security import check_password_hash, generate_password_hash
from dominio.gestion_personas_usuarios.acceso import IRepositorioAcceso
from dominio.compartido.validacion import entero


class ServicioAplicacionAcceso:
    def __init__(self, repositorio: IRepositorioAcceso):
        self.repositorio = repositorio
        self._hash_ausente = generate_password_hash('cuenta-ausente', method='scrypt')

    def autenticar_cuenta(self, nombre, clave):
        if (
            not isinstance(nombre, str)
            or not isinstance(clave, str)
            or len(nombre) > 50
            or len(clave) > 256
        ):
            return None
        cuenta = self.repositorio.consultar_cuenta_por_usuario(nombre.strip())
        try:
            correcta = check_password_hash(
                cuenta.contrasena_hash if cuenta else self._hash_ausente, clave
            )
        except (ValueError, TypeError):
            correcta = False
        if cuenta and correcta and cuenta.puede_acceder():
            self.repositorio.registrar_acceso(cuenta.id_usuario)
            return cuenta
        return None

    def consultar_cuenta_activa(self, identificador):
        try:
            cuenta = self.repositorio.consultar_cuenta_por_id(entero(identificador))
        except ValueError:
            return None
        return cuenta if cuenta and cuenta.puede_acceder() else None
