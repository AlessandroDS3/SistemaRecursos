"""Formatos y visibilidad del HTML; no alteran los datos ni las columnas del CSV."""

from dataclasses import dataclass, replace
from dominio.gestion_control.catalogo_reportes import CampoReporte, REPORTES


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
    'fecha_adquisicion': 'dia',
    'estado': 'estado',
    'situacion': 'estado',
    'cumplimiento': 'estado',
    'tipo_evento': 'estado',
    'estado_actual': 'estado',
    'condicion_devolucion': 'etiqueta',
    'tipo_gestion': 'etiqueta',
    'retraso_minutos': 'duracion',
    'id_sancion': 'numero',
    'id_historial_estado': 'numero',
    'prestamos': 'numero',
    'bienes_prestados': 'numero',
    'solicitantes': 'numero',
}
FORMATOS_INDICADORES = {
    'porcentaje_puntual': 'porcentaje',
    'retraso_promedio': 'duracion',
    'retraso_maximo': 'duracion',
}


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
    if tipo in ('prestamos', 'devoluciones', 'sanciones'):
        ocultos.update(('recurso', 'categoria'))
    if tipo == 'atrasados':
        ocultos.add('recurso')
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
        indicadores=tuple(
            CampoVistaReporte(c.nombre, c.etiqueta, FORMATOS_INDICADORES.get(c.nombre, 'texto'))
            for c in reporte.indicadores
        ),
    )
