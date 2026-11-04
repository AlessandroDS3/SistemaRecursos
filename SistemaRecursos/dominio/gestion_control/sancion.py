from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from dominio.gestion_personas_usuarios.validacion_persona import validar_dni
from dominio.gestion_recursos.validacion_recurso import texto


class EstadoSancion(str, Enum):
    ACTIVA = 'ACTIVA'
    CUMPLIDA = 'CUMPLIDA'
    LEVANTADA = 'LEVANTADA'
    ANULADA = 'ANULADA'


@dataclass(kw_only=True)
class Sancion:
    dni_persona: str
    id_sancion: int | None = None
    id_detalle_vencido_ref: int | None = None
    estado: EstadoSancion = EstadoSancion.ACTIVA
    fecha_levantamiento: datetime | None = None
    dni_levantamiento: str | None = None
    justificacion_levantamiento: str | None = None

    def __post_init__(self):
        self.dni_persona = validar_dni(self.dni_persona)
        self.estado = EstadoSancion(self.estado)

    def levantar(self, justificacion, dni_encargado, fecha):
        if self.estado != EstadoSancion.ACTIVA:
            raise ValueError('La sanción por tardanza ya fue retirada.')
        self.justificacion_levantamiento = texto(justificacion, 'Justificación para quitar la sanción', 255, True)
        self.dni_levantamiento = validar_dni(dni_encargado)
        self.fecha_levantamiento = fecha
        self.estado = EstadoSancion.LEVANTADA
