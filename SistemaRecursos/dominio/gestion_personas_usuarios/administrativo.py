from dataclasses import dataclass
from dominio.gestion_personas_usuarios.persona import Persona


@dataclass(kw_only=True)
class Administrativo(Persona):
    codigo_empleado: str | None = None
    area: str | None = None
    tipo = "ADMINISTRATIVO"

