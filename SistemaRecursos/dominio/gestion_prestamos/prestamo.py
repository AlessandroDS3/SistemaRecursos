from enum import Enum
from dominio.gestion_personas_usuarios.validacion_persona import validar_dni
from dataclasses import dataclass, field
from datetime import datetime, timezone
from dominio.gestion_prestamos.tipo_prestamo import TipoPrestamo
from dominio.gestion_recursos.bien_material import EstadoBienMaterial, ESTADOS_RECEPCION
from dominio.gestion_recursos.validacion_recurso import entero, texto


class EstadoPrestamo(str, Enum):
    ACTIVO = "ACTIVO"
    VENCIDO = "VENCIDO"
    DEVUELTO = "DEVUELTO"
    PARCIALMENTE_DEVUELTO = "PARCIALMENTE_DEVUELTO"


@dataclass(kw_only=True)
class Prestamo:
    dni_persona: str
    dni_encargado: str
    tipo_prestamo: TipoPrestamo = TipoPrestamo.INDIVIDUAL
    observaciones: str = ""
    id_prestamo: int | None = None
    fecha_solicitud: datetime | None = None
    fecha_entrega: datetime | None = None
    estado: EstadoPrestamo = EstadoPrestamo.ACTIVO
    detalles: list = field(default_factory=list)
    participantes: list = field(default_factory=list)
    salida_solicitada: bool = False

    def __post_init__(self):
        self.dni_persona = validar_dni(self.dni_persona)
        self.dni_encargado = validar_dni(self.dni_encargado)
        try:
            self.tipo_prestamo = TipoPrestamo(self.tipo_prestamo)
            self.estado = EstadoPrestamo(self.estado)
        except (ValueError, TypeError):
            raise ValueError("El tipo o estado del préstamo no es válido.") from None
        self.observaciones = texto(self.observaciones, "Observaciones", 255)

    def agregar_detalle(self, detalle):
        for detalle_registrado in self.detalles:
            if detalle_registrado.id_bien_ref == detalle.id_bien_ref:
                raise ValueError("No se puede incluir el mismo bien dos veces.")
        self.detalles.append(detalle)

    def validar(self):
        if not self.detalles:
            raise ValueError("Selecciona al menos un bien para el préstamo.")
        ids_bienes = []
        for detalle in self.detalles:
            ids_bienes.append(detalle.id_bien_ref)
        if len(set(ids_bienes)) != len(ids_bienes):
            raise ValueError("No se puede incluir el mismo bien dos veces.")
        dnis_participantes = []
        for participante in self.participantes:
            dnis_participantes.append(participante.dni_persona)
        if len(set(dnis_participantes)) != len(dnis_participantes):
            raise ValueError("Un participante no puede repetirse.")
        if self.tipo_prestamo == TipoPrestamo.INDIVIDUAL and self.participantes:
            raise ValueError("Los préstamos individuales no tienen participantes adicionales.")
        if self.tipo_prestamo == TipoPrestamo.GRUPAL:
            responsables = []
            for participante in self.participantes:
                if participante.responsable:
                    responsables.append(participante)
            if (
                len(dnis_participantes) < 2
                or len(responsables) != 1
                or responsables[0].dni_persona != self.dni_persona
            ):
                raise ValueError(
                    "El préstamo grupal necesita al solicitante como responsable y al menos otro participante."
                )

    def estado_actual(self, ahora=None):
        ahora = ahora or datetime.now(timezone.utc).replace(tzinfo=None)
        pendientes = []
        for detalle in self.detalles:
            if detalle.pendiente():
                pendientes.append(detalle)
        if not pendientes:
            return EstadoPrestamo.DEVUELTO
        for detalle in pendientes:
            if detalle.fecha_limite_devolucion < ahora:
                return EstadoPrestamo.VENCIDO
        if len(pendientes) < len(self.detalles):
            return EstadoPrestamo.PARCIALMENTE_DEVUELTO
        return EstadoPrestamo.ACTIVO

    def marcar_vencido(self, ahora=None):
        self.estado = self.estado_actual(ahora)
        return self.estado

    def registrar_devolucion(self, id_detalle, estado, ahora=None):
        detalle = None
        for detalle_prestamo in self.detalles:
            if detalle_prestamo.id_detalle == id_detalle:
                detalle = detalle_prestamo
                break
        if not detalle or not detalle.pendiente():
            raise ValueError("El bien no pertenece al préstamo o ya fue devuelto.")
        if estado not in ESTADOS_RECEPCION:
            raise ValueError("Selecciona la condición de recepción del bien.")
        detalle.estado_devolucion = EstadoBienMaterial(estado)
        self.estado = self.estado_actual(ahora)
