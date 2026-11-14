from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from presentacion.seguridad import requiere_permiso


class ControladorSancion:
    def __init__(self, servicio):
        self.servicio = servicio
        self.blueprint = Blueprint('sanciones', __name__, url_prefix='/sanciones')
        self.blueprint.add_url_rule('', 'listar', self.listar)
        self.blueprint.add_url_rule(
            '/<int:identificador>/levantar', 'levantar', self.levantar, methods=['POST']
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def listar(self):
        return render_template('vista_sancion.html', sanciones=self.servicio.listar())

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def levantar(self, identificador):
        self.servicio.levantar(
            identificador, request.form.get('justificacion'), g.usuario.id_usuario
        )
        flash('Sanción levantada para todos los participantes del préstamo.')
        return redirect(url_for('sanciones.listar'))
