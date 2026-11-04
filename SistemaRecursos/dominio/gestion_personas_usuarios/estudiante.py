from dataclasses import dataclass
from dominio.gestion_personas_usuarios.persona import Persona


ESTADOS_MATRICULA_VIGENTE = ("VIGENTE",)


def tiene_matricula_vigente(estado):
    return isinstance(estado, str) and estado == "vigente"


@dataclass(kw_only=True)
class Estudiante(Persona):
    cui: str
    estado_matricula: str
    ciclo: int | None = None
    semestre_academico: str | None = None
    tipo = "ESTUDIANTE"

    def __post_init__(self):
        super().__post_init__()
        if self.semestre_academico is not None:
            self.semestre_academico = self.semestre_academico.strip() or None

    def matricula_vigente(self):
        return self.esta_activa() and tiene_matricula_vigente(self.estado_matricula)
