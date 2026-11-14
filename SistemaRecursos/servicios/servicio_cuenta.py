from dominio.cuentas import (
    Credenciales,
    IRepositorioCuenta,
    IRepositorioRol,
    IdentidadAcceso,
    NombreRol,
    UsuarioSistema,
)
from dominio.personas import IRepositorioPersona, validar_dni
from dominio.validaciones import entero as identificador
from werkzeug.security import generate_password_hash


class ServicioAplicacionCuenta:
    """Crea y administra cuentas; el inicio de sesión pertenece al servicio de acceso."""

    def __init__(self, repositorio_cuentas: IRepositorioCuenta,
                 repositorio_personas: IRepositorioPersona, repositorio_roles: IRepositorioRol):
        self.repositorio = repositorio_cuentas
        self.personas = repositorio_personas
        self.roles = repositorio_roles

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

    def consultar_cuenta_persona(self, dni) -> UsuarioSistema | None:
        return self.repositorio.consultar_cuenta_persona(validar_dni(dni))

    def consultar_resumen_cuentas(self, dnis_persona) -> dict[str, dict[str, bool]]:
        return self.repositorio.consultar_resumen_cuentas(dnis_persona)

    def consultar_cuenta(self, dni) -> UsuarioSistema:
        cuenta = self.consultar_cuenta_persona(dni)
        if not cuenta:
            raise LookupError("Esta persona todavía no tiene una cuenta de acceso.")
        return cuenta

    def registrar_cuenta(self, dni, nombre_usuario, clave) -> UsuarioSistema:
        nombre_usuario = self._nombre_usuario(nombre_usuario)
        persona = self.personas.consultar_persona(validar_dni(dni))
        rol = next((rol for rol in self.roles.consultar_roles() if rol.nombre == NombreRol.USUARIO), None)
        if not persona or not persona.esta_activa():
            raise ValueError("La persona debe estar activa para crear su cuenta.")
        if rol is None:
            raise ValueError("El rol Usuario debe existir para crear cuentas.")
        cuenta = UsuarioSistema(
            persona=IdentidadAcceso(dni=persona.dni, nombres=persona.nombres,
                                   apellidos=persona.apellidos, estado=persona.estado.value),
            rol=rol, credenciales=Credenciales(nombre_usuario, self._hash_clave(clave)),
        )
        return self.repositorio.registrar_cuenta(cuenta)

    def actualizar_cuenta(self, dni, datos, id_usuario_actor) -> UsuarioSistema:
        id_usuario_actor = identificador(id_usuario_actor)
        cuenta = self.consultar_cuenta(dni)
        nombre = self._nombre_usuario(datos.get("nombre_usuario"))
        clave = datos.get("clave", "")
        hash_clave = self._hash_clave(clave) if clave != "" else None
        return self.repositorio.actualizar_cuenta(
            cuenta.id_usuario, nombre_usuario=nombre, contrasena_hash=hash_clave,
            id_usuario_actor=id_usuario_actor,
        )

    def cambiar_estado_cuenta(self, dni, activar, id_usuario_actor):
        if not isinstance(activar, bool):
            raise ValueError("La activación debe ser verdadera o falsa.")
        id_usuario_actor = identificador(id_usuario_actor)
        cuenta = self.consultar_cuenta(dni)
        return self.repositorio.actualizar_cuenta(
            cuenta.id_usuario, activar=activar, id_usuario_actor=id_usuario_actor,
        )
