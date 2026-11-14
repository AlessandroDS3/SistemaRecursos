import os
import secrets
from datetime import timedelta, timezone
from dominio.compartido.validaciones import ConflictoEdicion
from flask import Flask, g, render_template
from mysql.connector import Error
from pathlib import Path
from presentacion.controladores.controlador_acceso import ControladorAcceso
from presentacion.controladores.controlador_ampliacion_prestamo import ControladorAmpliacionPrestamo
from presentacion.controladores.controlador_bien_material import ControladorBienMaterial
from presentacion.controladores.controlador_persona import ControladorPersona
from presentacion.controladores.controlador_politica_prestamo import ControladorPoliticaPrestamo
from presentacion.controladores.controlador_prestamo import ControladorPrestamo
from presentacion.controladores.controlador_recurso import ControladorRecurso
from presentacion.controladores.controlador_reporte import ControladorReporte
from presentacion.controladores.controlador_reserva import ControladorReserva
from presentacion.controladores.controlador_rol import ControladorRol
from presentacion.seguridad import preparar_peticion, requiere_permiso, token_csrf
from repositorio.conexion_mysql import MySQLConnection
from repositorio.repositorio_acceso_sql import RepositorioAccesoSQL
from repositorio.repositorio_bien_material_sql import RepositorioBienMaterialSQL
from repositorio.repositorio_persona_sql import RepositorioPersonaSQL
from repositorio.repositorio_politica_prestamo_sql import RepositorioPoliticaPrestamoSQL
from repositorio.repositorio_prestamo_sql import RepositorioPrestamoSQL
from repositorio.repositorio_recurso_sql import RepositorioRecursoSQL
from repositorio.repositorio_reporte_sql import RepositorioReporteSQL
from repositorio.repositorio_reserva_sql import RepositorioReservaSQL
from repositorio.repositorio_rol_sql import RepositorioRolSQL
from repositorio.repositorio_sancion_sql import RepositorioSancionSQL
from servicios.procesador_vencimientos import iniciar_procesador_vencimientos
from servicios.servicio_acceso import ServicioAplicacionAcceso
from servicios.servicio_ampliacion_prestamo import ServicioAplicacionAmpliacionPrestamo
from servicios.servicio_bien_material import ServicioAplicacionBienMaterial
from servicios.servicio_cuenta import ServicioAplicacionCuenta
from servicios.servicio_persona import ServicioAplicacionPersona
from servicios.servicio_politica_prestamo import ServicioAplicacionPoliticaPrestamo
from servicios.servicio_prestamo import ServicioAplicacionPrestamo
from servicios.servicio_recurso import ServicioAplicacionRecurso
from servicios.servicio_reporte import ServicioAplicacionReporte
from servicios.servicio_reserva import ServicioAplicacionReserva
from servicios.servicio_rol import ServicioAplicacionRol
from servicios.servicio_sancion import ServicioAplicacionSancion
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def obtener_clave_sesion():
    """La clave del entorno tiene prioridad; el desarrollo local conserva la suya."""
    if os.environ.get('FLASK_SECRET_KEY'):
        return os.environ['FLASK_SECRET_KEY']
    archivo = Path(__file__).resolve().parent / 'datos_locales' / 'clave_sesion.txt'
    archivo.parent.mkdir(exist_ok=True)
    try:
        with archivo.open('x', encoding='utf-8') as salida:
            salida.write(secrets.token_hex(32))
    except FileExistsError:
        pass
    return archivo.read_text(encoding='utf-8').strip()


