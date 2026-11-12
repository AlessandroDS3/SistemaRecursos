"""Datos de entrada para recibir un bien; se guardan en detalle_prestamo."""
from dataclasses import dataclass
from dominio.gestion_personas_usuarios.validacion_persona import validar_dni
from dominio.gestion_recursos.validacion_recurso import entero, texto
from dominio.gestion_recursos.bien_material import CondicionBien, EstadoBienMaterial


@dataclass(kw_only=True)
class Devolucion:
    id_detalle: int
    dni_encargado: str
    condicion_devolucion: CondicionBien = CondicionBien.BUENO
    observaciones: str = ""

    def __post_init__(self):
        self.id_detalle = entero(self.id_detalle, "Detalle del préstamo")
        self.dni_encargado = validar_dni(self.dni_encargado)
        try:
            self.condicion_devolucion = CondicionBien(self.condicion_devolucion)
        except (ValueError, TypeError):
            raise ValueError("Selecciona bueno o dañado. Un bien perdido sigue pendiente de devolución.") from None
        self.observaciones = texto(self.observaciones, "Observaciones de devolución", 255)
        if self.condicion_devolucion == CondicionBien.DANADO and not self.observaciones:
            raise ValueError("Describe los daños del bien recibido.")

    @property
    def estado_bien(self):
        return (EstadoBienMaterial.DISPONIBLE if self.condicion_devolucion == CondicionBien.BUENO
                else EstadoBienMaterial.DANADO)
