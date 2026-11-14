from flask import Blueprint, g, redirect, render_template, request, session, url_for
from presentacion.seguridad import iniciar_sesion


class ControladorAcceso:
    def __init__(self, servicio):
        self.servicio = servicio
        self.blueprint = Blueprint('auth', __name__)
        self.blueprint.add_url_rule('/login', 'login', self.login, methods=['GET', 'POST'])
        self.blueprint.add_url_rule('/logout', 'logout', self.logout, methods=['POST'])

    def login(self):
        if g.usuario:
            return redirect(url_for('inicio'))
        error = None
        if request.method == 'POST':
            cuenta = self.servicio.autenticar(
                request.form.get('usuario', ''), request.form.get('clave', '')
            )
            if cuenta:
                iniciar_sesion(cuenta)
                return redirect(url_for('inicio'))
            error = 'Credenciales incorrectas o cuenta sin acceso.'
        return render_template('vista_acceso.html', error=error)

    def logout(self):
        session.clear()
        return redirect(url_for('auth.login'))
