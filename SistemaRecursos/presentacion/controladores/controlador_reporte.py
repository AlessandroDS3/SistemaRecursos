from dominio.gestion_personas_usuarios.personas import TipoPersona
from dominio.gestion_prestamos.prestamos import EstadoPrestamo, TipoPrestamo
from flask import Blueprint, Response, render_template, request, url_for
from presentacion.seguridad import requiere_permiso
from servicios.servicio_reporte import ServicioAplicacionReporte


class ControladorReporte:
    def __init__(self, servicio: ServicioAplicacionReporte):
        self.servicio = servicio
        self.blueprint = Blueprint('reportes', __name__, url_prefix='/reportes')
        self.blueprint.add_url_rule('', 'consultar_prestamos', self.consultar_prestamos, methods=['GET'])
        self.blueprint.add_url_rule('/prestamos.csv', 'exportar_prestamos', self.exportar_prestamos, methods=['GET'])

    def _mostrar(self, resultado=None, error=None):
        filtros = {campo: request.args.get(campo, '')
                   for campo in ('desde', 'hasta', 'estado', 'tipo_persona', 'modalidad', 'q')}
        return render_template('vista_reporte.html', resultado=resultado, error=error,
            filtros=filtros, estados=EstadoPrestamo, tipos_persona=TipoPersona, modalidades=TipoPrestamo,
            url_pagina=lambda pagina: url_for('reportes.consultar_prestamos', pagina=pagina, **filtros),
            url_csv=url_for('reportes.exportar_prestamos', **filtros))

    @requiere_permiso('REPORTES_CONSULTAR')
    def consultar_prestamos(self):
        try:
            resultado = self.servicio.consultar_prestamos(request.args)
        except ValueError as error:
            return self._mostrar(error=str(error)), 400
        return self._mostrar(resultado)

    @requiere_permiso('REPORTES_CONSULTAR')
    def exportar_prestamos(self):
        try:
            contenido = self.servicio.exportar_prestamos(request.args)
        except ValueError as error:
            return self._mostrar(error=str(error)), 400
        return Response(contenido, content_type='text/csv; charset=utf-8', headers={
            'Content-Disposition': 'attachment; filename="prestamos_devoluciones.csv"'})
