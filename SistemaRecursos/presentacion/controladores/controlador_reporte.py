from flask import Blueprint, Response, render_template, request
from presentacion.seguridad import requiere_permiso


class ControladorReporte:
    def __init__(self, servicio):
        self.servicio = servicio
        self.blueprint = Blueprint('reportes', __name__, url_prefix='/reportes')
        self.blueprint.add_url_rule('', 'listar', self.listar)
        self.blueprint.add_url_rule('/exportar.csv', 'exportar', self.exportar)

    @requiere_permiso('REPORTES_CONSULTAR')
    def listar(self):
        return render_template('vista_reporte.html', **self.servicio.consultar(request.args))

    @requiere_permiso('REPORTES_CONSULTAR')
    def exportar(self):
        contenido, tipo = self.servicio.exportar(request.args)
        return Response(
            contenido.encode('utf-8'),
            content_type='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename="{tipo}.csv"'},
        )
