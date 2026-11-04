from dataclasses import dataclass
from datetime import datetime


@dataclass(kw_only=True)
class HistorialPrestamo:
    id_prestamo: int
    estado_nuevo: str
    fecha: datetime
    dni_responsable: str
    estado_anterior: str | None = None
    observacion: str = ""
    id_historial: int | None = None
