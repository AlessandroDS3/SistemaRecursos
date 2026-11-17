from flask import Blueprint, flash, g, redirect, request
from presentacion.seguridad import requiere_permiso
from presentacion.navegacion import detalle_prestamo


class ControladorAmpliacionPrestamo:
    def __init__(self, servicio):
        self.servicio = servicio
        self.blueprint = Blueprint('ampliaciones', __name__)
        self.blueprint.add_url_rule(
            '/prestamos/<int:identificador>/detalles/<int:detalle_id>/ampliar',
            'ampliar_prestamo',
            self.ampliar_prestamo,
            methods=['POST'],
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def ampliar_prestamo(self, identificador, detalle_id):
        self.servicio.ampliar_prestamo(
            identificador, detalle_id, request.form.to_dict(), g.usuario.id_usuario
        )
        flash('Plazo ampliado.')
        return redirect(detalle_prestamo(identificador))
