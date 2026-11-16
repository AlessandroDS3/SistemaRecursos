from datetime import datetime, timedelta, timezone
import logging
import os
from pathlib import Path
from secrets import token_hex

from flask import Flask, g, render_template
from mysql.connector import Error as ErrorMySQL
from werkzeug.exceptions import HTTPException

from dominio.compartido.validacion import Conflicto, LIMA, NoEncontrado

from repositorio.conexion_mysql import MySQLConnection
from repositorio.repositorio_acceso_sql import RepositorioAccesoSQL
from repositorio.repositorio_cuenta_sql import RepositorioCuentaSQL
from repositorio.repositorio_persona_sql import RepositorioPersonaSQL
from repositorio.repositorio_rol_sql import RepositorioRolSQL
from repositorio.repositorio_recurso_sql import RepositorioRecursoSQL
from repositorio.repositorio_bien_material_sql import RepositorioBienMaterialSQL
from repositorio.repositorio_politica_prestamo_sql import RepositorioPoliticaPrestamoSQL
from repositorio.repositorio_prestamo_sql import RepositorioPrestamoSQL
from repositorio.repositorio_reserva_sql import RepositorioReservaSQL
from repositorio.repositorio_ampliacion_prestamo_sql import RepositorioAmpliacionPrestamoSQL
from repositorio.repositorio_sancion_sql import RepositorioSancionSQL
from repositorio.repositorio_reporte_sql import RepositorioReporteSQL

from servicios.servicio_acceso import ServicioAplicacionAcceso
from servicios.servicio_cuenta import ServicioAplicacionCuenta
from servicios.servicio_persona import ServicioAplicacionPersona
from servicios.servicio_rol import ServicioAplicacionRol
from servicios.servicio_recurso import ServicioAplicacionRecurso
from servicios.servicio_bien_material import ServicioAplicacionBienMaterial
from servicios.servicio_politica_prestamo import ServicioAplicacionPoliticaPrestamo
from servicios.servicio_prestamo import ServicioAplicacionPrestamo
from servicios.servicio_reserva import ServicioAplicacionReserva
from servicios.servicio_ampliacion_prestamo import ServicioAplicacionAmpliacionPrestamo
from servicios.servicio_sancion import ServicioAplicacionSancion
from servicios.servicio_reporte import ServicioAplicacionReporte
from servicios.procesador_vencimientos import iniciar_procesador_vencimientos

from presentacion.seguridad import configurar_seguridad
from presentacion.controladores.controlador_acceso import ControladorAcceso
from presentacion.controladores.controlador_cuenta import ControladorCuenta
from presentacion.controladores.controlador_persona import ControladorPersona
from presentacion.controladores.controlador_rol import ControladorRol
from presentacion.controladores.controlador_recurso import ControladorRecurso
from presentacion.controladores.controlador_bien_material import ControladorBienMaterial
from presentacion.controladores.controlador_politica_prestamo import ControladorPoliticaPrestamo
from presentacion.controladores.controlador_prestamo import ControladorPrestamo
from presentacion.controladores.controlador_reserva import ControladorReserva
from presentacion.controladores.controlador_ampliacion_prestamo import ControladorAmpliacionPrestamo
from presentacion.controladores.controlador_sancion import ControladorSancion
from presentacion.controladores.controlador_reporte import ControladorReporte


def clave_local():
    if os.getenv('FLASK_SECRET_KEY'):
        return os.environ['FLASK_SECRET_KEY']
    archivo = Path(__file__).parent / 'clave_sesion.txt'
    if not archivo.exists():
        archivo.write_text(token_hex(32))
    return archivo.read_text().strip()


def crear_servicios(conexion):
    return {
        'acceso': ServicioAplicacionAcceso(RepositorioAccesoSQL(conexion)),
        'cuentas': ServicioAplicacionCuenta(RepositorioCuentaSQL(conexion)),
        'personas': ServicioAplicacionPersona(RepositorioPersonaSQL(conexion)),
        'roles': ServicioAplicacionRol(RepositorioRolSQL(conexion)),
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
    }


