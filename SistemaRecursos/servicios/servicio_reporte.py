import csv
from io import StringIO
from datetime import datetime, timezone
from dominio.compartido.validacion import LIMA
from dominio.gestion_control.reporte import (
    paginas_reporte,
    FiltroReporte,
    IRepositorioReporte,
    celda_csv,
)


class ServicioAplicacionReporte:
    def __init__(self, repositorio: IRepositorioReporte):
        self.repositorio = repositorio

    def consultar_reportes(self, datos, paginar=True):
        filtro = FiltroReporte.desde_datos(datos)
        filas, resumen = self.repositorio.consultar_reportes(filtro, paginar)
        return dict(
            filtro=filtro,
            reporte=filtro.definicion,
            parametros=filtro.parametros,
            filas=filas,
            resumen=resumen,
            paginas=paginas_reporte(resumen['detalles']),
        )

    def exportar_reportes_csv(self, datos):
        filtro = FiltroReporte.desde_datos(datos)
        filas = self.repositorio.consultar_filas_reporte(filtro)
        campos = [c.nombre for c in filtro.definicion.columnas]
        salida = StringIO(newline='')
        salida.write('\ufeff')
        escritor = csv.writer(salida, delimiter=';', lineterminator='\r\n')
        escritor.writerow(campos)
        for fila in filas:
            valores = [fila[campo] for campo in campos]
            valores = [
                (
                    v.replace(tzinfo=timezone.utc).astimezone(LIMA).strftime('%Y-%m-%d %H:%M:%S')
                    if isinstance(v, datetime)
                    else v
                )
                for v in valores
            ]
            escritor.writerow([celda_csv(v) for v in valores])
        return salida.getvalue(), filtro.tipo
