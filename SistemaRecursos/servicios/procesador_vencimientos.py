"""Ejecuta casos de uso periódicos; no introduce reglas ni abre conexiones SQL."""

import atexit
import logging
from threading import Event, Thread


def iniciar_procesador_vencimientos(sanciones, reservas, intervalo=30):
    detener = Event()

    def procesar():
        while not detener.is_set():
            for servicio in (sanciones, reservas):
                try:
                    servicio.procesar_vencimientos()
                except Exception:
                    logging.getLogger(__name__).exception(
                        'Falló una revisión de vencimientos; se reintentará.'
                    )
            detener.wait(intervalo)

    hilo = Thread(target=procesar, name='vencimientos', daemon=True)
    atexit.register(detener.set)
    hilo.start()
    return detener
