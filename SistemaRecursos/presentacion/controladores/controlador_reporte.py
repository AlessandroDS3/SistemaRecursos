from flask import Blueprint, Response, render_template, request
from presentacion.seguridad import requiere_permiso
from dominio.gestion_control.catalogo_reportes import OPCIONES_FILTROS, REPORTES
from presentacion.formatos_reportes import etiqueta_reporte, presentar_reporte, valor_reporte
from presentacion.pdf_reportes import generar_pdf_reporte


class ControladorReporte:
    def __init__(self, servicio, recursos):
        self.servicio, self.recursos = servicio, recursos
        self.blueprint = Blueprint('reportes', __name__, url_prefix='/reportes')
        self.blueprint.add_app_template_filter(etiqueta_reporte, 'etiqueta_reporte')
        self.blueprint.add_app_template_filter(valor_reporte, 'valor_reporte')
        self.blueprint.add_url_rule('', 'consultar_reportes', self.consultar_reportes)
        self.blueprint.add_url_rule(
            '/exportar.csv', 'exportar_reportes_csv', self.exportar_reportes_csv
        )
        self.blueprint.add_url_rule(
            '/exportar.pdf', 'exportar_reportes_pdf', self.exportar_reportes_pdf
        )

    @requiere_permiso('REPORTES_CONSULTAR')
    def consultar_reportes(self):
        resultado = self.servicio.consultar_reportes(request.args)
        resultado['reporte'] = presentar_reporte(resultado['filtro'].tipo)
        return render_template(
            'vista_reporte.html',
            **resultado,
            reportes=REPORTES,
            opciones_filtros=OPCIONES_FILTROS,
            categorias=(
                self.recursos.consultar_categorias()
                if 'id_categoria' in resultado['reporte'].filtros
                else []
            ),
        )

    @requiere_permiso('REPORTES_CONSULTAR')
    def exportar_reportes_csv(self):
        contenido, tipo = self.servicio.exportar_reportes_csv(request.args)
        return Response(
            contenido.encode('utf-8'),
            content_type='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename="{tipo}.csv"'},
        )

    @requiere_permiso('REPORTES_CONSULTAR')
    def exportar_reportes_pdf(self):
        filtro, filas = self.servicio.consultar_exportacion_reporte(request.args)
        return Response(
            generar_pdf_reporte(filtro, filas),
            content_type='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="{filtro.tipo}.pdf"'},
        )
