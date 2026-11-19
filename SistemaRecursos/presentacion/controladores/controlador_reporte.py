from flask import Blueprint, Response, g, render_template, request
from presentacion.seguridad import requiere_permiso
from dominio.gestion_control.catalogo_reportes import OPCIONES_FILTROS, REPORTES
from presentacion.formatos_reportes import (
    etiqueta_reporte,
    presentar_reporte,
    valor_reporte,
)
from presentacion.pdf_reportes import generar_pdf_historial, generar_pdf_reporte
from presentacion.graficos_reportes import preparar_graficos
from presentacion.dibujos_reportes import dibujos_graficos
from reportlab.graphics import renderSVG


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
        self.blueprint.add_url_rule(
            '/mi-historial',
            'consultar_historial_propio',
            self.consultar_historial_propio,
        )
        self.blueprint.add_url_rule(
            '/mi-historial/exportar.csv',
            'exportar_historial_propio_csv',
            self.exportar_historial_propio_csv,
        )
        self.blueprint.add_url_rule(
            '/mi-historial/exportar.pdf',
            'exportar_historial_propio_pdf',
            self.exportar_historial_propio_pdf,
        )

    @requiere_permiso('REPORTES_CONSULTAR')
    def consultar_reportes(self):
        resultado = self.servicio.consultar_reportes(request.args)
        resultado['reporte'] = presentar_reporte(resultado['filtro'].tipo)
        if not resultado['filtro'].tipo.startswith('historial_'):
            resultado['graficos'] = preparar_graficos(resultado['filtro'].tipo, resultado['filas'])
            if resultado['graficos']:
                resultado['graficos']['svg'] = [renderSVG.drawToString(d) for d in dibujos_graficos(resultado['graficos'])]
        return render_template(
            (
                'vista_historial.html'
                if resultado['filtro'].tipo.startswith('historial_')
                else 'vista_reporte.html'
            ),
            **resultado,
            reportes=REPORTES,
            opciones_filtros=OPCIONES_FILTROS,
            categorias=(
                self.recursos.consultar_categorias()
                if 'id_categoria' in resultado['reporte'].filtros
                else []
            ),
        )

    @requiere_permiso('PRESTAMOS_PROPIOS_CONSULTAR')
    def consultar_historial_propio(self):
        return render_template(
            'vista_historial.html',
            **self.servicio.consultar_historial_propio(g.usuario.dni),
        )

    @requiere_permiso('PRESTAMOS_PROPIOS_CONSULTAR')
    def exportar_historial_propio_csv(self):
        contenido, _ = self.servicio.exportar_historial_propio_csv(g.usuario.dni)
        return Response(
            contenido.encode('utf-8'),
            content_type='text/csv; charset=utf-8',
            headers={'Content-Disposition': 'attachment; filename="mi_historial.csv"'},
        )

    @requiere_permiso('PRESTAMOS_PROPIOS_CONSULTAR')
    def exportar_historial_propio_pdf(self):
        resultado = self.servicio.consultar_historial_propio(g.usuario.dni)
        return Response(
            generar_pdf_historial(resultado),
            content_type='application/pdf',
            headers={'Content-Disposition': 'attachment; filename="mi_historial.pdf"'},
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
        resultado = self.servicio.consultar_reportes(request.args)
        filtro = resultado['filtro']
        if filtro.tipo.startswith('historial_'):
            contenido = generar_pdf_historial(resultado)
        else:
            contenido = generar_pdf_reporte(filtro, resultado['filas'])
        return Response(
            contenido,
            content_type='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filtro.tipo}.pdf"'
            },
        )
