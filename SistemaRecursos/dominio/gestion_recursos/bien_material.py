from dataclasses import dataclass
from datetime import date
from typing import Protocol
from dominio.compartido.contratos import IRepositorioTransaccional
from dominio.compartido.validacion import Conflicto, entero, texto

ESTADOS_BIEN = ('DISPONIBLE', 'PRESTADO', 'RESERVADO', 'DANADO', 'MANTENIMIENTO', 'PERDIDO')
ESTADOS_MANUALES = ('DISPONIBLE', 'DANADO', 'MANTENIMIENTO', 'PERDIDO')


@dataclass(kw_only=True)
class BienMaterial:
    id_recurso: int
    codigo_inventario: str
    numero_serie: str = ''
    fecha_adquisicion: date | None = None
    ubicacion: str = ''
    descripcion_bien: str | None = None
    id_bien: int | None = None

    def __post_init__(self):
        self.id_recurso = entero(self.id_recurso, 'Recurso')
        self.codigo_inventario = texto(self.codigo_inventario, 'Código de inventario', 40, True)
        self.numero_serie = texto(self.numero_serie, 'Número de serie', 60)
        self.ubicacion = texto(self.ubicacion, 'Ubicación', 120)
        self.descripcion_bien = texto(self.descripcion_bien, 'Descripción', 255) or None
        if self.fecha_adquisicion in ('', None):
            self.fecha_adquisicion = None
        elif not isinstance(self.fecha_adquisicion, date):
            try:
                self.fecha_adquisicion = date.fromisoformat(self.fecha_adquisicion)
            except (ValueError, TypeError):
                raise ValueError('La fecha de adquisición no es válida.') from None


def validar_cambio_estado(actual, nuevo, esperado):
    if actual != esperado:
        raise Conflicto('El estado cambió. Recarga el bien.')
    if actual in ('PRESTADO', 'RESERVADO') or nuevo not in ESTADOS_MANUALES:
        raise Conflicto('Los estados de préstamo y reserva se cambian desde su operación.')
    if actual == nuevo:
        raise ValueError('Selecciona un estado diferente.')


class IRepositorioBienMaterial(IRepositorioTransaccional, Protocol):
    def consultar(self, identificador: int, bloquear=False) -> dict | None: ...
    def listar(self, filtros: dict) -> list[dict]: ...
    def guardar(self, bien: BienMaterial): ...
    def cambiar_estado(
        self, identificador: int, anterior: str, nuevo: str, motivo: str, actor: str
    ): ...
    def prestamo_pendiente(self, identificador: int) -> dict | None: ...
    def eliminar(self, identificador: int): ...
