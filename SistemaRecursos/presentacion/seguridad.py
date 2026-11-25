"""Sesión web, CSRF y permisos HTTP. No contiene consultas ni reglas de préstamo."""

from functools import wraps
from hmac import compare_digest
from secrets import token_urlsafe
from flask import abort, flash, g, redirect, request, session, url_for


def csrf_token():
    if 'csrf' not in session:
        session['csrf'] = token_urlsafe(32)
    return session['csrf']


def establecer_sesion(cuenta_acceso, token_sesion):
    """Guarda la identidad, el token de la sesión del servidor y renueva el token CSRF."""
    session.clear()
    session.permanent = True
    session.update(
        id_usuario=cuenta_acceso.id_usuario,
        credenciales=cuenta_acceso.version_credenciales,
        sid=token_sesion,
        csrf=token_urlsafe(32),
    )


def requiere_permiso(*permisos):
    def decorar(funcion):
        @wraps(funcion)
        def protegida(*args, **kwargs):
            if g.usuario is None or not any(g.usuario.permite(p) for p in permisos):
                abort(403, description='Tu cuenta no tiene permiso para esta operación.')
            return funcion(*args, **kwargs)

        return protegida

    return decorar


def configurar_seguridad(app, acceso):
    """Instala sesión, permisos y validación CSRF global para POST, PUT, PATCH y DELETE."""
    app.jinja_env.globals['csrf_token'] = csrf_token

    @app.before_request
    def recuperar_sesion():
        g.usuario = None
        identificador = session.get('id_usuario')
        if identificador is not None:
            cuenta_acceso = acceso.consultar_cuenta_activa(identificador)
            if (
                cuenta_acceso
                and compare_digest(
                    cuenta_acceso.version_credenciales, session.get('credenciales', '')
                )
                and acceso.validar_sesion(session.get('sid'), identificador)
            ):
                g.usuario = cuenta_acceso
            else:
                session.clear()
                if request.endpoint not in ('auth.iniciar_sesion', 'static'):
                    flash('Tu sesión terminó. Inicia sesión nuevamente.')
        if request.endpoint not in ('auth.iniciar_sesion', 'static') and g.usuario is None:
            return redirect(url_for('auth.iniciar_sesion'))
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            recibido = request.form.get('csrf_token', '')
            esperado = session.get('csrf', '')
            if (
                not recibido
                or not recibido.isascii()
                or not isinstance(esperado, str)
                or not esperado
                or not esperado.isascii()
                or not compare_digest(recibido, esperado)
            ):
                abort(
                    400, description='El formulario caducó. Recarga la página e inténtalo otra vez.'
                )
        if (
            g.usuario is not None
            and g.usuario.debe_cambiar_clave
            and request.endpoint
            not in (
                'cuentas.cambiar_clave_propia',
                'auth.cerrar_sesion',
                'auth.iniciar_sesion',
                'static',
            )
        ):
            return redirect(url_for('cuentas.cambiar_clave_propia'))
