from __future__ import annotations
from servicios.servicio_acceso import ServicioAplicacionAcceso
from flask import Blueprint, render_template, request, redirect, url_for, session, g, current_app


class ControladorAcceso:
    def __init__(self, servicio: ServicioAplicacionAcceso):
        self.servicio: ServicioAplicacionAcceso = servicio
        self.blueprint = Blueprint("auth", __name__)
        self.blueprint.add_url_rule("/login", "login", self.login, methods=["GET", "POST"])
        self.blueprint.add_url_rule("/logout", "logout", self.logout, methods=["POST"])

    def login(self):
        if g.get("usuario") is not None:
            return redirect(url_for("inicio"))
        if request.method == "POST":
            cuenta = self.servicio.autenticar(
                request.form.get("usuario", ""), request.form.get("clave", ""), request.remote_addr or "local"
            )
            if cuenta is None:
                mensaje = "Credenciales incorrectas o cuenta sin acceso."
                formulario = render_template("vista_acceso.html", error=mensaje)
                return formulario
            session.clear()
            session["token_acceso"] = self.servicio.abrir_sesion(
                cuenta, int(current_app.permanent_session_lifetime.total_seconds())
            )
            session["id_usuario"] = cuenta.id_usuario
            session["version_credenciales"] = self.servicio.version_credenciales(cuenta)
            return redirect(url_for("inicio"))
        return render_template("vista_acceso.html")

    def logout(self):
        self.servicio.cerrar_sesion(session.get("token_acceso"))
        session.clear()
        return redirect(url_for("auth.login"))
