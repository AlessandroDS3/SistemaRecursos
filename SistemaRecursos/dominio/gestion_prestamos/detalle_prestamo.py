from dataclasses import dataclass
from datetime import datetime
from dominio.gestion_recursos.bien_material import EstadoBienMaterial
from dominio.gestion_recursos.validacion_recurso import entero, texto


@dataclass(kw_only=True)
class DetallePrestamo:
    id_bien_ref: int
    id_politica_ref: int
    fecha_limite_devolucion: datetime
    estado_entrega: EstadoBienMaterial = EstadoBienMaterial.DISPONIBLE
    estado_devolucion: EstadoBienMaterial | None = None
    observaciones: str = ""
    id_detalle: int | None = None

    def __post_init__(self):
        self.id_bien_ref = entero(self.id_bien_ref, "Bien")
        self.id_politica_ref = entero(self.id_politica_ref, "Política")
        self.estado_entrega = EstadoBienMaterial(self.estado_entrega)
        if self.estado_devolucion is not None:
            self.estado_devolucion = EstadoBienMaterial(self.estado_devolucion)
        self.observaciones = texto(self.observaciones, "Observaciones", 255)

    def pendiente(self):
        return self.estado_devolucion is None
