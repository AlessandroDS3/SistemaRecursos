from dataclasses import dataclass
from dominio.gestion_personas_usuarios.persona import Persona


ESTADOS_MATRICULA_VIGENTE = ("VIGENTE",)


def tiene_matricula_vigente(estado):
    return isinstance(estado, str) and estado == "VIGENTE"


@dataclass(kw_only=True)
class Estudiante(Persona):
    cui: str
    estado_matricula: str
    ciclo: int | None = None
    tipo = "ESTUDIANTE"

    def matricula_vigente(self):
        return self.esta_activa() and tiene_matricula_vigente(self.estado_matricula)
