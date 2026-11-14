"""Sesión web, CSRF y permisos HTTP. No contiene consultas ni reglas de préstamo."""

from functools import wraps
from hmac import compare_digest
from secrets import token_urlsafe
from time import time
from flask import abort, g, redirect, request, session, url_for


def csrf_token():
    if 'csrf' not in session:
        session['csrf'] = token_urlsafe(32)
    return session['csrf']


def iniciar_sesion(cuenta):
    session.clear()
    session.permanent = True
    session.update(
        id_usuario=cuenta.id_usuario,
        credenciales=cuenta.version_credenciales,
        iniciada=time(),
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
    app.jinja_env.globals['csrf_token'] = csrf_token

    @app.before_request
    def recuperar_sesion():
        g.usuario = None
        identificador = session.get('id_usuario')
        if identificador is not None:
            iniciada = session.get('iniciada', 0)
            cuenta = acceso.recuperar(identificador) if 0 <= time() - iniciada < 8 * 3600 else None
            if (
                cuenta
                and cuenta.puede_acceder()
                and compare_digest(cuenta.version_credenciales, session.get('credenciales', ''))
            ):
                g.usuario = cuenta
            else:
                session.clear()
        if request.endpoint not in ('auth.login', 'static') and g.usuario is None:
            return redirect(url_for('auth.login'))
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            recibido = request.form.get('csrf_token', '')
            esperado = session.get('csrf', '')
            if not recibido or not esperado or not compare_digest(recibido, esperado):
                abort(
                    400, description='El formulario caducó. Recarga la página e inténtalo otra vez.'
                )
