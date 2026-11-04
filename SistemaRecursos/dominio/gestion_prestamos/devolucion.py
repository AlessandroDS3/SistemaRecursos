from dominio.gestion_personas_usuarios.validacion_persona import validar_dni
from dataclasses import dataclass
from datetime import datetime
from dominio.gestion_recursos.validacion_recurso import entero, texto
from dominio.gestion_recursos.bien_material import ESTADOS_RECEPCION


@dataclass(kw_only=True)
class Devolucion:
    id_detalle_ref: int
    dni_encargado: str
    estado_devolucion: str = "DISPONIBLE"
    observaciones: str = ""
    fecha: datetime | None = None
    id_devolucion: int | None = None

    def __post_init__(self):
        self.id_detalle_ref = entero(self.id_detalle_ref, "Detalle del préstamo")
        self.dni_encargado = validar_dni(self.dni_encargado)
        if self.estado_devolucion not in ESTADOS_RECEPCION:
            raise ValueError(
                "La recepción solo permite disponible, dañado o mantenimiento. Una pérdida sigue pendiente de devolución."
            )
        self.observaciones = texto(self.observaciones, "Observaciones de devolución", 255)
        if self.estado_devolucion != "DISPONIBLE" and not self.observaciones:
            raise ValueError("Describe la condición del bien dañado o en mantenimiento.")
