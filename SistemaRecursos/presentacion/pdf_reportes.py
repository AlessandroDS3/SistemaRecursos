"""Exportación en PDF de reportes e historiales."""

from datetime import date, datetime, timezone
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    CondPageBreak, LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle,
)

from dominio.compartido.validacion import LIMA
from presentacion.formatos_reportes import (
    CampoVistaReporte, etiqueta_reporte, presentar_reporte, valor_reporte,
)


CUERPO = ParagraphStyle(
    'CeldaReporte', fontName='Helvetica', fontSize=8, leading=10.5,
    alignment=TA_LEFT, splitLongWords=True,
)
ENCABEZADO = ParagraphStyle('EncabezadoReporte', parent=CUERPO, fontName='Helvetica-Bold')
TITULO = ParagraphStyle(
    'TituloReporte', fontName='Helvetica-Bold', fontSize=17, leading=21,
)
TEXTO = ParagraphStyle('TextoReporte', parent=CUERPO, fontSize=10, leading=14)
SECCION = ParagraphStyle(
    'SeccionReporte', parent=TEXTO, fontName='Helvetica-Bold', fontSize=13,
    leading=17, spaceBefore=14, spaceAfter=6, keepWithNext=True,
    textColor=colors.HexColor('#620021'),
)
SUBTITULO = ParagraphStyle(
    'SubtituloReporte', parent=TEXTO, fontName='Helvetica-Bold', spaceBefore=9,
    spaceAfter=4, keepWithNext=True,
)
TITULO_CRONOLOGIA = ParagraphStyle(
    'TituloCronologia', parent=SECCION, keepWithNext=False,
)


def _texto_pdf(valor):
    return escape(str(valor)).replace('\r\n', '\n').replace('\n', '<br/>')


def _fecha_lima(valor):
    if valor is None:
        return '-'
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(LIMA).strftime('%d/%m/%Y %H:%M')


def _celda_pdf(fila, columna):
    valor = fila.get(columna.nombre)
    if valor is None or valor == '':
        return '-'
    if isinstance(valor, datetime):
        return _fecha_lima(valor).replace(' ', '<br/>')
    if isinstance(valor, date):
        return valor.strftime('%d/%m/%Y')
    if columna.formato == 'persona':
        partes = [_texto_pdf(valor), 'DNI: ' + _texto_pdf(fila['dni_persona'])]
        if fila.get('integrantes'):
            partes.append('Integrantes: ' + _texto_pdf(fila['integrantes']))
        return '<br/>'.join(partes)
    if columna.formato == 'bien':
        return _texto_pdf(valor) + '<br/>' + _texto_pdf(fila['recurso'])
    if columna.formato in ('prestamo', 'reserva'):
        texto = '#' + _texto_pdf(valor)
        if fila.get('tipo_prestamo'):
            texto += '<br/>' + _texto_pdf(etiqueta_reporte(fila['tipo_prestamo']))
        return texto
    if columna.formato in ('estado', 'etiqueta'):
        return _texto_pdf(etiqueta_reporte(valor))
    return _texto_pdf(valor_reporte(valor, columna.formato))


def _peso_columna(columna):
    if columna.formato == 'persona':
        return 2.5
    if columna.formato in ('bien', 'inventario'):
        return 1.8
    if columna.formato in ('fecha', 'dia'):
        return 1.3
    if columna.nombre in ('motivo', 'observacion', 'justificacion_levantamiento', 'condiciones'):
        return 2.3
    if columna.nombre in ('recurso', 'registrador', 'marca', 'modelo'):
        return 1.5
    if columna.formato in ('prestamo', 'reserva', 'numero'):
        return 0.8
    return 1.2


def _preparar_pdf(titulo, generado_en):
    salida = BytesIO()
    documento = SimpleDocTemplate(
        salida,
        pagesize=landscape(A4),
        leftMargin=28,
        rightMargin=28,
        topMargin=28,
        bottomMargin=32,
        title=titulo,
        author='Sistema de préstamos escolares',
    )
    fecha = _fecha_lima(generado_en or datetime.now(LIMA))
    contenido = [
        Paragraph(_texto_pdf(titulo), TITULO),
        Spacer(1, 5),
        Paragraph(f'Fecha de generación: {fecha} (Lima)', TEXTO),
        Spacer(1, 14),
    ]
    return documento, salida, contenido


