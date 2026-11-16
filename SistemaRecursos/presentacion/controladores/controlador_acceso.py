from flask import Blueprint, g, redirect, render_template, request, session, url_for
from presentacion.seguridad import establecer_sesion


class ControladorAcceso:
    def __init__(self, servicio):
        self.servicio = servicio
        self.blueprint = Blueprint('auth', __name__)
        self.blueprint.add_url_rule(
            '/login', 'iniciar_sesion', self.iniciar_sesion, methods=['GET', 'POST']
        )
        self.blueprint.add_url_rule(
            '/logout', 'cerrar_sesion', self.cerrar_sesion, methods=['POST']
        )

    def iniciar_sesion(self):
        if g.usuario:
            return redirect(url_for('inicio'))
        error = None
        if request.method == 'POST':
            cuenta_acceso = self.servicio.autenticar_cuenta(
                request.form.get('usuario', ''), request.form.get('clave', '')
            )
            if cuenta_acceso:
                establecer_sesion(cuenta_acceso)
                return redirect(url_for('inicio'))
            error = 'Credenciales incorrectas o cuenta sin acceso.'
        return render_template('vista_acceso.html', error=error)

    def cerrar_sesion(self):
        session.clear()
        return redirect(url_for('auth.iniciar_sesion'))
