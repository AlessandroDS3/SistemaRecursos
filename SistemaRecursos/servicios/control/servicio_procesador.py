"""Ejecuta la revisión periódica con exclusión entre procesos y deja constancia (OPE-01)."""

import logging
from datetime import timedelta

registro = logging.getLogger(__name__)

# El ciclo corre cada 30 s; cinco minutos sin una ejecución correcta indica un problema.
MAXIMO_SIN_EJECUCION = timedelta(minutes=5)


class ServicioAplicacionProcesador:
    def __init__(self, repositorio):
        self.repositorio = repositorio

    def ejecutar_revision_de_vencimientos(self, operaciones, *, intervalo_minimo=None) -> str:
        """Devuelve 'ok', 'omitida' (otro proceso la está haciendo) o 'error'."""
        try:
            with self.repositorio.bloqueo_exclusivo() as obtenido:
                if not obtenido:
                    return 'omitida'
                if intervalo_minimo is not None and self._hubo_revision_reciente(intervalo_minimo):
                    return 'omitida'
                errores = []
                for operacion in operaciones:
                    try:
                        operacion()
                    except Exception as error:  # Una operación no debe detener las demás.
                        registro.exception('Falló una revisión de vencimientos; se reintentará.')
                        errores.append(f'{getattr(operacion, "__name__", "operación")}: {error}')
                if errores:
                    self._registrar_error_de_revision(' | '.join(errores))
                    return 'error'
                self.repositorio.registrar_ejecucion_correcta()
                return 'ok'
        except Exception as error:  # Base caída: se reintenta en el siguiente ciclo.
            registro.exception('No se pudo ejecutar la revisión de vencimientos.')
            self._registrar_error_de_revision(str(error))
            return 'error'

    def _hubo_revision_reciente(self, intervalo):
        estado = self.repositorio.consultar_estado_procesador() or {}
        ultimo = max((estado[campo] for campo in ('ultima_ejecucion_correcta', 'ultimo_error_fecha')
                      if estado.get(campo) is not None), default=None)
        return ultimo is not None and self.repositorio.consultar_fecha_actual() - ultimo < intervalo

    def _registrar_error_de_revision(self, mensaje):
        try:
            self.repositorio.registrar_error_del_procesador(mensaje)
        except Exception:
            registro.exception('No se pudo registrar el error del procesador.')

    def consultar_estado_procesador(self) -> dict:
        estado = self.repositorio.consultar_estado_procesador() or {}
        ahora = self.repositorio.consultar_fecha_actual()
        ultima = estado.get('ultima_ejecucion_correcta')
        return dict(
            ultima_ejecucion_correcta=ultima,
            ultimo_error=estado.get('ultimo_error'),
            ultimo_error_fecha=estado.get('ultimo_error_fecha'),
            fallos_consecutivos=estado.get('fallos_consecutivos', 0),
            alerta=ultima is None or ahora - ultima > MAXIMO_SIN_EJECUCION,
        )