def _tabla_pdf(columnas, filas, ancho, mensaje_vacio='No hay resultados para estos filtros.'):
    pesos = [_peso_columna(c) for c in columnas]
    minimos = [
        max(stringWidth(palabra, 'Helvetica-Bold', 8) for palabra in c.etiqueta.split()) + 12
        for c in columnas
    ]
    restante = ancho - sum(minimos)
    anchos = [minimo + restante * peso / sum(pesos) for minimo, peso in zip(minimos, pesos)]
    datos = [[Paragraph(_texto_pdf(c.etiqueta), ENCABEZADO) for c in columnas]]
    for fila in filas:
        datos.append([Paragraph(_celda_pdf(fila, c), CUERPO) for c in columnas])

    estilos = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eeeeee')),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#b8b8b8')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]
    if not filas:
        datos.append(
            [Paragraph(_texto_pdf(mensaje_vacio), CUERPO)]
            + [''] * (len(columnas) - 1)
        )
        estilos.append(('SPAN', (0, 1), (-1, 1)))
    return LongTable(
        datos,
        colWidths=anchos,
        repeatRows=1,
        hAlign='LEFT',
        splitByRow=1,
        splitInRow=1,
        style=TableStyle(estilos),
    )


def _pie_pagina(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#666666'))
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 17, f'Página {doc.page}')
    canvas.restoreState()


def generar_pdf_reporte(filtro, filas, generado_en=None):
    reporte = presentar_reporte(filtro.tipo)
    titulo = 'Bienes prestados' if filtro.tipo == 'prestamos' else reporte.titulo
    documento, salida, contenido = _preparar_pdf(titulo, generado_en)
    columnas = [c for c in reporte.columnas if c.en_tabla]
    contenido.append(_tabla_pdf(columnas, filas, documento.width - 12))
    documento.build(contenido, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)
    return salida.getvalue()


def _datos_pdf(campos):
    return Paragraph(
        '<br/>'.join(f'<b>{etiqueta}:</b> {_texto_pdf(valor)}' for etiqueta, valor in campos if valor),
        TEXTO,
    )


def _ficha_historial(sujeto, por_bien):
    if por_bien:
        return [
            ('Objeto', f"{sujeto['codigo_inventario']} · {sujeto['recurso']}"),
            ('Categoría', sujeto['categoria']),
            ('Serie', sujeto['numero_serie']),
            ('Ubicación', sujeto['ubicacion']),
            ('Estado actual del bien', etiqueta_reporte(sujeto['estado'])),
        ]
    return [
        ('Persona', sujeto['nombre_completo']),
        ('DNI', sujeto['dni']),
        ('CUI', sujeto.get('cui')),
        ('Estado de la persona', etiqueta_reporte(sujeto['estado'])),
    ]


def _detalle_prestamo_pdf(detalle):
    recibido = detalle['recibido_por'] or (
        'No registrado' if detalle['fecha_devolucion'] else 'Pendiente'
    )
    if detalle['dni_encargado_devolucion']:
        recibido += f"\nDNI: {detalle['dni_encargado_devolucion']}"
    condiciones = [f"Entrega: {etiqueta_reporte(detalle['condicion_entrega'])}"]
    if detalle['observaciones_entrega']:
        condiciones.append(detalle['observaciones_entrega'])
    if detalle['condicion_devolucion']:
        condiciones.append(f"Devolución: {etiqueta_reporte(detalle['condicion_devolucion'])}")
    if detalle['observaciones_devolucion']:
        condiciones.append(detalle['observaciones_devolucion'])
    return dict(detalle, recibido=recibido, condiciones='\n'.join(condiciones))


def _prestamo_pdf(prestamo, ancho):
    titulo = ' · '.join((
        f"Préstamo #{prestamo['id_prestamo']}",
        etiqueta_reporte(prestamo['tipo_prestamo']),
        etiqueta_reporte(prestamo['estado_prestamo']),
    ))
    entregado = prestamo['entregado_por'] or 'No registrado'
    datos = [
        ('Solicitante', f"{prestamo['solicitante']} · DNI: {prestamo['dni_persona']}"),
        ('Entregado por', f"{entregado} · DNI: {prestamo['dni_encargado']}"),
        ('Fecha de entrega', _fecha_lima(prestamo['fecha_entrega'])),
        ('Integrantes', prestamo['integrantes']),
        ('Observaciones', prestamo['observaciones_prestamo']),
    ]
    columnas = (
        CampoVistaReporte('codigo_inventario', 'Bien', 'bien'),
        CampoVistaReporte('situacion', 'Situación en el préstamo', 'estado'),
        CampoVistaReporte('fecha_limite_devolucion', 'Plazo vigente', 'fecha'),
        CampoVistaReporte('fecha_devolucion', 'Devolución', 'fecha'),
        CampoVistaReporte('recibido', 'Recibida por'),
        CampoVistaReporte('condiciones', 'Condiciones y observaciones'),
    )
    filas = [_detalle_prestamo_pdf(detalle) for detalle in prestamo['detalles']]
    return [
        Paragraph(_texto_pdf(titulo), SUBTITULO),
        _datos_pdf(datos),
        Spacer(1, 6),
        _tabla_pdf(columnas, filas, ancho),
    ]


