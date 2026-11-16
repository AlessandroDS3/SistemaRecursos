import csv
from io import StringIO
from datetime import datetime, timezone
from dominio.compartido.validacion import LIMA
from dominio.gestion_control.reporte import (
    FILAS_POR_PAGINA,
    FiltroReporte,
    IRepositorioReporte,
    celda_csv,
)


class ServicioAplicacionReporte:
    def __init__(self, repositorio: IRepositorioReporte):
        self.repositorio = repositorio

    def consultar_reportes(self, datos, paginar=True):
        filtro = FiltroReporte(
            **{k: datos[k] for k in FiltroReporte.__dataclass_fields__ if k in datos}
        )
        filas, resumen = self.repositorio.consultar_reportes(filtro, paginar)
        return dict(
            filtro=filtro,
            reporte=filtro.definicion,
            parametros=filtro.parametros,
            filas=filas,
            resumen=resumen,
            paginas=max(1, (resumen['detalles'] + FILAS_POR_PAGINA - 1) // FILAS_POR_PAGINA),
        )

    def exportar_reportes_csv(self, datos):
        resultado = self.consultar_reportes(datos, paginar=False)
        campos = [c.nombre for c in resultado['reporte'].columnas]
        salida = StringIO(newline='')
        salida.write('\ufeff')
        escritor = csv.writer(salida, delimiter=';', lineterminator='\r\n')
        escritor.writerow(campos)
        for fila in resultado['filas']:
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
        return salida.getvalue(), resultado['filtro'].tipo
