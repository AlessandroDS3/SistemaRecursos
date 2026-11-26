from argparse import ArgumentParser
import logging
import os
from pathlib import Path
from secrets import token_hex

from flask import Flask

from repositorio.base_datos.conexion_mysql import MySQLConnection
from repositorio.personas_usuarios.repositorio_acceso_sql import RepositorioAccesoSQL
from repositorio.personas_usuarios.repositorio_cuenta_sql import RepositorioCuentaSQL
from repositorio.personas_usuarios.repositorio_persona_sql import RepositorioPersonaSQL
from repositorio.recursos.repositorio_recurso_sql import RepositorioRecursoSQL
from repositorio.recursos.repositorio_bien_material_sql import RepositorioBienMaterialSQL
from repositorio.control.repositorio_politica_prestamo_sql import RepositorioPoliticaPrestamoSQL
from repositorio.prestamos.repositorio_prestamo_sql import RepositorioPrestamoSQL
from repositorio.prestamos.repositorio_reserva_sql import RepositorioReservaSQL
from repositorio.prestamos.repositorio_ampliacion_prestamo_sql import RepositorioAmpliacionPrestamoSQL
from repositorio.control.repositorio_sancion_sql import RepositorioSancionSQL
from repositorio.reportes.repositorio_reporte_sql import RepositorioReporteSQL
from repositorio.control.repositorio_procesador_sql import RepositorioProcesadorSQL

from servicios.personas_usuarios.servicio_acceso import ServicioAplicacionAcceso
from servicios.personas_usuarios.servicio_cuenta import ServicioAplicacionCuenta
from servicios.personas_usuarios.servicio_persona import ServicioAplicacionPersona
from servicios.recursos.servicio_recurso import ServicioAplicacionRecurso
from servicios.recursos.servicio_bien_material import ServicioAplicacionBienMaterial
from servicios.control.servicio_politica_prestamo import ServicioAplicacionPoliticaPrestamo
from servicios.prestamos.servicio_prestamo import ServicioAplicacionPrestamo
from servicios.prestamos.servicio_reserva import ServicioAplicacionReserva
from servicios.prestamos.servicio_ampliacion_prestamo import ServicioAplicacionAmpliacionPrestamo
from servicios.control.servicio_sancion import ServicioAplicacionSancion
from servicios.reportes.servicio_reporte import ServicioAplicacionReporte
from servicios.control.servicio_procesador import ServicioAplicacionProcesador
from arranque.procesador_vencimientos import iniciar_procesador_vencimientos
from dominio.gestion_personas_usuarios.sesion import DURACION_MAXIMA

from presentacion.controladores.controlador_inicio import registrar_inicio
from presentacion.errores_http import registrar_manejadores_de_errores_http
from presentacion.filtros_plantillas import registrar_filtros_de_plantillas
from presentacion.seguridad import configurar_seguridad
from presentacion.formularios import error_campo, generar_id_del_campo, valor_formulario
from presentacion.controladores.personas_usuarios.controlador_acceso import ControladorAcceso
from presentacion.controladores.personas_usuarios.controlador_cuenta import ControladorCuenta
from presentacion.controladores.personas_usuarios.controlador_persona import ControladorPersona
from presentacion.controladores.recursos.controlador_recurso import ControladorRecurso
from presentacion.controladores.recursos.controlador_bien_material import ControladorBienMaterial
from presentacion.controladores.control.controlador_politica_prestamo import ControladorPoliticaPrestamo
from presentacion.controladores.prestamos.controlador_prestamo import ControladorPrestamo
from presentacion.controladores.prestamos.controlador_reserva import ControladorReserva
from presentacion.controladores.prestamos.controlador_ampliacion_prestamo import ControladorAmpliacionPrestamo
from presentacion.controladores.control.controlador_sancion import ControladorSancion
from presentacion.controladores.reportes.controlador_reporte import ControladorReporte


def obtener_clave_de_sesion_flask():
    if os.getenv('FLASK_SECRET_KEY'):
        return os.environ['FLASK_SECRET_KEY']
    archivo = Path(__file__).parent / 'clave_sesion.txt'
    if not archivo.exists():
        archivo.write_text(token_hex(32))
    return archivo.read_text().strip()