def _tabla_sanciones_pdf(sanciones, ancho):
    columnas = (
        CampoVistaReporte('sancion', 'Sanción'),
        CampoVistaReporte('prestamo_bien', 'Préstamo y bien'),
        CampoVistaReporte('fecha', 'Fecha', 'fecha'),
        CampoVistaReporte('estado', 'Estado actual', 'estado'),
        CampoVistaReporte('motivo', 'Motivo y levantamiento'),
    )
    filas = []
    for sancion in sanciones:
        motivo = [sancion['motivo'], sancion['descripcion']]
        if sancion['fecha_levantamiento']:
            fecha = _fecha_lima(sancion['fecha_levantamiento'])
            operador = sancion['levantada_por'] or 'No registrado'
            motivo.extend([f'Levantada: {fecha} · {operador}', sancion['justificacion_levantamiento']])
        filas.append(dict(
            sancion,
            sancion=f"#{sancion['id_sancion']}",
            prestamo_bien=f"#{sancion['id_prestamo']} · {sancion['codigo_inventario']}",
            motivo='\n'.join(filter(None, motivo)),
        ))
    return _tabla_pdf(columnas, filas, ancho)


def _tabla_reservas_pdf(reservas, ancho):
    columnas = (
        CampoVistaReporte('solicitud', 'Solicitud'),
        CampoVistaReporte('recurso_asignado', 'Recurso'),
        CampoVistaReporte('solicitante', 'Solicitante', 'persona'),
        CampoVistaReporte('fecha_solicitud', 'Registrada', 'fecha'),
        CampoVistaReporte('fecha_requerida', 'Retiro solicitado', 'fecha'),
        CampoVistaReporte('estado', 'Estado actual', 'estado'),
    )
    filas = [
        dict(
            reserva,
            solicitud=f"#{reserva['id_reserva']}\n{etiqueta_reporte(reserva['tipo_gestion'])}",
            recurso_asignado=f"{reserva['recurso']}\n{reserva['codigo_inventario'] or 'Sin bien asignado'}",
        )
        for reserva in reservas
    ]
    return _tabla_pdf(columnas, filas, ancho)


def generar_pdf_historial(historial, generado_en=None):
    filtro = historial['filtro']
    titulo = 'Mi historial de préstamos' if historial['propio'] else filtro.definicion.titulo
    documento, salida, contenido = _preparar_pdf(titulo, generado_en)
    ancho = documento.width - 12
    sujeto = historial['sujeto']
    if sujeto:
        contenido.append(_datos_pdf(_ficha_historial(sujeto, filtro.tipo == 'historial_bien')))
        contenido.append(Paragraph('Resumen', SECCION))
        columnas_resumen = (
            CampoVistaReporte('prestamos', 'Préstamos relacionados'),
            CampoVistaReporte('pendientes', 'Bienes pendientes de devolución'),
            CampoVistaReporte('eventos', 'Eventos registrados'),
        )
        contenido.append(_tabla_pdf(columnas_resumen, [historial['resumen']], ancho))
        contenido.append(Paragraph('Préstamos relacionados', SECCION))
        for prestamo in historial['prestamos_agrupados']:
            contenido.extend(_prestamo_pdf(prestamo, ancho))
        if not historial['prestamos_agrupados']:
            contenido.append(Paragraph('No hay préstamos registrados.', TEXTO))
        if historial['sanciones']:
            contenido.append(Paragraph('Sanciones vinculadas a los préstamos', SECCION))
            contenido.append(_tabla_sanciones_pdf(historial['sanciones'], ancho))
        if not historial['propio'] and historial['reservas']:
            contenido.append(Paragraph('Solicitudes y reservas', SECCION))
            contenido.append(_tabla_reservas_pdf(historial['reservas'], ancho))
        contenido.append(CondPageBreak(90))
        contenido.append(Paragraph('Cronología registrada', TITULO_CRONOLOGIA))
        columnas = [c for c in presentar_reporte(filtro.tipo).columnas if c.en_tabla]
        contenido.append(_tabla_pdf(columnas, historial['filas'], ancho, 'No hay eventos registrados.'))
    else:
        contenido.append(Paragraph('Selecciona un objeto o una persona para descargar su historial.', TEXTO))
    documento.build(contenido, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)
    return salida.getvalue()
