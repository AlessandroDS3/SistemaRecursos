from __future__ import annotations

from dominio.gestion_personas_usuarios.i_repositorio_rol import IRepositorioRol
from dominio.gestion_personas_usuarios.i_repositorio_persona import IRepositorioPersona
from dominio.gestion_personas_usuarios.i_repositorio_acceso import IRepositorioAcceso
from dominio.gestion_personas_usuarios.validacion_persona import validar_dni
from hashlib import sha256
from dominio.gestion_personas_usuarios.nombre_rol import NombreRol
from servicios.validacion_identificadores import identificador
from werkzeug.security import check_password_hash, generate_password_hash
from dominio.gestion_personas_usuarios.usuario_sistema import UsuarioSistema
from dominio.gestion_personas_usuarios.credenciales import Credenciales


class ServicioAplicacionAcceso:
    def __init__(self, repositorio_cuentas: IRepositorioAcceso, repositorio_personas: IRepositorioPersona | None = None, repositorio_roles: IRepositorioRol | None = None):
        if repositorio_cuentas is None:
            raise RuntimeError("El servicio de acceso requiere un repositorio de cuentas.")
        self.usuarios: IRepositorioAcceso = repositorio_cuentas
        self.personas: IRepositorioPersona | None = repositorio_personas
        self.roles: IRepositorioRol | None = repositorio_roles
        self._hash_inexistente = generate_password_hash("usuario-inexistente", method="scrypt")

    @staticmethod
    def version_credenciales(cuenta):
        # La cookie guarda una huella, no el hash de contraseña de la base.
        return sha256(cuenta.credenciales.contrasena_hash.encode("utf-8")).hexdigest()

    @staticmethod
    def _nombre_usuario(nombre):
        if not isinstance(nombre, str) or not nombre.strip() or len(nombre.strip()) > 50:
            raise ValueError("Nombre de usuario: obligatorio, máximo 50 caracteres.")
        return nombre.strip()

    @staticmethod
    def _hash_clave(clave):
        if not isinstance(clave, str) or not 12 <= len(clave) <= 256:
            raise ValueError("La contraseña debe tener entre 12 y 256 caracteres.")
        return generate_password_hash(clave, method="scrypt")

    def autenticar(self, usuario, clave):
        if (
            not isinstance(usuario, str)
            or not isinstance(clave, str)
            or len(usuario) > 50
            or len(clave) > 256
        ):
            return None
        cuenta = self.usuarios.consultar_por_nombre_usuario(usuario.strip())
        hash_clave = cuenta.credenciales.contrasena_hash if cuenta else self._hash_inexistente
        try:
            correcta = check_password_hash(hash_clave, clave)
        except (ValueError, TypeError):
            correcta = False
        if not correcta or cuenta is None or not cuenta.puede_acceder():
            return None
        self.usuarios.registrar_acceso(cuenta.id_usuario)
        return cuenta

    def consultar_usuario_activo(self, id_usuario):
        try:
            id_usuario = identificador(id_usuario)
        except ValueError:
            return None
        cuenta = self.usuarios.consultar_cuenta_por_id(id_usuario)
        if not cuenta or not cuenta.puede_acceder():
            return None
        return cuenta

    def consultar_cuenta_persona(self, dni) -> UsuarioSistema | None:
        return self.usuarios.consultar_cuenta_persona(validar_dni(dni))

    def consultar_resumen_cuentas(self, dnis_persona) -> dict[str, dict[str, bool]]:
        return self.usuarios.consultar_resumen_cuentas(dnis_persona)

    def registrar_cuenta(self, dni, nombre_usuario, clave) -> UsuarioSistema:
        if self.personas is None:
            raise RuntimeError("El servicio de acceso requiere un repositorio de personas.")
        if self.roles is None:
            raise RuntimeError("El servicio de acceso requiere un repositorio de roles.")
        nombre_usuario = self._nombre_usuario(nombre_usuario)
        persona = self.personas.consultar_persona(validar_dni(dni))
        rol = next((rol for rol in self.roles.consultar_roles() if rol.nombre == NombreRol.USUARIO and rol.activo), None)
        if not persona or not persona.esta_activa():
            raise ValueError("La persona debe estar activa para crear su cuenta.")
        if rol is None:
            raise ValueError("El rol Usuario debe estar activo para crear cuentas.")
        hash_clave = self._hash_clave(clave)
        cuenta = UsuarioSistema(
            persona=persona, rol=rol, credenciales=Credenciales(nombre_usuario, hash_clave)
        )
        return self.usuarios.registrar_cuenta(cuenta)

    def consultar_cuenta(self, dni):
        cuenta = self.consultar_cuenta_persona(dni)
        if not cuenta:
            raise LookupError("Esta persona todavía no tiene una cuenta de acceso.")
        return cuenta

    def actualizar_cuenta(self, dni, datos, id_usuario_actor) -> UsuarioSistema:
        id_usuario_actor = identificador(id_usuario_actor)
        cuenta = self.consultar_cuenta(dni)
        nombre = self._nombre_usuario(datos.get("nombre_usuario"))
        clave = datos.get("clave", "")
        hash_clave = self._hash_clave(clave) if clave != "" else None
        # La edición no reactiva una cuenta ni cambia la persona asociada.
        return self.usuarios.actualizar_cuenta(
            cuenta.id_usuario,
            nombre_usuario=nombre,
            contrasena_hash=hash_clave,
            id_usuario_actor=id_usuario_actor,
        )

    def cambiar_estado_cuenta(self, dni, activar, id_usuario_actor):
        if not isinstance(activar, bool):
            raise ValueError("La activación debe ser verdadera o falsa.")
        id_usuario_actor = identificador(id_usuario_actor)
        cuenta = self.consultar_cuenta(dni)
        return self.usuarios.actualizar_cuenta(
            cuenta.id_usuario, activar=activar, id_usuario_actor=id_usuario_actor
        )
