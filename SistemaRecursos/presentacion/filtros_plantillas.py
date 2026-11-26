from datetime import datetime, timedelta, timezone

from dominio.compartido.validacion import LIMA
from dominio.gestion_control.politica_prestamo import DIAS_LABORABLES, NOMBRES_DIAS, dias_habilitados


def registrar_filtros_de_plantillas(app):
    app.add_template_filter(dias_habilitados, 'dias_habilitados')
    app.jinja_env.globals['dias_laborables'] = DIAS_LABORABLES

    @app.template_filter('dias_atencion_texto')
    def dias_atencion_texto(mascara):
        if mascara == DIAS_LABORABLES:
            return 'lunes a viernes'
        return ', '.join(NOMBRES_DIAS[dia].lower() for dia in dias_habilitados(mascara))

    @app.template_filter('fecha')
    def formatear_fecha_en_lima(valor):
        if not valor:
            return '—'
        if isinstance(valor, datetime):
            valor = valor.replace(tzinfo=timezone.utc).astimezone(LIMA)
            return valor.strftime('%d/%m/%Y %H:%M')
        return str(valor)

    @app.template_filter('hora')
    def formatear_hora_de_atencion(valor):
        if not valor and not isinstance(valor, timedelta):
            return ''
        if isinstance(valor, timedelta):
            minutos = int(valor.total_seconds()) // 60
            return f'{minutos // 60:02d}:{minutos % 60:02d}'
        return str(valor)[:5]
