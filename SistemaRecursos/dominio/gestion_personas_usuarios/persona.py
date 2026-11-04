from enum import Enum
from dataclasses import dataclass
from dominio.gestion_personas_usuarios.validacion_persona import validar_datos_persona


class EstadoPersona(str, Enum):
    ACTIVA = "ACTIVA"
    INACTIVA = "INACTIVA"


@dataclass(kw_only=True)
class Persona:
    dni: str
    nombres: str
    apellidos: str
    correo: str
    telefono: str = ""
    estado: EstadoPersona = EstadoPersona.ACTIVA

    def __post_init__(self):
        self.estado = EstadoPersona(self.estado)
        validar_datos_persona(dict(vars(self), tipo=self.tipo))
        self.nombres = self.nombres.strip()
        self.apellidos = self.apellidos.strip()
        self.correo = self.correo.strip()
        self.telefono = self.telefono.strip()

    @property
    def documento_identidad(self):
        return self.dni

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"

    def esta_activa(self):
        return self.estado == EstadoPersona.ACTIVA
