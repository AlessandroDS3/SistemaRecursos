from dataclasses import dataclass
from dominio.gestion_personas_usuarios.persona import Persona


@dataclass(kw_only=True)
class Docente(Persona):
    codigo_docente: str | None = None
    departamento_academico: str | None = None
    facultad: str | None = None
    escuela_profesional: str | None = None
    tipo = "DOCENTE"

