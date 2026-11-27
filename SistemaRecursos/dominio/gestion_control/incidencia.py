from dominio.compartido.codigos import Codigo
from dominio.gestion_recursos.bien_material import CondicionBien


class TipoIncidencia(Codigo):
    RETRASO = 'RETRASO'
    DANIO = 'DANIO'
    PERDIDA = 'PERDIDA'
    SALIDA_NO_AUTORIZADA = 'SALIDA_NO_AUTORIZADA'
    CUSTODIA = 'CUSTODIA'


def hay_retraso(detalle, ahora):
    return detalle['fecha_limite_devolucion'] < (detalle.get('fecha_devolucion') or ahora)


def hay_danio_nuevo(condicion_entrega: str | None, condicion_devolucion: str | None) -> bool:
    return condicion_entrega == CondicionBien.BUENO and condicion_devolucion == CondicionBien.DANADO
