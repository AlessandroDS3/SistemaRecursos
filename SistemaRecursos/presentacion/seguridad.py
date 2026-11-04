import hmac
import secrets
from functools import wraps
from flask import session, request, abort, redirect, url_for, g, current_app


def token_csrf():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def validar_csrf():
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        esperado = session.get("csrf_token", "")
        recibido = request.form.get("csrf_token", "")
        if (
            not isinstance(esperado, str) or not esperado
            or not hmac.compare_digest(esperado.encode("utf-8"), recibido.encode("utf-8"))
        ):
            abort(400, description="El formulario venció. Recarga la página e inténtalo otra vez.")


def requiere_permiso(codigo=None):
    def decorar(vista):
        @wraps(vista)
        def protegida(*args, **kwargs):
            if not g.usuario:
                return redirect(url_for("auth.login"))
            if codigo and not g.usuario.rol.tiene_permiso(codigo):
                abort(403)
            return vista(*args, **kwargs)

        return protegida

    return decorar


def redirigir_segun_permiso(destino, permiso, **valores):
    # Una operación puede haber cambiado el rol o sus permisos en esta petición.
    usuario = current_app.extensions["acceso"].consultar_usuario_activo(session.get("id_usuario"))
    if usuario is None:
        session.clear()
        return redirect(url_for("auth.login"))
    if usuario.rol.tiene_permiso(permiso):
        return redirect(url_for(destino, **valores))
    return redirect(url_for("inicio"))
