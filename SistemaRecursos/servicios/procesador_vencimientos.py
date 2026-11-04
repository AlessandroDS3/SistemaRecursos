"""Procesador del servidor: independiente de las consultas y desactivado en pruebas."""
import atexit
from threading import Event, Thread
from time import monotonic


def iniciar_procesador_vencimientos(app, servicio, servicio_reservas=None):
    detener = Event()

    def procesar():
        espera = 1
        siguiente_revision_reservas = 0
        while not detener.is_set():
            if servicio_reservas is not None and monotonic() >= siguiente_revision_reservas:
                siguiente_revision_reservas = monotonic() + 30
                try:
                    servicio_reservas.expirar_solicitudes_vencidas()
                except Exception:
                    app.logger.exception('No se pudieron expirar solicitudes y reservas; se reintentará.')
            try:
                servicio.aplicar_sanciones_vencidas()
                espera = 1
            except Exception:
                app.logger.exception('No se pudieron registrar las sanciones por vencimiento; se reintentará.')
                espera = min(espera * 2, 30)
            detener.wait(espera)

    hilo = Thread(target=procesar, name='sanciones-vencimientos', daemon=True)
    app.extensions['procesador_vencimientos'] = {'detener': detener, 'hilo': hilo}
    atexit.register(detener.set)
    hilo.start()
