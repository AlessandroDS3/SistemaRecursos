from flask import Blueprint, flash, g, redirect, request, url_for
from presentacion.seguridad import requiere_permiso


class ControladorAmpliacionPrestamo:
    def __init__(self, servicio):
        self.servicio = servicio
        self.blueprint = Blueprint('ampliaciones', __name__)
        self.blueprint.add_url_rule(
            '/prestamos/<int:identificador>/detalles/<int:detalle_id>/ampliar',
            'ampliar',
            self.ampliar,
            methods=['POST'],
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def ampliar(self, identificador, detalle_id):
        self.servicio.ampliar(
            identificador, detalle_id, request.form.to_dict(), g.usuario.id_usuario
        )
        flash('Plazo ampliado.')
        return redirect(url_for('prestamos.detalle', identificador=identificador))
