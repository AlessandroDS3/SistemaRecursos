"""Regreso a listados con filtros, limitado a rutas internas conocidas."""

from urllib.parse import parse_qsl, urlsplit

from flask import request, url_for


def regreso_prestamos():
    listado = url_for('prestamos.consultar_prestamos')
    origen = request.form if request.method == 'POST' else request.args
    try:
        destino = urlsplit(origen.get('volver', ''))
        if destino.scheme or destino.netloc or destino.path != listado:
            return listado
        filtros = {
            clave: valor
            for clave, valor in parse_qsl(destino.query, max_num_fields=20)
            if clave in ('q', 'estado', 'pagina') and len(valor) <= 120
        }
    except ValueError:
        return listado
    return url_for('prestamos.consultar_prestamos', **filtros)


def detalle_prestamo(identificador):
    volver = regreso_prestamos()
    parametros = {'volver': volver} if volver != url_for('prestamos.consultar_prestamos') else {}
    return url_for('prestamos.consultar_prestamo', identificador=identificador, **parametros)
