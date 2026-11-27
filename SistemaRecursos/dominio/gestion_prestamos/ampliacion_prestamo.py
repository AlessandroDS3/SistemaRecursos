from dataclasses import dataclass
from datetime import datetime

from dominio.compartido.validacion import Conflicto, validar_entero, normalizar_fecha_hora_utc, validar_texto
from dominio.gestion_control.politica_prestamo import HorarioAtencion, PoliticaPrestamo, UnidadPlazo
from dominio.gestion_personas_usuarios.persona import PersonaParaPrestamo
from dominio.gestion_prestamos.prestamo import EstadoPrestamo

EVENTO_AMPLIACION_PLAZO = 'AMPLIACION_PLAZO'


@dataclass(frozen=True)
class PrestamoParaAmpliar:
    id_prestamo: int
    dni_persona: str
    estado: EstadoPrestamo


@dataclass(frozen=True)
class DetalleParaAmpliar:
    id_recurso: int
    fecha_limite_devolucion: datetime
    prestado_pendiente: bool
    ampliado: bool


@dataclass(init=False)
class AmpliacionPrestamo:
    cantidad: int
    unidad: UnidadPlazo
    fecha_anterior: datetime
    motivo: str

    def __init__(self, *, cantidad: int | str | None, unidad: str | None,
                 fecha_anterior: datetime | str | None, motivo: str = '') -> None:
        self.cantidad = validar_entero(cantidad, 'Tiempo adicional', maximo=87600)
        if unidad not in tuple(UnidadPlazo):
            raise ValueError('Selecciona horas o días.')
        self.unidad = UnidadPlazo(unidad)
        self.fecha_anterior = normalizar_fecha_hora_utc(fecha_anterior)
        self.motivo = validar_texto(motivo, 'Motivo', 120)

    def calcular_nuevo_plazo_de_devolucion(self, detalle: DetalleParaAmpliar, ahora: datetime, politica: PoliticaPrestamo,
                 horario: HorarioAtencion | None) -> datetime:
        actual = detalle.fecha_limite_devolucion
        if actual != self.fecha_anterior:
            raise Conflicto('El plazo cambió. Recarga antes de volver a ampliar.')
        if actual <= ahora or not detalle.prestado_pendiente:
            raise Conflicto(
                'Solo se amplían bienes prestados, no vencidos y pendientes de devolución.'
            )
        if detalle.ampliado:
            raise Conflicto('Este bien ya recibió su única ampliación en este préstamo.')
        extra = self.unidad.duracion(self.cantidad)
        if extra > politica.duracion:
            raise ValueError('La ampliación no puede superar otro plazo de la política.')
        try:
            nueva = actual + extra
        except OverflowError:
            raise ValueError('La ampliación produce una fecha fuera de rango.') from None
        if politica.unidad_plazo is UnidadPlazo.HORAS and (horario is None or nueva > horario.obtener_cierre_si_hay_atencion(actual)):
            raise ValueError('La ampliación debe respetar el cierre de atención.')
        return horario.siguiente_dia_de_atencion(nueva) if horario is not None else nueva


@dataclass(frozen=True, kw_only=True)
class DatosParaValidarAmpliacion:
    prestamo: PrestamoParaAmpliar | None = None
    detalle: DetalleParaAmpliar | None = None
    politica: PoliticaPrestamo | None = None
    horario: HorarioAtencion | None = None


@dataclass(frozen=True, kw_only=True)
class RestriccionesAmpliacion:
    personas: list[PersonaParaPrestamo]
    sancion: bool
    reservas_sin_bien: bool
