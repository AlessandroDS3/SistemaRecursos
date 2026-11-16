from flask import Blueprint, Response, render_template, request
from presentacion.seguridad import requiere_permiso
from dominio.gestion_control.catalogo_reportes import ETIQUETAS_VALORES, OPCIONES_FILTROS, REPORTES


def etiqueta_reporte(valor):
    return ETIQUETAS_VALORES.get(valor, str(valor).replace('_', ' ').capitalize())


def valor_reporte(valor, formato='texto'):
    if valor is None or valor == '':
        return '—'
    if formato == 'porcentaje':
        return f'{float(valor):.1f} %'
    if formato == 'duracion':
        if 0 < valor < 1:
            return 'Menos de 1 min'
        minutos = max(0, int(valor))
        dias, minutos = divmod(minutos, 1440)
        horas, minutos = divmod(minutos, 60)
        partes = [
            f'{cantidad} {unidad}'
            for cantidad, unidad in ((dias, 'd'), (horas, 'h'), (minutos, 'min'))
            if cantidad
        ]
        return ' '.join(partes) or '0 min'
    if formato == 'numero':
        return str(int(valor))
    if formato == 'etiqueta':
        return etiqueta_reporte(valor)
    return valor


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

    @requiere_permiso('REPORTES_CONSULTAR')
    def consultar_reportes(self):
        resultado = self.servicio.consultar_reportes(request.args)
        return render_template(
            'vista_reporte.html',
            **resultado,
            reportes=REPORTES,
            opciones_filtros=OPCIONES_FILTROS,
            categorias=self.recursos.consultar_categorias(),
        )

    @requiere_permiso('REPORTES_CONSULTAR')
    def exportar_reportes_csv(self):
        contenido, tipo = self.servicio.exportar_reportes_csv(request.args)
        return Response(
            contenido.encode('utf-8'),
            content_type='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename="{tipo}.csv"'},
        )
