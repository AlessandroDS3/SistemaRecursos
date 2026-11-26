"""Exportación CSV de reportes e historiales."""

import csv
from datetime import datetime, timezone
from io import StringIO

from dominio.compartido.validacion import LIMA


def _sanear_valor_para_csv(valor):
    texto_celda = '' if valor is None else str(valor)
    peligroso = texto_celda.startswith(('\t', '\r', '\n')) or texto_celda.lstrip().startswith(
        ('=', '+', '-', '@')
    )
    return "'" + texto_celda if peligroso else texto_celda


def generar_csv_reporte(filtro, filas):
    campos = [c.nombre for c in filtro.definicion.columnas]
    salida = StringIO(newline='')
    salida.write('\ufeff')
    escritor = csv.writer(salida, delimiter=';', lineterminator='\r\n')
    escritor.writerow(campos)
    for fila in filas:
        valores = [fila[campo] for campo in campos]
        valores = [
            (
                v.replace(tzinfo=timezone.utc)
                .astimezone(LIMA)
                .strftime('%Y-%m-%d %H:%M:%S')
                if isinstance(v, datetime)
                else v
            )
            for v in valores
        ]
        escritor.writerow([_sanear_valor_para_csv(v) for v in valores])
    return salida.getvalue()
