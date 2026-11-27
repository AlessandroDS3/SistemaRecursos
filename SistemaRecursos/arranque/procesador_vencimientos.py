"""Ejecuta casos de uso periódicos; no introduce reglas ni abre conexiones SQL directamente."""

from argparse import ArgumentParser
from datetime import timedelta
import logging
from threading import Event, Thread


def procesar_vencimientos(sanciones, reservas, procesador, detener, intervalo=30):
    operaciones = (
        sanciones.procesar_sanciones_por_vencimiento,
        reservas.expirar_reservas_vencidas,
    )

    periodo = timedelta(seconds=intervalo)
    while not detener.is_set():
        procesador.ejecutar_revision_de_vencimientos(operaciones, intervalo_minimo=periodo)
        detener.wait(intervalo)


def iniciar_procesador_vencimientos(sanciones, reservas, procesador, intervalo=30):
    detener = Event()
    hilo = Thread(target=procesar_vencimientos, args=(sanciones, reservas, procesador, detener, intervalo),
                  name='vencimientos', daemon=True)
    hilo.start()
    return detener


def ejecutar_procesador_desde_consola(argv=None):
    parser = ArgumentParser(description='Ejecuta la revisión automática de vencimientos.')
    parser.parse_args(argv)

    from app import crear_servicios
    from repositorio.base_datos.conexion_mysql import MySQLConnection

    logging.basicConfig(level=logging.INFO)
    servicios = crear_servicios(MySQLConnection())
    logging.info('Procesador de vencimientos iniciado.')
    try:
        procesar_vencimientos(servicios['sanciones'], servicios['reservas'], servicios['procesador'], Event())
    except KeyboardInterrupt:
        return 0


if __name__ == '__main__':
    raise SystemExit(ejecutar_procesador_desde_consola())