def create_app(config=None, repositorios=None, repositorios_recursos=None):
    app = Flask(
        __name__, template_folder="presentacion/vistas", static_folder="presentacion/static"
    )
    app.config.update(
        SECRET_KEY=(config or {}).get('SECRET_KEY') or obtener_clave_sesion(),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=64 * 1024,
    )
    if config:
        app.config.update(config)
    conexion = MySQLConnection(app.config.get("MYSQL_CONFIG"))
    if repositorios is None:
        personas = RepositorioPersonaSQL(conexion)
        roles = RepositorioRolSQL(conexion)
        usuarios = RepositorioAccesoSQL(conexion)
    else:
        personas, roles, usuarios = repositorios
    acceso = ServicioAplicacionAcceso(usuarios)
    cuentas = ServicioAplicacionCuenta(usuarios, personas, roles)
    servicio_persona = ServicioAplicacionPersona(personas)
    servicio_rol = ServicioAplicacionRol(roles, usuarios)
    app.extensions["acceso"] = acceso
    app.extensions["cuentas"] = cuentas
    recursos, bienes = (
        repositorios_recursos
        if repositorios_recursos is not None
        else (RepositorioRecursoSQL(conexion), RepositorioBienMaterialSQL(conexion))
    )
    servicio_recurso = ServicioAplicacionRecurso(recursos, bienes)
    servicio_bien = ServicioAplicacionBienMaterial(bienes, recursos)
    app.extensions["recursos"] = servicio_recurso
    app.extensions["bienes"] = servicio_bien
    servicio_politica = ServicioAplicacionPoliticaPrestamo(RepositorioPoliticaPrestamoSQL(conexion), recursos)
    servicio_prestamo = ServicioAplicacionPrestamo(
        RepositorioPrestamoSQL(conexion), personas, bienes, recursos
    )
    app.extensions["politicas"] = servicio_politica
    app.extensions["prestamos"] = servicio_prestamo
    servicio_sancion = ServicioAplicacionSancion(RepositorioSancionSQL(conexion))
    app.extensions['sanciones'] = servicio_sancion
    servicio_reserva = ServicioAplicacionReserva(RepositorioReservaSQL(conexion), servicio_prestamo)
    app.extensions["reservas"] = servicio_reserva
    servicio_reporte = ServicioAplicacionReporte(RepositorioReporteSQL(conexion))
    app.extensions['reportes'] = servicio_reporte
    servicio_ampliacion = ServicioAplicacionAmpliacionPrestamo(servicio_prestamo.repositorio)
    app.extensions['ampliaciones'] = servicio_ampliacion

    @app.template_filter("descripcion_permiso")
    def descripcion_permiso(permiso):
        descripcion = permiso.descripcion.replace(" (siguiente corte)", "")
        if permiso.codigo == "RESERVAS_PROPIAS_GESTIONAR":
            return "Solicitar préstamos y gestionar reservas propias"
        return descripcion

    @app.template_filter("fecha_local")
    def fecha_local(fecha):
        if fecha is None:
            return "—"
        try:
            zona = ZoneInfo("America/Lima")
        except ZoneInfoNotFoundError:
            zona = timezone(timedelta(hours=-5))
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
        return fecha.astimezone(zona).strftime("%d/%m/%Y %H:%M")

    app.before_request(preparar_peticion)

    @app.context_processor
    def contexto():
        return {
            "csrf_token": token_csrf,
            "puede": lambda codigo: bool(g.get("usuario") and g.usuario.rol.tiene_permiso(codigo)),
        }

    @app.after_request
    def cabeceras(respuesta):
        respuesta.headers["Cache-Control"] = "no-store"
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        respuesta.headers["X-Frame-Options"] = "DENY"
        return respuesta

    @app.get("/")
    @requiere_permiso()
    def inicio():
        resumen_inicio = {}
        gestionar_prestamos = g.usuario.rol.tiene_permiso("PRESTAMOS_GESTIONAR")
        consultar_prestamos = g.usuario.rol.tiene_permiso("PRESTAMOS_PROPIOS_CONSULTAR")
        if gestionar_prestamos or consultar_prestamos:
            resumen_inicio.update(
                servicio_prestamo.consultar_resumen_prestamos(
                    g.usuario.persona.dni, gestionar=gestionar_prestamos
                )
            )
        if g.usuario.rol.tiene_permiso("CATALOGO_CONSULTAR"):
            resumen_inicio["bienes_disponibles"] = servicio_bien.contar_disponibles()
        return render_template("base.html", resumen_inicio=resumen_inicio)

    app.register_blueprint(ControladorAcceso(acceso).blueprint)
    app.register_blueprint(ControladorPersona(servicio_persona, cuentas).blueprint)
    app.register_blueprint(ControladorRol(servicio_rol).blueprint)
    app.register_blueprint(ControladorRecurso(servicio_recurso, servicio_politica).blueprint)
    app.register_blueprint(ControladorBienMaterial(servicio_bien, servicio_recurso).blueprint)

    app.register_blueprint(ControladorReserva(
        servicio_reserva, servicio_recurso, servicio_politica, servicio_persona
    ).blueprint)
    app.register_blueprint(ControladorPrestamo(servicio_prestamo, servicio_politica, servicio_sancion).blueprint)
    app.register_blueprint(ControladorAmpliacionPrestamo(servicio_ampliacion).blueprint)
    app.register_blueprint(ControladorPoliticaPrestamo(servicio_politica).blueprint)
    app.register_blueprint(ControladorReporte(servicio_reporte).blueprint)

    @app.errorhandler(ConflictoEdicion)
    def mostrar_conflicto(error):
        return render_template("base.html", mensaje_error=str(error)), 409

    @app.errorhandler(ValueError)
    @app.errorhandler(LookupError)
    def mostrar_error_validacion(error):
        codigo = 404 if isinstance(error, LookupError) else 400
        return render_template("base.html", mensaje_error=str(error)), codigo

    @app.errorhandler(Error)
    def mostrar_error_base_datos(error):
        app.logger.exception('No se pudo completar la operación de MySQL.')
        return render_template(
            "base.html",
            mensaje_error="No se pudo completar la operación. Revisa los datos e inténtalo otra vez.",
        ), 500

    @app.errorhandler(400)
    def mostrar_error_formulario(error):
        return render_template("base.html", mensaje_error=error.description), error.code

    @app.errorhandler(PermissionError)
    @app.errorhandler(403)
    def mostrar_error_permiso(error):
        return render_template(
            "base.html", mensaje_error="Tu cuenta no tiene permiso para esta operación."
        ), 403

    if app.config.get('INICIAR_PROCESADOR_VENCIMIENTOS', not app.testing):
        iniciar_procesador_vencimientos(app, servicio_sancion, servicio_reserva)
    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", "5001")))
