"""Punto de composición: conecta HTTP, casos de uso y adaptadores de MySQL."""

from datetime import datetime, timedelta, timezone
import logging
import os
from pathlib import Path
from secrets import token_hex

from flask import Flask, g, redirect, render_template, url_for
from flask_wtf.csrf import CSRFProtect
from mysql.connector import Error as ErrorMySQL, IntegrityError
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
    archivo = Path(__file__).parent / 'datos_locales' / 'clave_sesion.txt'
    archivo.parent.mkdir(exist_ok=True)
    try:
        with archivo.open('x', encoding='utf-8') as salida:
            salida.write(token_hex(32))
    except FileExistsError:
        pass
    clave = archivo.read_text(encoding='utf-8').strip()
    if len(clave) < 32:
        raise ValueError('La clave de sesión local está vacía o incompleta.')
    return clave


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
        'ampliaciones': ServicioAplicacionAmpliacionPrestamo(RepositorioAmpliacionPrestamoSQL(conexion)),
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
        ControladorReporte(servicios['reportes']),
    ]
    for controlador in controladores:
        app.register_blueprint(controlador.blueprint)


def registrar_inicio(app):
    @app.get('/')
    def inicio():
        for permiso, endpoint in (
            ('CATALOGO_CONSULTAR', 'recursos.consultar_recursos'),
            ('PRESTAMOS_GESTIONAR', 'prestamos.consultar_prestamos'),
            ('PERSONAS_CONSULTAR', 'personas.consultar_personas'),
        ):
            if g.usuario.permite(permiso):
                return redirect(url_for(endpoint))
        return render_template('inicio.html')


def registrar_filtros(app):
    @app.template_filter('fecha')
    def fecha(valor):
        if not valor:
            return '—'
        if isinstance(valor, datetime):
            return valor.replace(tzinfo=timezone.utc).astimezone(LIMA).strftime('%d/%m/%Y %H:%M')
        return str(valor)

    @app.template_filter('hora')
    def hora(valor):
        if not valor:
            return ''
        if isinstance(valor, timedelta):
            segundos = int(valor.total_seconds())
            return f'{segundos // 3600:02d}:{segundos % 3600 // 60:02d}'
        return valor.strftime('%H:%M') if hasattr(valor, 'strftime') else str(valor)[:5]


def registrar_errores(app):
    def mostrar_error(error, codigo):
        return render_template('error.html', mensaje=str(error), codigo=codigo), codigo

    app.register_error_handler(Conflicto, lambda e: mostrar_error(e, 409))
    app.register_error_handler(ValueError, lambda e: mostrar_error(e, 400))
    app.register_error_handler(NoEncontrado, lambda e: mostrar_error(e, 404))
    app.register_error_handler(PermissionError, lambda e: mostrar_error(e, 403))
    app.register_error_handler(HTTPException, lambda e: mostrar_error(e.description, e.code))

    @app.errorhandler(ErrorMySQL)
    def error_base(error):
        app.logger.exception('Falló una operación de base de datos.')
        if error.errno in (1205, 1213):
            return mostrar_error(
                'Otra operación modificaba estos datos. Recarga e inténtalo otra vez.', 409
            )
        if isinstance(error, IntegrityError):
            return mostrar_error(
                'Los datos están duplicados o relacionados con otros registros.', 409
            )
        return mostrar_error(
            'No se pudo acceder a la base de datos. Revisa la conexión y vuelve a intentar.', 503
        )


def create_app(config=None):
    app = Flask(
        __name__, template_folder='presentacion/vistas', static_folder='presentacion/static'
    )
    app.config.update(
        SECRET_KEY=clave_local(),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        SESSION_REFRESH_EACH_REQUEST=False,
        SESSION_COOKIE_NAME='recursos_rehecho',
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        MAX_CONTENT_LENGTH=1024 * 1024,
        INICIAR_PROCESADOR_VENCIMIENTOS=False,
        WTF_CSRF_ENABLED=True,
    )
    app.config.update(config or {})
    CSRFProtect(app)

    conexion = MySQLConnection(app.config.get('MYSQL_CONFIG'))
    servicios = crear_servicios(conexion)
    app.extensions['servicios'] = servicios

    configurar_seguridad(app, servicios['acceso'])
    registrar_controladores(app, servicios)
    registrar_inicio(app)
    registrar_filtros(app)
    registrar_errores(app)

    if app.config['INICIAR_PROCESADOR_VENCIMIENTOS']:
        app.extensions['detener_vencimientos'] = iniciar_procesador_vencimientos(
            servicios['sanciones'], servicios['reservas']
        )
    return app


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    create_app({'INICIAR_PROCESADOR_VENCIMIENTOS': True}).run(
        host='127.0.0.1', port=int(os.getenv('PORT', '5001'))
    )

