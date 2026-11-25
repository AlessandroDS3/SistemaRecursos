"""Gráficos vectoriales compartidos por HTML y PDF (sin servicios externos)."""
from math import sin, cos, pi
from reportlab.graphics.shapes import Drawing, Polygon, Rect, Line, String
from reportlab.lib.colors import HexColor, Color


def circular_3d(serie):
    dibujo = Drawing(350, 220)
    if not serie['total']:
        return dibujo
    sectores, etiquetas = [], []
    angulo = pi / 2
    for indice, item in enumerate(serie['elementos']):
        amplitud = 2 * pi * item['cantidad'] / serie['total']
        pasos = max(2, ceil_segmentos(amplitud))
        puntos = [175, 120]
        for i in range(pasos + 1):
            a = angulo - amplitud * i / pasos
            puntos.extend((175 + 140 * cos(a), 120 + 76 * sin(a)))
        sectores.append((puntos, item['color']))
        if item['porcentaje'] >= 5:
            medio = angulo - amplitud / 2
            etiquetas.append((175 + 93 * cos(medio), 120 + 50 * sin(medio), str(indice + 1)))
        angulo -= amplitud
    # Capas inferiores simulan espesor; la cara superior mantiene las proporciones.
    for desplazamiento in range(16, 0, -2):
        for puntos, color in sectores:
            tono = HexColor(color)
            sombra = Color(tono.red * .65, tono.green * .65, tono.blue * .65)
            inferiores = [v - desplazamiento if i % 2 else v for i, v in enumerate(puntos)]
            dibujo.add(Polygon(inferiores, fillColor=sombra, strokeColor=None))
    for puntos, color in sectores:
        dibujo.add(Polygon(puntos, fillColor=HexColor(color), strokeColor=HexColor('#ffffff'), strokeWidth=.6))
    for x, y, etiqueta in etiquetas:
        dibujo.add(String(x, y, etiqueta, textAnchor='middle', fontName='Helvetica-Bold', fontSize=15, fillColor=HexColor('#ffffff')))
    return dibujo


def ceil_segmentos(amplitud):
    return int(amplitud * 24) + 1


def columnas(serie, histograma=False):
    dibujo = Drawing(350, 220)
    maximo = serie['maximo'] or 1
    techo = maximo
    for i in range(5):
        y = 35 + i * 40
        dibujo.add(Line(35, y, 340, y, strokeColor=HexColor('#e9e9e7'), strokeWidth=.6))
        dibujo.add(String(29, y - 3, f'{techo * i / 4:g}', textAnchor='end', fontSize=10, fillColor=HexColor('#73726e')))
    cantidad = len(serie['elementos'])
    if not cantidad:
        return dibujo
    paso = 300 / cantidad
    ancho = paso if histograma else paso * .65
    for i, item in enumerate(serie['elementos']):
        x = 38 + i * paso + (paso - ancho) / 2
        alto = 160 * item['cantidad'] / maximo
        dibujo.add(Rect(x, 35, ancho, alto, fillColor=HexColor('#111113'), strokeColor=HexColor('#ffffff'), strokeWidth=.6))
        dibujo.add(String(x + ancho / 2, 40 + alto, str(item['cantidad']), textAnchor='middle', fontName='Helvetica-Bold', fontSize=12))
        dibujo.add(String(x + ancho / 2, 20, str(i + 1), textAnchor='middle', fontSize=11))
    return dibujo


def dibujos_graficos(graficos):
    return circular_3d(graficos['circular']), columnas(graficos['barras'], graficos.get('histograma', False))
