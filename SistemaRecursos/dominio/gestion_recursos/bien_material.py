from dataclasses import dataclass, fields
from datetime import date, datetime
from secrets import choice

from dominio.compartido.validacion import LIMA, Conflicto, entero, texto, version

# Sin 0/O ni 1/I para que el identificador se pueda dictar y copiar sin confusiones.
ALFABETO_IDENTIFICADOR = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'


def generar_identificador_sistema(anio: int) -> str:
    """Identificador interno del sistema (AUT-01), distinto de la serie del fabricante."""
    return f'SR-{anio}-' + ''.join(choice(ALFABETO_IDENTIFICADOR) for _ in range(6))

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
        self.numero_serie = texto(self.numero_serie, 'Serie del fabricante', 60)
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
        if isinstance(self.fecha_adquisicion, datetime):
            self.fecha_adquisicion = self.fecha_adquisicion.date()
        if self.fecha_adquisicion and self.fecha_adquisicion > datetime.now(LIMA).date():
            raise ValueError('La fecha de adquisición no puede ser futura.')


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
