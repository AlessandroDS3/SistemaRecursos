from dominio.cuentas import IRepositorioAcceso
from dominio.validaciones import entero as identificador
from hashlib import sha256
from werkzeug.security import check_password_hash, generate_password_hash


class ServicioAplicacionAcceso:
    """Autentica cuentas y recupera sesiones; solo necesita el contrato de acceso."""

    def __init__(self, repositorio_acceso: IRepositorioAcceso):
        if repositorio_acceso is None:
            raise RuntimeError("El servicio de acceso requiere un repositorio de cuentas.")
        self.repositorio = repositorio_acceso
        self._hash_inexistente = generate_password_hash("usuario-inexistente", method="scrypt")

    @staticmethod
    def version_credenciales(cuenta):
        # La cookie guarda una huella, no el hash de contraseña de la base.
        return sha256(cuenta.credenciales.contrasena_hash.encode("utf-8")).hexdigest()

    def autenticar(self, usuario, clave):
        if (not isinstance(usuario, str) or not isinstance(clave, str)
                or len(usuario) > 50 or len(clave) > 256):
            return None
        cuenta = self.repositorio.consultar_por_nombre_usuario(usuario.strip())
        hash_clave = cuenta.credenciales.contrasena_hash if cuenta else self._hash_inexistente
        try:
            correcta = check_password_hash(hash_clave, clave)
        except (ValueError, TypeError):
            correcta = False
        if not correcta or cuenta is None or not cuenta.puede_acceder():
            return None
        self.repositorio.registrar_acceso(cuenta.id_usuario)
        return cuenta

    def consultar_usuario_activo(self, id_usuario):
        try:
            id_usuario = identificador(id_usuario)
        except ValueError:
            return None
        cuenta = self.repositorio.consultar_cuenta_por_id(id_usuario)
        if not cuenta or not cuenta.puede_acceder():
            return None
        return cuenta
