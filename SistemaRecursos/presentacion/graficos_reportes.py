"""Datos visuales calculados sobre las filas filtradas, sin consultas adicionales."""
from collections import Counter
from math import ceil

from presentacion.formatos_reportes import etiqueta_reporte


CONFIGURACION = {
    'prestamos': ('situacion', 'Situación de los bienes', 'bienes prestados'),
    'devoluciones': ('cumplimiento', 'Cumplimiento de devoluciones', 'devoluciones'),
    'atrasados': ('retraso_minutos', 'Tiempo de atraso', 'bienes atrasados'),
    'inventario': ('estado', 'Estado del inventario', 'bienes'),
    'reservas': ('estado', 'Estado de las solicitudes', 'solicitudes'),
    'sanciones': ('estado', 'Estado de las sanciones', 'sanciones'),
    'danos_perdidas': ('tipo_evento', 'Daños y pérdidas', 'eventos'),
    'personas': ('estado', 'Estado de las personas', 'personas'),
}
COLORES = ('#87002e', '#287b78', '#b77918', '#6554a4', '#3275a8', '#b64e40', '#77838b')


def _rango(minutos):
    if minutos < 60:
        return 'Menos de 1 hora'
    if minutos < 1440:
        return 'De 1 a menos de 24 horas'
    if minutos < 10080:
        return 'De 1 a menos de 7 días'
    return '7 días o más'


def _serie(conteos):
    total = sum(conteos.values())
    maximo = max(conteos.values(), default=0)
    acumulado = 0
    elementos, sectores = [], []
    for indice, (etiqueta, cantidad) in enumerate(conteos.items()):
        color = COLORES[indice % len(COLORES)]
        inicio = 360 * acumulado / total if total else 0
        acumulado += cantidad
        fin = 360 * acumulado / total if total else 0
        sectores.append(f'{color} {inicio:.6f}deg {fin:.6f}deg')
        elementos.append(dict(
            etiqueta=etiqueta, cantidad=cantidad, color=color,
            porcentaje=round(100 * cantidad / total, 1) if total else 0,
            ancho=round(100 * cantidad / maximo, 2) if maximo else 0,
        ))
    return dict(total=total, maximo=maximo, elementos=elementos, gradiente=', '.join(sectores))


def preparar_graficos(tipo, filas):
    if tipo not in CONFIGURACION:
        return None
    campo, titulo, unidad = CONFIGURACION[tipo]
    distribucion = Counter(
        _rango(fila[campo]) if tipo == 'atrasados' else etiqueta_reporte(fila[campo])
        for fila in filas
    )
    if tipo == 'atrasados':
        orden = [_rango(m) for m in (0, 60, 1440, 10080)]
        distribucion = {nombre: distribucion[nombre] for nombre in orden if distribucion[nombre]}
    else:
        distribucion = dict(sorted(distribucion.items()))
    campo_grupo = 'tipo_persona' if tipo == 'personas' else 'recurso'
    grupos = Counter(
        etiqueta_reporte(fila[campo_grupo]) if tipo == 'personas' else fila[campo_grupo]
        for fila in filas
    )
    ordenados = sorted(grupos.items(), key=lambda item: (-item[1], item[0]))
    # Conservar el total: los grupos fuera del top 6 se representan juntos.
    principales = ordenados[:6]
    if len(ordenados) > 6:
        principales.append(('Resto de recursos (agrupados)', sum(n for _, n in ordenados[6:])))
    resultado = dict(
        titulo=titulo, unidad=unidad, circular=_serie(distribucion),
        titulo_barras='Tipos de persona' if tipo == 'personas' else 'Registros por recurso',
        descripcion_barras=('Distribución por tipo de persona.' if tipo == 'personas' else
                            'Por nombre de recurso: los 6 primeros y el resto agrupado.'),
        barras=_serie(dict(principales)),
    )
    if tipo in ('atrasados', 'devoluciones') and filas:
        minutos = [max(0, int(fila['retraso_minutos'])) for fila in filas]
        paso = max(1, ceil((max(minutos) + 1) / 6))
        frecuencias = {f'{i * paso} a <{(i + 1) * paso} min': 0 for i in range(6)}
        etiquetas = list(frecuencias)
        for valor in minutos:
            frecuencias[etiquetas[min(valor // paso, 5)]] += 1
        resultado.update(
            titulo_barras='Distribución de retrasos',
            descripcion_barras='Frecuencia en 6 intervalos de igual amplitud, en minutos.',
            barras=_serie(frecuencias), histograma=True,
        )
    return resultado
