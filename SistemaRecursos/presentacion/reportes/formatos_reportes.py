"""Formatos y visibilidad del HTML; no alteran los datos ni las columnas del CSV."""

from dataclasses import dataclass, replace
from servicios.reportes.catalogo_reportes import CampoReporte, REPORTES


@dataclass(frozen=True)
class CampoVistaReporte(CampoReporte):
    formato: str = 'texto'
    en_tabla: bool = True


ETIQUETAS_VALORES = {'DANADO': 'Dañado', 'TARDIA': 'Tardía', 'PRESTAMO': 'Solicitud de préstamo'}
FORMATOS = {
    'id_prestamo': 'prestamo',
    'solicitante': 'persona',
    'id_reserva': 'reserva',
    'fecha_entrega': 'fecha',
    'fecha_limite_devolucion': 'fecha',
    'fecha_devolucion': 'fecha',
    'fecha_solicitud': 'fecha',
    'fecha_requerida': 'fecha',
    'fecha_limite_vencimiento': 'fecha',
    'fecha': 'fecha',
    'fecha_levantamiento': 'fecha',
    'fecha_fin': 'fecha',
    'fecha_regularizacion': 'fecha',
    'gravedad': 'estado',
    'tipo_regularizacion': 'etiqueta',
    'fecha_adquisicion': 'dia',
    'fecha_registro': 'fecha',
    'estado': 'estado',
    'situacion': 'estado',
    'cumplimiento': 'estado',
    'tipo_evento': 'estado',
    'estado_actual': 'estado',
    'condicion_devolucion': 'etiqueta',
    'tipo_gestion': 'etiqueta',
    'tipo_persona': 'etiqueta',
    'retraso_minutos': 'duracion',
    'id_sancion': 'numero',
    'id_historial_estado': 'numero',
}


def etiqueta_reporte(valor):
    return ETIQUETAS_VALORES.get(valor, str(valor).replace('_', ' ').capitalize())


def valor_reporte(valor, formato='texto'):
    if valor is None or valor == '':
        return '—'
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


def presentar_reporte(tipo):
    reporte = REPORTES[tipo]
    ocultos = {
        'dni_persona',
        'tipo_prestamo',
        'integrantes',
        'id_bien',
        'dni_registrador',
        'descripcion',
    }
    if tipo.startswith('historial_'):
        visibles = {'fecha', 'evento', 'referencia', 'codigo_inventario',
                    'solicitante', 'registrador', 'transicion', 'observacion'}
        ocultos = {c.nombre for c in reporte.columnas if c.nombre not in visibles}
    if tipo in ('prestamos', 'devoluciones', 'sanciones'):
        ocultos.update(('recurso', 'categoria'))
    if tipo == 'atrasados':
        ocultos.add('recurso')
    if tipo == 'sanciones':
        # El CSV conserva todos los datos; el detalle de sanción muestra fechas y aceptación.
        ocultos.update(('fecha_fin', 'fecha_regularizacion', 'tipo_regularizacion'))
    formatos = dict(
        FORMATOS,
        codigo_inventario='inventario' if tipo in ('inventario', 'danos_perdidas') else 'bien',
    )
    return replace(
        reporte,
        columnas=tuple(
            CampoVistaReporte(
                c.nombre, c.etiqueta, formatos.get(c.nombre, 'texto'), c.nombre not in ocultos
            )
            for c in reporte.columnas
        ),
    )
