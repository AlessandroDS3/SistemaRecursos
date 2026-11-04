from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timezone
from dominio.gestion_recursos.validacion_recurso import texto, entero, instante_utc


class EstadoFueraServicio(str, Enum):
    ACTIVO = "ACTIVO"
    RESUELTO = "RESUELTO"


@dataclass(kw_only=True)
class RegistroFueraServicio:
    id_bien_ref: int
    motivo: str
    fecha_inicio: datetime
    descripcion: str = ""
    fecha_fin_estimada: datetime | None = None
    fecha_fin_real: datetime | None = None
    estado: EstadoFueraServicio = EstadoFueraServicio.ACTIVO
    id_registro: int | None = None

    def __post_init__(self):
        self.id_bien_ref = entero(self.id_bien_ref, "Bien")
        self.motivo = texto(self.motivo, "Motivo", 255, True)
        self.descripcion = texto(self.descripcion, "Descripción", 255)
        try:
            self.estado = EstadoFueraServicio(self.estado)
        except (ValueError, TypeError):
            raise ValueError("El estado del registro fuera de servicio no es válido.") from None
        self.fecha_inicio = instante_utc(self.fecha_inicio, "Fecha de inicio")
        if self.fecha_fin_estimada is not None:
            self.fecha_fin_estimada = instante_utc(self.fecha_fin_estimada, "Fecha estimada")
            if self.fecha_fin_estimada < self.fecha_inicio:
                raise ValueError("Fecha estimada: no puede ser anterior al inicio.")

        if self.fecha_fin_real is not None:
            self.fecha_fin_real = instante_utc(self.fecha_fin_real, "Fecha de cierre")
            if self.fecha_fin_real < self.fecha_inicio:
                raise ValueError("Fecha de cierre: no puede ser anterior al inicio.")

        if self.estado == EstadoFueraServicio.ACTIVO and self.fecha_fin_real is not None:
            raise ValueError("Un registro activo no puede tener fecha de cierre.")
        if self.estado == EstadoFueraServicio.RESUELTO and self.fecha_fin_real is None:
            raise ValueError("Un registro resuelto debe tener fecha de cierre.")

    def cerrar_registro(self, fecha_cierre=None):
        if self.estado != EstadoFueraServicio.ACTIVO:
            raise ValueError("El registro ya está cerrado.")
        cierre = instante_utc(
            datetime.now(timezone.utc) if fecha_cierre is None else fecha_cierre,
            "Fecha de cierre",
        )
        if cierre < self.fecha_inicio:
            raise ValueError("La fecha de cierre no puede ser anterior al inicio.")
        self.fecha_fin_real = cierre
        self.estado = EstadoFueraServicio.RESUELTO
