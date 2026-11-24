from datetime import datetime, timedelta, timezone

from dominio.compartido.validacion import LIMA


def registrar_filtros(app):
    @app.template_filter('fecha')
    def fecha(valor):
        if not valor:
            return '—'
        if isinstance(valor, datetime):
            valor = valor.replace(tzinfo=timezone.utc).astimezone(LIMA)
            return valor.strftime('%d/%m/%Y %H:%M')
        return str(valor)

    @app.template_filter('hora')
    def hora(valor):
        if not valor:
            return ''
        if isinstance(valor, timedelta):
            minutos = int(valor.total_seconds()) // 60
            return f'{minutos // 60:02d}:{minutos % 60:02d}'
        return str(valor)[:5]
