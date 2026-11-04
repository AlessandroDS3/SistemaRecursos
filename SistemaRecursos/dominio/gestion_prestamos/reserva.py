from dominio.gestion_personas_usuarios.validacion_persona import validar_dni
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from dominio.gestion_prestamos.solicitud_prestamo import SolicitudPrestamo
from dominio.gestion_prestamos.validacion_prestamo import validar_persona, ConflictoPrestamoError
from dominio.gestion_recursos.validacion_recurso import entero, texto, instante_utc


class EstadoReserva(str, Enum):
    EN_ESPERA = "EN_ESPERA"
    LISTA_PARA_RETIRO = "LISTA_PARA_RETIRO"
    ATENDIDA = "ATENDIDA"
    CANCELADA = "CANCELADA"
    RECHAZADA = "RECHAZADA"
    EXPIRADA = "EXPIRADA"


class TipoSolicitud(str, Enum):
    PRESTAMO = "PRESTAMO"
    RESERVA = "RESERVA"


class AccionReserva(str, Enum):
    PREPARAR = "preparar"
    ENTREGAR = "entregar"
    CANCELAR = "cancelar"
    RECHAZAR = "rechazar"
    EXPIRAR = "expirar"

    @classmethod
    def desde_valor(cls, valor):
        try:
            return cls(valor)
        except (TypeError, ValueError):
            raise PermissionError("No tienes permiso para esta acción.") from None

    @property
    def requiere_motivo(self):
        return self in {self.RECHAZAR, self.EXPIRAR}

    @property
    def estado_destino(self):
        return ESTADOS_POR_ACCION[self]

    @property
    def observacion(self):
        return OBSERVACIONES_POR_ACCION[self]

    def validar_permiso(self, gestionar):
        if not gestionar and self != self.CANCELAR:
            raise PermissionError("No tienes permiso para esta acción.")


ESTADOS_POR_ACCION = {
    AccionReserva.PREPARAR: EstadoReserva.LISTA_PARA_RETIRO,
    AccionReserva.ENTREGAR: EstadoReserva.ATENDIDA,
    AccionReserva.CANCELAR: EstadoReserva.CANCELADA,
    AccionReserva.RECHAZAR: EstadoReserva.RECHAZADA,
    AccionReserva.EXPIRAR: EstadoReserva.EXPIRADA,
}
OBSERVACIONES_POR_ACCION = {
    AccionReserva.PREPARAR: "Bien listo para retiro",
    AccionReserva.ENTREGAR: "Entrega física confirmada",
    AccionReserva.CANCELAR: "Cancelada por el solicitante o personal",
    AccionReserva.RECHAZAR: "RECHAZADA",
    AccionReserva.EXPIRAR: "EXPIRADA",
}


TRANSICIONES_RESERVA = {
    EstadoReserva.EN_ESPERA: frozenset({
        EstadoReserva.LISTA_PARA_RETIRO, EstadoReserva.CANCELADA,
        EstadoReserva.RECHAZADA, EstadoReserva.EXPIRADA,
    }),
    EstadoReserva.LISTA_PARA_RETIRO: frozenset({
        EstadoReserva.ATENDIDA, EstadoReserva.CANCELADA,
        EstadoReserva.RECHAZADA, EstadoReserva.EXPIRADA,
    }),
}


def autorizar_resolucion(dni_solicitante, accion, dni_responsable, gestionar):
    accion.validar_permiso(gestionar)
    if not gestionar and dni_solicitante != dni_responsable:
        raise PermissionError("Solo puedes cancelar tus propias solicitudes o reservas.")


@dataclass(kw_only=True)
class Reserva:
    dni_persona: str
    id_recurso_ref: int
    fecha_requerida: datetime
    tipo_gestion: TipoSolicitud = TipoSolicitud.RESERVA
    observaciones: str = ""
    salida_solicitada: bool = False
    id_reserva: int | None = None
    id_bien_ref: int | None = None
    fecha_limite_vencimiento: datetime | None = None
    estado: EstadoReserva = EstadoReserva.EN_ESPERA

    def __post_init__(self):
        self.dni_persona = validar_dni(self.dni_persona)
        self.id_recurso_ref = entero(self.id_recurso_ref, "Recurso")
        self.fecha_requerida = instante_utc(self.fecha_requerida, "Fecha requerida")
        try:
            self.tipo_gestion = TipoSolicitud(self.tipo_gestion)
        except (TypeError, ValueError):
            raise ValueError("Selecciona solicitud de préstamo o reserva.") from None
        self.estado = EstadoReserva(self.estado)
        self.observaciones = texto(self.observaciones, "Observaciones", 220)
        if self.fecha_limite_vencimiento is not None:
            self.fecha_limite_vencimiento = instante_utc(self.fecha_limite_vencimiento, "Fecha límite")
        if self.id_bien_ref is not None:
            self.id_bien_ref = entero(self.id_bien_ref, "Bien reservado")

    def cambiar_estado(self, nuevo):
        nuevo = EstadoReserva(nuevo)
        if nuevo not in TRANSICIONES_RESERVA.get(self.estado, frozenset()):
            raise ValueError("La solicitud ya fue resuelta o su estado cambió. Recarga la página.")
        self.estado = nuevo
        return nuevo

    def resolver_reserva(self, accion, dni_responsable, gestionar, motivo="", acepta=False):
        autorizar_resolucion(self.dni_persona, accion, dni_responsable, gestionar)
        if accion == AccionReserva.ENTREGAR:
            if self.estado != EstadoReserva.LISTA_PARA_RETIRO:
                raise ConflictoPrestamoError("Prepara un bien antes de confirmar la entrega.")
            if not acepta:
                raise ValueError("Confirma la entrega física y la comunicación del plazo y permiso de salida.")
        if accion.requiere_motivo and not motivo.strip():
            raise ValueError("Indica el motivo de la resolución.")
        return self.cambiar_estado(accion.estado_destino)

    def validar_solicitante(self, persona, tiene_sancion):
        if not persona:
            raise LookupError("No se encontró al solicitante.")
        validar_persona(persona)
        if tiene_sancion:
            raise ConflictoPrestamoError("El solicitante tiene una sanción activa.")

    def validar_politica(self, politica):
        if politica is None:
            raise ValueError("Falta la política de préstamo para esta persona y recurso.")
        if self.salida_solicitada and not politica.permite_salida:
            raise ValueError("La política no permite sacar este recurso de la institución.")

    def validar_fecha_retiro(self, ahora):
        if self.fecha_requerida > ahora:
            raise ValueError("La fecha de retiro aún no llega. La solicitud permanece en espera.")

    def validar_turno(self, primera_solicitud):
        if primera_solicitud != self.id_reserva:
            raise ConflictoPrestamoError(
                "Atiende primero la solicitud anterior de este recurso que ya puede retirarse."
            )

    def preparar_solicitud_prestamo(self, dni_encargado):
        if self.id_bien_ref is None:
            raise ConflictoPrestamoError("Prepara un bien antes de confirmar la entrega.")
        observacion_uso = (
            "Salida externa autorizada. " if self.salida_solicitada
            else "Uso dentro de la institución. "
        )
        return SolicitudPrestamo(
            dni_persona=self.dni_persona,
            dni_encargado=dni_encargado,
            observaciones=observacion_uso + self.observaciones,
            salida_solicitada=self.salida_solicitada,
            ids_bienes=[self.id_bien_ref],
        )
