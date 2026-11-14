from flask import Blueprint, Response, render_template, request
from presentacion.seguridad import requiere_permiso


class ControladorReporte:
    def __init__(self, servicio):
        self.servicio = servicio
        self.blueprint = Blueprint('reportes', __name__, url_prefix='/reportes')
        self.blueprint.add_url_rule('', 'consultar_reportes', self.consultar_reportes)
        self.blueprint.add_url_rule(
            '/exportar.csv', 'exportar_reportes_csv', self.exportar_reportes_csv
        )

    @requiere_permiso('REPORTES_CONSULTAR')
    def consultar_reportes(self):
        return render_template(
            'vista_reporte.html', **self.servicio.consultar_reportes(request.args)
        )

    @requiere_permiso('REPORTES_CONSULTAR')
    def exportar_reportes_csv(self):
        contenido, tipo = self.servicio.exportar_reportes_csv(request.args)
        return Response(
            contenido.encode('utf-8'),
            content_type='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename="{tipo}.csv"'},
        )
