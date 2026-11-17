from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from presentacion.seguridad import requiere_permiso


class ControladorSancion:
    def __init__(self, servicio):
        self.servicio = servicio
        self.blueprint = Blueprint('sanciones', __name__, url_prefix='/sanciones')
        self.blueprint.add_url_rule('', 'consultar_sanciones', self.consultar_sanciones)
        self.blueprint.add_url_rule(
            '/<int:identificador>/levantar',
            'levantar_sancion',
            self.levantar_sancion,
            methods=['POST'],
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def consultar_sanciones(self):
        estado = request.args.get('estado') or 'ACTIVA'
        consulta = request.args.get('q', '').strip()
        return render_template(
            'vista_sancion.html',
            sanciones=self.servicio.consultar_sanciones(dict(estado=estado, q=consulta)),
            estado_actual=estado,
            consulta=consulta,
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def levantar_sancion(self, identificador):
        self.servicio.levantar_sancion(
            identificador, request.form.get('justificacion'), g.usuario.id_usuario
        )
        flash('Sanción levantada para todos los participantes del préstamo.')
        return redirect(url_for('sanciones.consultar_sanciones', q=request.form.get('q', '')))
