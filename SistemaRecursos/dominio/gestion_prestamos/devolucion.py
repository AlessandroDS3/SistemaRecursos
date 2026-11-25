from dataclasses import dataclass
from dominio.compartido.validacion import Conflicto, entero, texto


@dataclass(kw_only=True)
class Devolucion:
    id_detalle: int
    condicion: str
    observacion: str = ''

    def __post_init__(self):
        self.id_detalle = entero(self.id_detalle, 'Detalle')
        if self.condicion not in ('BUENO', 'DANADO'):
            raise ValueError('La recepción física debe indicar BUENO o DANADO.')
        self.observacion = texto(self.observacion, 'Observación', 255, self.condicion == 'DANADO')

    @property
    def estado_bien(self):
        return 'DISPONIBLE' if self.condicion == 'BUENO' else 'DANADO'

    def validar(self, detalle):
        if detalle['fecha_devolucion'] is not None or detalle.get('fecha_regularizacion'):
            raise Conflicto('El bien ya fue recibido.')
        if detalle['estado_bien'] not in ('PRESTADO', 'PERDIDO'):
            raise Conflicto('El inventario no corresponde a una entrega pendiente.')

    @staticmethod
    def validar_codigo_recibido(detalle, valor):
        codigo = texto(valor, 'Código del bien recibido', 40, True)
        if codigo.casefold() != detalle['codigo_inventario'].casefold():
            raise Conflicto('El código del bien recibido no coincide. Verifica el ejemplar o registra una discrepancia.')