def crear_servicios(conexion, dominios_institucionales=('unsa.edu.pe',)):
    return {
        'acceso': ServicioAplicacionAcceso(RepositorioAccesoSQL(conexion)),
        'cuentas': ServicioAplicacionCuenta(
            RepositorioCuentaSQL(conexion), dominios_institucionales
        ),
        'personas': ServicioAplicacionPersona(RepositorioPersonaSQL(conexion)),
        'recursos': ServicioAplicacionRecurso(RepositorioRecursoSQL(conexion)),
        'bienes': ServicioAplicacionBienMaterial(RepositorioBienMaterialSQL(conexion)),
        'politicas': ServicioAplicacionPoliticaPrestamo(RepositorioPoliticaPrestamoSQL(conexion)),
        'prestamos': ServicioAplicacionPrestamo(RepositorioPrestamoSQL(conexion)),
        'reservas': ServicioAplicacionReserva(RepositorioReservaSQL(conexion)),
        'ampliaciones': ServicioAplicacionAmpliacionPrestamo(
            RepositorioAmpliacionPrestamoSQL(conexion)
        ),
        'sanciones': ServicioAplicacionSancion(RepositorioSancionSQL(conexion)),
        'reportes': ServicioAplicacionReporte(RepositorioReporteSQL(conexion)),
        'procesador': ServicioAplicacionProcesador(RepositorioProcesadorSQL(conexion)),
    }


def registrar_controladores(app, servicios):
    controladores = [
        ControladorAcceso(servicios['acceso']),
        ControladorCuenta(servicios['cuentas']),
        ControladorPersona(servicios['personas'], servicios['cuentas']),
        ControladorRecurso(servicios['recursos'], servicios['bienes'], servicios['politicas']),
        ControladorBienMaterial(servicios['bienes'], servicios['recursos']),
        ControladorPoliticaPrestamo(servicios['politicas'], servicios['recursos']),
        ControladorPrestamo(
            servicios['prestamos'],
            servicios['bienes'],
            servicios['recursos'],
            servicios['politicas'],
            servicios['ampliaciones'],
        ),
        ControladorReserva(servicios['reservas']),
        ControladorAmpliacionPrestamo(servicios['ampliaciones'], servicios['prestamos']),
        ControladorSancion(servicios['sanciones']),
        ControladorReporte(servicios['reportes'], servicios['recursos']),
    ]
    for controlador in controladores:
        app.register_blueprint(controlador.blueprint)


def create_app(config=None):
    app = Flask(
        __name__, template_folder='presentacion/vistas', static_folder='presentacion/static'
    )
    app.config.update(
        SECRET_KEY=obtener_clave_de_sesion_flask(),
        SESSION_COOKIE_NAME='recursos_rehecho',
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        # La cookie dura como máximo lo mismo que la sesión del servidor (SEG-02).
        PERMANENT_SESSION_LIFETIME=DURACION_MAXIMA,
        MAX_CONTENT_LENGTH=1024 * 1024,
    )
    app.config.update(config or {})

    conexion = MySQLConnection(app.config.get('MYSQL_CONFIG'))
    dominios = app.config.get(
        'DOMINIOS_CORREO_INSTITUCIONAL', os.getenv('DOMINIOS_CORREO_INSTITUCIONAL', 'unsa.edu.pe')
    )
    if isinstance(dominios, str):
        dominios = dominios.split(',')
    servicios = crear_servicios(conexion, dominios)
    app.extensions['servicios'] = servicios

    configurar_seguridad(app, servicios['acceso'])
    app.jinja_env.globals.update(
        error_campo=error_campo, generar_id_del_campo=generar_id_del_campo,
        valor_formulario=valor_formulario,
    )
    registrar_controladores(app, servicios)
    registrar_inicio(app, servicios)
    registrar_filtros_de_plantillas(app)
    registrar_manejadores_de_errores_http(app)
    return app


def iniciar_servidor_web(argv=None):
    parser = ArgumentParser(description='Inicia el servidor web del Sistema de Recursos.')
    parser.add_argument('--sin-procesador', action='store_true',
                        help='Ejecuta la revisión automática en un proceso independiente.')
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    detener = None
    if not args.sin_procesador:
        servicios = app.extensions['servicios']
        detener = iniciar_procesador_vencimientos(
            servicios['sanciones'], servicios['reservas'], servicios['procesador']
        )
    try:
        app.run(host='127.0.0.1', port=int(os.getenv('PORT', '5001')), use_reloader=False)
    finally:
        if detener is not None:
            detener.set()


if __name__ == '__main__':
    iniciar_servidor_web()
