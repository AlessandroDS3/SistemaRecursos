from enum import Enum
from dominio.gestion_personas_usuarios.nombre_rol import NombreRol
from dataclasses import dataclass
from datetime import datetime
from dominio.gestion_personas_usuarios.persona import Persona
from dominio.gestion_personas_usuarios.rol import Rol
from dominio.gestion_personas_usuarios.credenciales import Credenciales


class EstadoCuenta(str, Enum):
    ACTIVA = "ACTIVA"
    INACTIVA = "INACTIVA"
    BLOQUEADA = "BLOQUEADA"


@dataclass(kw_only=True)
class UsuarioSistema:
    persona: Persona
    rol: Rol
    credenciales: Credenciales
    id_usuario: int | None = None
    ultimo_acceso: datetime | None = None
    estado_cuenta: EstadoCuenta = EstadoCuenta.ACTIVA

    def __post_init__(self):
        self.estado_cuenta = EstadoCuenta(self.estado_cuenta)

    @property
    def activo(self):
        return self.estado_cuenta == EstadoCuenta.ACTIVA

    def puede_acceder(self):
        return (
            self.activo
            and self.persona.esta_activa()
        )


def es_administrador_activo(cuenta):
    return (cuenta["rol"] == NombreRol.ADMINISTRADOR
            and cuenta["estado_cuenta"] == EstadoCuenta.ACTIVA
            and cuenta["estado_persona"] == "ACTIVA")


def validar_baja_persona(dni, id_usuario_actor, cuentas):
    cuentas_persona = []
    for cuenta in cuentas:
        if cuenta["dni_persona"] == dni:
            cuentas_persona.append(cuenta)

    for cuenta in cuentas_persona:
        if cuenta["id_usuario"] == id_usuario_actor:
            raise ValueError("No puedes desactivar la persona de la cuenta con la que estás trabajando.")

    tiene_cuenta_administradora = False
    for cuenta in cuentas_persona:
        if es_administrador_activo(cuenta):
            tiene_cuenta_administradora = True
            break
    if not tiene_cuenta_administradora:
        return

    for cuenta in cuentas:
        if cuenta["dni_persona"] != dni and es_administrador_activo(cuenta):
            return
    raise ValueError("Debe conservarse al menos una cuenta administradora activa.")


def validar_conservacion_administrador(cuenta_actual, cuenta_nueva, cuentas):
    """Impide quitar acceso a la ultima cuenta administradora activa."""
    era_administrador = es_administrador_activo(cuenta_actual)
    seguira_siendo_administrador = es_administrador_activo(cuenta_nueva)
    if era_administrador and not seguira_siendo_administrador:
        hay_otro_administrador = False
        for cuenta in cuentas:
            if cuenta["id_usuario"] == cuenta_actual["id_usuario"]:
                continue
            if es_administrador_activo(cuenta):
                hay_otro_administrador = True
                break
        if not hay_otro_administrador:
            raise ValueError("Debe conservarse al menos una cuenta administradora activa.")
