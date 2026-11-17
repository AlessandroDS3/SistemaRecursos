"""PDF sencillo: título, fecha de generación y tabla de resultados filtrados."""

from datetime import date, datetime, timezone
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from dominio.compartido.validacion import LIMA
from presentacion.formatos_reportes import etiqueta_reporte, presentar_reporte, valor_reporte


def _texto_pdf(valor):
    return escape(str(valor)).replace('\r\n', '\n').replace('\n', '<br/>')


def _celda_pdf(fila, columna):
    valor = fila.get(columna.nombre)
    if valor is None or valor == '':
        return '-'
    if isinstance(valor, datetime):
        if valor.tzinfo is None:
            valor = valor.replace(tzinfo=timezone.utc)
        return valor.astimezone(LIMA).strftime('%d/%m/%Y<br/>%H:%M')
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
    if columna.nombre in ('motivo', 'observacion', 'justificacion_levantamiento'):
        return 2.3
    if columna.nombre in ('recurso', 'registrador', 'marca', 'modelo'):
        return 1.5
    if columna.formato in ('prestamo', 'reserva', 'numero'):
        return 0.8
    return 1.2


def generar_pdf_reporte(filtro, filas, generado_en=None):
    reporte = presentar_reporte(filtro.tipo)
    titulo = 'Bienes prestados' if filtro.tipo == 'prestamos' else reporte.titulo
    generado_en = generado_en or datetime.now(LIMA)
    fecha = generado_en.astimezone(LIMA).strftime('%d/%m/%Y %H:%M')
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
    cuerpo = ParagraphStyle(
        'CeldaReporte',
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        alignment=TA_LEFT,
        splitLongWords=True,
    )
    encabezado = ParagraphStyle(
        'EncabezadoReporte',
        parent=cuerpo,
        fontName='Helvetica-Bold',
        fontSize=8,
    )
    estilo_titulo = ParagraphStyle(
        'TituloReporte',
        fontName='Helvetica-Bold',
        fontSize=17,
        leading=21,
    )
    estilo_fecha = ParagraphStyle(
        'FechaReporte',
        parent=cuerpo,
        fontSize=9,
        leading=12,
    )
    columnas = [c for c in reporte.columnas if c.en_tabla]
    pesos = [_peso_columna(c) for c in columnas]
    minimos = [
        max(stringWidth(palabra, 'Helvetica-Bold', 8) for palabra in c.etiqueta.split()) + 12
        for c in columnas
    ]
    restante = documento.width - sum(minimos)
    anchos = [minimo + restante * peso / sum(pesos) for minimo, peso in zip(minimos, pesos)]
    datos = [[Paragraph(_texto_pdf(c.etiqueta), encabezado) for c in columnas]]
    for fila in filas:
        datos.append([Paragraph(_celda_pdf(fila, c), cuerpo) for c in columnas])

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
            [Paragraph('No hay resultados para estos filtros.', cuerpo)]
            + [''] * (len(columnas) - 1)
        )
        estilos.append(('SPAN', (0, 1), (-1, 1)))
    tabla = LongTable(
        datos,
        colWidths=anchos,
        repeatRows=1,
        hAlign='LEFT',
        splitByRow=1,
        splitInRow=1,
        style=TableStyle(estilos),
    )

    def pie_pagina(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 17, f'Página {doc.page}')
        canvas.restoreState()

    documento.build(
        [
            Paragraph(_texto_pdf(titulo), estilo_titulo),
            Spacer(1, 5),
            Paragraph(f'Fecha: {fecha} (Lima)', estilo_fecha),
            Spacer(1, 14),
            tabla,
        ],
        onFirstPage=pie_pagina,
        onLaterPages=pie_pagina,
    )
    return salida.getvalue()
