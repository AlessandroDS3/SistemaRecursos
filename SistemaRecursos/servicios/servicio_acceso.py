from werkzeug.security import check_password_hash, generate_password_hash
from dominio.gestion_personas_usuarios.acceso import IRepositorioAcceso
from dominio.compartido.validacion import entero


class ServicioAplicacionAcceso:
    def __init__(self, repositorio: IRepositorioAcceso):
        self.repositorio = repositorio
        self._hash_ausente = generate_password_hash('cuenta-ausente', method='scrypt')

    def autenticar_cuenta(self, nombre, clave):
        """Devuelve una CuentaAcceso activa si la contraseña coincide; en otro caso, None."""
        if (
            not isinstance(nombre, str)
            or not isinstance(clave, str)
            or len(nombre) > 50
            or len(clave) > 256
        ):
            return None
        cuenta_acceso = self.repositorio.consultar_cuenta_por_usuario(nombre.strip())
        hash_a_comprobar = cuenta_acceso.contrasena_hash if cuenta_acceso else self._hash_ausente
        try:
            correcta = check_password_hash(hash_a_comprobar, clave)
        except (ValueError, TypeError):
            correcta = False
        if cuenta_acceso is None or not correcta:
            return None
        if not cuenta_acceso.puede_acceder():
            return None
        self.repositorio.registrar_acceso(cuenta_acceso.id_usuario)
        return cuenta_acceso

    def consultar_cuenta_activa(self, identificador):
        """Recupera una CuentaAcceso activa, o None si el identificador o el estado no sirven."""
        try:
            cuenta_acceso = self.repositorio.consultar_cuenta_por_id(entero(identificador))
        except ValueError:
            return None
        if cuenta_acceso is None or not cuenta_acceso.puede_acceder():
            return None
        return cuenta_acceso
