"""Ejecuta casos de uso periódicos; no introduce reglas ni abre conexiones SQL directamente."""

import atexit
from threading import Event, Thread


def iniciar_procesador_vencimientos(sanciones, reservas, procesador, intervalo=30):
    """Revisa vencimientos cada `intervalo` segundos mientras el proceso esté activo.

    `procesador` registra la última ejecución correcta y los errores, y evita que dos
    procesos sobre la misma base hagan la revisión a la vez (OPE-01).
    """
    detener = Event()
    operaciones = (
        sanciones.procesar_sanciones_por_vencimiento,
        reservas.expirar_reservas_vencidas,
    )

    def procesar():
        while not detener.is_set():
            procesador.ejecutar_revision(operaciones)
            detener.wait(intervalo)

    hilo = Thread(target=procesar, name='vencimientos', daemon=True)
    atexit.register(detener.set)
    hilo.start()
    return detener
