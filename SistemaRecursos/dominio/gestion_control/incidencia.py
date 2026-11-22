from enum import Enum


class TipoIncidencia(str, Enum):
    RETRASO = 'RETRASO'
    DANIO = 'DANIO'
    PERDIDA = 'PERDIDA'
    SALIDA_NO_AUTORIZADA = 'SALIDA_NO_AUTORIZADA'
    CUSTODIA = 'CUSTODIA'


def hay_retraso(detalle, ahora):
    return detalle['fecha_limite_devolucion'] < (detalle.get('fecha_devolucion') or ahora)
