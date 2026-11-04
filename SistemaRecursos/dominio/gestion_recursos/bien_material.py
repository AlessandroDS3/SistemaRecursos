from enum import Enum
from dataclasses import dataclass
from datetime import date
from dominio.gestion_recursos.validacion_recurso import entero, texto, fecha


class EstadoBienMaterial(str, Enum):
    DISPONIBLE = "DISPONIBLE"
    PRESTADO = "PRESTADO"
    RESERVADO = "RESERVADO"
    DANADO = "DANADO"
    MANTENIMIENTO = "MANTENIMIENTO"
    PERDIDO = "PERDIDO"


ESTADOS_FUERA_SERVICIO = frozenset({
    EstadoBienMaterial.DANADO, EstadoBienMaterial.MANTENIMIENTO, EstadoBienMaterial.PERDIDO,
})
ESTADOS_CAMBIO_MANUAL = ESTADOS_FUERA_SERVICIO | {EstadoBienMaterial.DISPONIBLE}
ESTADOS_GESTION_PRESTAMOS = frozenset({EstadoBienMaterial.PRESTADO, EstadoBienMaterial.RESERVADO})
ESTADOS_RECEPCION = frozenset({
    EstadoBienMaterial.DISPONIBLE, EstadoBienMaterial.DANADO, EstadoBienMaterial.MANTENIMIENTO,
})


@dataclass(kw_only=True)
class BienMaterial:
    id_recurso_ref: int
    codigo_inventario: str
    fecha_adquisicion: date
    numero_serie: str = ""
    descripcion_bien: str = ""
    ubicacion: str = ""
    estado: EstadoBienMaterial = EstadoBienMaterial.DISPONIBLE
    id_bien: int | None = None

    def __post_init__(self):
        self.id_recurso_ref = entero(self.id_recurso_ref, "Recurso")
        self.codigo_inventario = texto(self.codigo_inventario, "Código de inventario", 40, True)
        self.numero_serie = texto(self.numero_serie, "Número de serie", 60)
        self.descripcion_bien = texto(self.descripcion_bien, "Descripción del bien", 255)
        self.ubicacion = texto(self.ubicacion, "Ubicación", 120)
        self.fecha_adquisicion = fecha(self.fecha_adquisicion, "Fecha de adquisición")
        if self.fecha_adquisicion > date.today():
            raise ValueError("La fecha de adquisición no puede ser futura.")
        try:
            self.estado = EstadoBienMaterial(self.estado)
        except (ValueError, TypeError):
            raise ValueError("Selecciona un estado de bien válido.") from None

    def esta_disponible(self):
        return self.estado == EstadoBienMaterial.DISPONIBLE

    def validar_disponible(self):
        if not self.esta_disponible():
            raise ValueError("El bien no está disponible.")

    def cambiar_estado(self, estado):
        try:
            nuevo = EstadoBienMaterial(estado)
        except (ValueError, TypeError):
            raise ValueError("El estado solicitado no es válido.") from None
        if nuevo not in TRANSICIONES_PERMITIDAS[self.estado]:
            raise ValueError(f"No se puede cambiar de {self.estado.value} a {nuevo.value}.")
        self.estado = nuevo


TRANSICIONES_PERMITIDAS = {
    EstadoBienMaterial.DISPONIBLE: ESTADOS_FUERA_SERVICIO | ESTADOS_GESTION_PRESTAMOS,
    EstadoBienMaterial.PRESTADO: ESTADOS_RECEPCION | {EstadoBienMaterial.PERDIDO},
    EstadoBienMaterial.RESERVADO: frozenset({EstadoBienMaterial.DISPONIBLE, EstadoBienMaterial.PRESTADO}),
    EstadoBienMaterial.DANADO: frozenset({
        EstadoBienMaterial.DISPONIBLE, EstadoBienMaterial.MANTENIMIENTO, EstadoBienMaterial.PERDIDO,
    }),
    EstadoBienMaterial.MANTENIMIENTO: frozenset({
        EstadoBienMaterial.DISPONIBLE, EstadoBienMaterial.DANADO, EstadoBienMaterial.PERDIDO,
    }),
    EstadoBienMaterial.PERDIDO: ESTADOS_RECEPCION,
}
