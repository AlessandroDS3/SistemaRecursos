"""Reglas del registro de mantenimiento de bienes (MAN-01)."""

from dataclasses import dataclass
from datetime import date, datetime

from dominio.compartido.validacion import LIMA, Conflicto, validar_texto

TIPOS_MANTENIMIENTO = ('PREVENTIVO', 'CORRECTIVO')
RESULTADOS_MANTENIMIENTO = ('DISPONIBLE', 'DANADO')
# Estados desde los que un bien puede entrar a mantenimiento. MANTENIMIENTO cubre bienes
# marcados así antes de existir el registro: se abre el registro sin cambiar su estado.
ESTADOS_APERTURA = ('DISPONIBLE', 'DANADO', 'MANTENIMIENTO')


@dataclass(kw_only=True)
class AperturaMantenimiento:
    tipo: str
    motivo: str
    fecha_fin_estimada: date | str | None = None

    def __post_init__(self):
        if self.tipo not in TIPOS_MANTENIMIENTO:
            raise ValueError('Selecciona si el mantenimiento es preventivo o correctivo.')
        self.motivo = validar_texto(self.motivo, 'Motivo del mantenimiento', 255, True)
        if self.fecha_fin_estimada in ('', None):
            self.fecha_fin_estimada = None
            return
        if isinstance(self.fecha_fin_estimada, str):
            try:
                self.fecha_fin_estimada = date.fromisoformat(self.fecha_fin_estimada)
            except ValueError:
                raise ValueError('La fecha estimada de fin no es válida.') from None
        if self.fecha_fin_estimada < datetime.now(LIMA).date():
            raise ValueError('La fecha estimada de fin no puede ser anterior a hoy.')


@dataclass(kw_only=True)
class CierreMantenimiento:
    resultado: str
    observacion: str

    def __post_init__(self):
        if self.resultado not in RESULTADOS_MANTENIMIENTO:
            raise ValueError('Indica si el bien queda disponible o sigue dañado.')
        self.observacion = validar_texto(self.observacion, 'Observación de cierre', 255, True)


def validar_apertura_mantenimiento(estado_bien: str, abierto, prestamo_pendiente) -> None:
    if abierto:
        raise Conflicto('El bien ya tiene un mantenimiento abierto.')
    if prestamo_pendiente:
        raise Conflicto('El bien tiene una entrega pendiente; recíbelo antes del mantenimiento.')
    if estado_bien not in ESTADOS_APERTURA:
        raise Conflicto('Solo un bien disponible o dañado puede pasar a mantenimiento.')
