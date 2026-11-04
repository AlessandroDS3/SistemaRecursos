from enum import Enum
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
            and self.rol.activo
        )
