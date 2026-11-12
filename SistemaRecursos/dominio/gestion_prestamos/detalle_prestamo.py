from dataclasses import dataclass
from datetime import datetime
from dominio.gestion_recursos.bien_material import CondicionBien
from dominio.gestion_recursos.validacion_recurso import entero, texto
from dominio.gestion_personas_usuarios.validacion_persona import validar_dni


@dataclass(kw_only=True)
class DetallePrestamo:
    id_bien: int
    id_politica: int
    fecha_limite_devolucion: datetime
    condicion_entrega: CondicionBien = CondicionBien.BUENO
    observaciones_entrega: str = ""
    fecha_devolucion: datetime | None = None
    dni_encargado_devolucion: str | None = None
    condicion_devolucion: CondicionBien | None = None
    observaciones_devolucion: str | None = None
    id_detalle: int | None = None

    def __post_init__(self):
        self.id_bien = entero(self.id_bien, "Bien")
        self.id_politica = entero(self.id_politica, "Política")
        self.condicion_entrega = CondicionBien(self.condicion_entrega)
        self.observaciones_entrega = texto(self.observaciones_entrega, "Observaciones de entrega", 255)
        if self.fecha_devolucion is None:
            if any(valor is not None for valor in (self.dni_encargado_devolucion,
                    self.condicion_devolucion, self.observaciones_devolucion)):
                raise ValueError("La devolución debe tener fecha, encargado y condición juntos.")
        else:
            if not isinstance(self.fecha_devolucion, datetime):
                raise ValueError("La fecha de devolución no es válida.")
            self.dni_encargado_devolucion = validar_dni(self.dni_encargado_devolucion)
            self.condicion_devolucion = CondicionBien(self.condicion_devolucion)
            self.observaciones_devolucion = texto(self.observaciones_devolucion, "Observaciones de devolución", 255) or None

    def pendiente(self):
        return self.fecha_devolucion is None
