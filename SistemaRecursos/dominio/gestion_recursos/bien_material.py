from dataclasses import dataclass, fields
from datetime import date
from typing import Protocol
from dominio.compartido.contratos import IRepositorioTransaccional
from dominio.compartido.validacion import Conflicto, entero, texto, version

ESTADOS_BIEN = ('DISPONIBLE', 'PRESTADO', 'RESERVADO', 'DANADO', 'MANTENIMIENTO', 'PERDIDO')
ESTADOS_MANUALES = ('DISPONIBLE', 'DANADO', 'MANTENIMIENTO', 'PERDIDO')


@dataclass(kw_only=True)
class BienMaterial:
    id_recurso: int
    codigo_inventario: str
    numero_serie: str = ''
    fecha_adquisicion: date | str | None = None
    ubicacion: str = ''
    descripcion_bien: str | None = None
    id_bien: int | None = None

    @classmethod
    def desde_datos(
        cls, datos: dict, *, id_recurso: int, id_bien: int | None = None
    ) -> 'BienMaterial':
        valores = {
            campo.name: datos[campo.name]
            for campo in fields(cls)
            if campo.name in datos and campo.name not in ('id_recurso', 'id_bien')
        }
        valores.setdefault('codigo_inventario', None)
        return cls(**valores, id_recurso=id_recurso, id_bien=id_bien)

    def __post_init__(self):
        self.id_recurso = entero(self.id_recurso, 'Recurso')
        self.codigo_inventario = texto(self.codigo_inventario, 'Código de inventario', 40, True)
        self.numero_serie = texto(self.numero_serie, 'Número de serie', 60)
        self.ubicacion = texto(self.ubicacion, 'Ubicación', 120)
        self.descripcion_bien = texto(self.descripcion_bien, 'Descripción', 255) or None
        if self.fecha_adquisicion in ('', None):
            self.fecha_adquisicion = None
        elif isinstance(self.fecha_adquisicion, str):
            try:
                self.fecha_adquisicion = date.fromisoformat(self.fecha_adquisicion)
            except (ValueError, TypeError):
                raise ValueError('La fecha de adquisición no es válida.') from None
        elif not isinstance(self.fecha_adquisicion, date):
            raise ValueError('La fecha de adquisición no es válida.')


def version_bien_material(datos: dict) -> str:
    """La edición descriptiva no depende del estado ni de los nombres de otras tablas."""
    return version({campo.name: datos[campo.name] for campo in fields(BienMaterial)})


def validar_filtros_inventario(filtros) -> dict:
    estado = filtros.get('estado', '')
    if estado and estado not in ESTADOS_BIEN:
        raise ValueError('Estado de bien inválido.')
    resultado = dict(q=texto(filtros.get('q'), 'Búsqueda', 120), estado=estado)
    for campo in ('id_recurso', 'id_categoria'):
        valor = filtros.get(campo)
        resultado[campo] = entero(valor) if valor not in (None, '') else None
    resultado['solo_disponibles'] = filtros.get('solo_disponibles') == '1'
    return resultado


def validar_cambio_estado(actual, nuevo, esperado) -> None:
    if actual != esperado:
        raise Conflicto('El estado cambió. Recarga el bien.')
    if actual in ('PRESTADO', 'RESERVADO') or nuevo not in ESTADOS_MANUALES:
        raise Conflicto('Los estados de préstamo y reserva se cambian desde su operación.')
    if actual == nuevo:
        raise ValueError('Selecciona un estado diferente.')


class IRepositorioBienMaterial(IRepositorioTransaccional, Protocol):
    def consultar_bien_material(self, identificador: int, bloquear=False) -> dict | None: ...
    def consultar_bienes_materiales(self, filtros: dict) -> list[dict]: ...
    def guardar_bien_material(self, bien: BienMaterial) -> int: ...
    def cambiar_estado_bien_material(
        self, identificador: int, anterior: str, nuevo: str, motivo: str, actor: str
    ) -> None: ...
    def consultar_prestamo_pendiente(self, identificador: int, bloquear=True) -> dict | None: ...
    def consultar_relaciones_bien_material(self, identificador: int, bloquear=True) -> dict: ...
    def eliminar_bien_material(self, identificador: int) -> None: ...
