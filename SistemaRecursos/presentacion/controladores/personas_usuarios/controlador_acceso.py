from flask import Blueprint, g, redirect, render_template, request, session, url_for
from dominio.gestion_personas_usuarios.sesion import AccesoBloqueado
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
            destino = 'cuentas.cambiar_clave_propia' if g.usuario.debe_cambiar_clave else 'inicio'
            return redirect(url_for(destino))
        error, codigo = None, 200
        if request.method == 'POST':
            try:
                cuenta_acceso = self.servicio.autenticar_cuenta(
                    request.form.get('usuario', ''),
                    request.form.get('clave', ''),
                    request.remote_addr or '',
                )
            except AccesoBloqueado as bloqueo:
                cuenta_acceso, error, codigo = None, str(bloqueo), 429
            if cuenta_acceso:
                establecer_sesion(
                    cuenta_acceso, self.servicio.iniciar_sesion(cuenta_acceso.id_usuario)
                )
                destino = (
                    'cuentas.cambiar_clave_propia' if cuenta_acceso.debe_cambiar_clave else 'inicio'
                )
                return redirect(url_for(destino))
            if error is None:
                error, codigo = 'Credenciales incorrectas o cuenta sin acceso.', 401
        return render_template('personas_usuarios/vista_acceso.html', error=error), codigo

    def cerrar_sesion(self):
        self.servicio.cerrar_sesion(session.get('sid'))
        session.clear()
        return redirect(url_for('auth.iniciar_sesion'))
