from servicios.reportes.contratos import IRepositorioReporte
from servicios.reportes.filtro_reporte import FiltroReporte
from servicios.reportes.historial import organizar_historial


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
