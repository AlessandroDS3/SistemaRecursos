from dataclasses import dataclass
from dominio.compartido.validacion import Conflicto, validar_entero, validar_texto
from dominio.gestion_recursos.bien_material import CondicionBien, EstadoBien


@dataclass(kw_only=True)
class Devolucion:
    id_detalle: int
    condicion: CondicionBien
    observacion: str = ''

    def __post_init__(self):
        self.id_detalle = validar_entero(self.id_detalle, 'Detalle')
        if self.condicion not in tuple(CondicionBien):
            raise ValueError('La recepción física debe indicar BUENO o DANADO.')
        self.condicion = CondicionBien(self.condicion)
        self.observacion = validar_texto(self.observacion, 'Observación', 255, self.condicion == 'DANADO')

    @property
    def estado_bien(self) -> EstadoBien:
        return EstadoBien.DISPONIBLE if self.condicion is CondicionBien.BUENO else EstadoBien.DANADO

    def validar_bien_pendiente_de_devolucion(self, detalle):
        if detalle['fecha_devolucion'] is not None or detalle.get('fecha_regularizacion'):
            raise Conflicto('El bien ya fue recibido.')
        if detalle['estado_bien'] not in (EstadoBien.PRESTADO, EstadoBien.PERDIDO):
            raise Conflicto('El inventario no corresponde a una entrega pendiente.')

    @staticmethod
    def validar_codigo_recibido(detalle, valor):
        codigo = validar_texto(valor, 'Código del bien recibido', 40, True)
        if codigo.casefold() != detalle['codigo_inventario'].casefold():
            raise Conflicto('El código del bien recibido no coincide. Verifica el ejemplar o registra una discrepancia.')
