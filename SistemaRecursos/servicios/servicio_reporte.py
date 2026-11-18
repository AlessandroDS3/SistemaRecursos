import csv
from io import StringIO
from datetime import datetime, timezone
from dominio.compartido.validacion import LIMA
from dominio.gestion_control.historial import organizar_historial
from dominio.gestion_control.reporte import (
    FiltroReporte,
    IRepositorioReporte,
    celda_csv,
)


class ServicioAplicacionReporte:
    def __init__(self, repositorio: IRepositorioReporte):
        self.repositorio = repositorio

    def consultar_reportes(self, datos):
        filtro = FiltroReporte.desde_datos(datos)
        if filtro.tipo in ('historial_bien', 'historial_persona'):
            return self._consultar_historial(filtro)
        filas = self.repositorio.consultar_filas_reporte(filtro)
        return dict(
            filtro=filtro,
            reporte=filtro.definicion,
            parametros=filtro.parametros,
            filas=filas,
        )

    def consultar_exportacion_reporte(self, datos):
        resultado = self.consultar_reportes(datos)
        return resultado['filtro'], resultado['filas']

    def _consultar_historial(self, filtro, propio=False):
        resultado = organizar_historial(
            self.repositorio.consultar_historial(filtro, propio)
        )
        return dict(
            resultado,
            filtro=filtro,
            reporte=filtro.definicion,
            parametros=filtro.parametros,
            propio=propio,
        )

    def consultar_historial_propio(self, documento):
        # La identidad se recibe de la sesión, nunca de los parámetros del enlace.
        filtro = FiltroReporte(tipo='historial_persona', dni_persona=documento)
        return self._consultar_historial(filtro, propio=True)

    def exportar_historial_propio_csv(self, documento):
        resultado = self.consultar_historial_propio(documento)
        return (
            self._exportar_csv(resultado['filtro'], resultado['filas']),
            'mi_historial',
        )

    def exportar_reportes_csv(self, datos):
        filtro, filas = self.consultar_exportacion_reporte(datos)
        return self._exportar_csv(filtro, filas), filtro.tipo

    @staticmethod
    def _exportar_csv(filtro, filas):
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
            escritor.writerow([celda_csv(v) for v in valores])
        return salida.getvalue()