def registrar_controladores(app, servicios):
    controladores = [
        ControladorAcceso(servicios['acceso']),
        ControladorCuenta(servicios['cuentas']),
        ControladorPersona(servicios['personas']),
        ControladorRol(servicios['roles'], servicios['cuentas']),
        ControladorRecurso(servicios['recursos'], servicios['bienes']),
        ControladorBienMaterial(servicios['bienes'], servicios['recursos']),
        ControladorPoliticaPrestamo(servicios['politicas'], servicios['recursos']),
        ControladorPrestamo(servicios['prestamos'], servicios['bienes']),
        ControladorReserva(servicios['reservas']),
        ControladorAmpliacionPrestamo(servicios['ampliaciones']),
        ControladorSancion(servicios['sanciones']),
        ControladorReporte(servicios['reportes'], servicios['recursos']),
    ]
    for controlador in controladores:
        app.register_blueprint(controlador.blueprint)


def registrar_inicio(app, servicios):
    @app.get('/')
    def inicio():
        resumen = {}
        usuario = g.usuario
        gestionar = usuario.permite('PRESTAMOS_GESTIONAR')

        if gestionar or usuario.permite('PRESTAMOS_PROPIOS_CONSULTAR'):
            dni = None if gestionar else usuario.dni
            prestamos = servicios['prestamos'].consultar_prestamos({}, dni)
            pendientes = [p for p in prestamos if p['estado_actual'] != 'DEVUELTO']
            vencidos = [p for p in prestamos if p['estado_actual'] == 'VENCIDO']
            resumen['prestamos_pendientes'] = len(pendientes)
            resumen['prestamos_vencidos'] = len(vencidos)

        if usuario.permite('CATALOGO_CONSULTAR'):
            recursos = servicios['recursos'].consultar_recursos({})
            resumen['bienes_disponibles'] = sum(r['disponibles'] for r in recursos)

        return render_template('inicio.html', resumen=resumen)


def registrar_filtros(app):
    @app.template_filter('fecha')
    def fecha(valor):
        if not valor:
            return '—'
        if isinstance(valor, datetime):
            valor = valor.replace(tzinfo=timezone.utc).astimezone(LIMA)
            return valor.strftime('%d/%m/%Y %H:%M')
        return str(valor)

    @app.template_filter('hora')
    def hora(valor):
        if not valor:
            return ''
        if isinstance(valor, timedelta):
            minutos = int(valor.total_seconds()) // 60
            return f'{minutos // 60:02d}:{minutos % 60:02d}'
        return str(valor)[:5]


def registrar_errores(app):
    def mostrar_error(mensaje, codigo):
        return render_template('error.html', mensaje=mensaje, codigo=codigo), codigo

    @app.errorhandler(Conflicto)
    def conflicto(error):
        return mostrar_error(str(error), 409)

    @app.errorhandler(ValueError)
    def valor_invalido(error):
        return mostrar_error(str(error), 400)

    @app.errorhandler(NoEncontrado)
    def no_encontrado(error):
        return mostrar_error(str(error), 404)

    @app.errorhandler(PermissionError)
    def sin_permiso(error):
        return mostrar_error(str(error), 403)

    @app.errorhandler(HTTPException)
    def error_http(error):
        return mostrar_error(error.description, error.code)

    @app.errorhandler(ErrorMySQL)
    def error_base(error):
        app.logger.exception('Falló la base de datos.')
        return mostrar_error('No se pudo acceder a la base de datos.', 503)


def create_app(config=None):
    app = Flask(
        __name__, template_folder='presentacion/vistas',
          static_folder='presentacion/static'
    )
    app.config.update(
        SECRET_KEY=clave_local(),
        SESSION_COOKIE_NAME='recursos_rehecho',
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        MAX_CONTENT_LENGTH=1024 * 1024,
    )
    app.config.update(config or {})

    conexion = MySQLConnection(app.config.get('MYSQL_CONFIG'))
    servicios = crear_servicios(conexion)
    app.extensions['servicios'] = servicios

    configurar_seguridad(app, servicios['acceso'])
    registrar_controladores(app, servicios)
    registrar_inicio(app, servicios)
    registrar_filtros(app)
    registrar_errores(app)
    return app


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    servicios = app.extensions['servicios']
    iniciar_procesador_vencimientos(servicios['sanciones'], servicios['reservas'])
    app.run(host='127.0.0.1', port=int(os.getenv('PORT', '5001')))