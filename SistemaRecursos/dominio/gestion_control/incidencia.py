from enum import Enum


class TipoIncidencia(str, Enum):
    RETRASO = 'RETRASO'
    DANIO = 'DANIO'
    PERDIDA = 'PERDIDA'


def hay_retraso(detalle, ahora):
    return detalle['fecha_limite_devolucion'] < (detalle.get('fecha_devolucion') or ahora)
