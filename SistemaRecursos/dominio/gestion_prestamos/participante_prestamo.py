from dominio.gestion_personas_usuarios.validacion_persona import validar_dni
from dataclasses import dataclass
from dominio.gestion_recursos.validacion_recurso import entero, texto


@dataclass(kw_only=True)
class ParticipantePrestamo:
    dni_persona: str
    rol_participacion: str = "Integrante"
    responsable: bool = False
    id_participante: int | None = None

    def __post_init__(self):
        self.dni_persona = validar_dni(self.dni_persona)
        self.rol_participacion = texto(self.rol_participacion, "Rol de participación", 60, True)
