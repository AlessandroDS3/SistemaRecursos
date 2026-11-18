from datetime import datetime, timezone
from flask import Blueprint, flash, g, jsonify, redirect, render_template, request
from dominio.compartido.validacion import Conflicto
from presentacion.seguridad import requiere_permiso
from presentacion.navegacion import detalle_prestamo, regreso_prestamos
from presentacion.formularios import recuperar_formulario


class ControladorAmpliacionPrestamo:
    def __init__(self, servicio, prestamos):
        self.servicio, self.prestamos = servicio, prestamos
        self.blueprint = Blueprint('ampliaciones', __name__)
        self.blueprint.add_url_rule(
            '/prestamos/<int:identificador>/detalles/<int:detalle_id>/ampliacion-previa',
            'consultar_ampliacion_prestamo',
            self.consultar_ampliacion_prestamo,
        )
        self.blueprint.add_url_rule(
            '/prestamos/<int:identificador>/detalles/<int:detalle_id>/ampliar',
            'ampliar_prestamo',
            self.ampliar_prestamo,
            methods=['POST'],
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def consultar_ampliacion_prestamo(self, identificador, detalle_id):
        try:
            nueva = self.servicio.consultar_ampliacion_prestamo(
                identificador, detalle_id, request.args, g.usuario.id_usuario
            )
        except ValueError as error:
            return jsonify(error=str(error)), 409 if isinstance(error, Conflicto) else 400
        return jsonify(fecha=nueva.replace(tzinfo=timezone.utc).isoformat())

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    @recuperar_formulario(
        lambda self, identificador, detalle_id: self._mostrar_prestamo(identificador)
    )
    def ampliar_prestamo(self, identificador, detalle_id):
        self.servicio.ampliar_prestamo(
            identificador, detalle_id, request.form.to_dict(), g.usuario.id_usuario
        )
        flash('Plazo ampliado.')
        return redirect(detalle_prestamo(identificador))

    def _mostrar_prestamo(self, identificador):
        return render_template(
            'vista_prestamo.html',
            modo='detalle',
            gestionar=True,
            prestamo=self.prestamos.consultar_prestamo(identificador, g.usuario.dni, True),
            ahora=datetime.now(timezone.utc).replace(tzinfo=None),
            volver=regreso_prestamos(),
        )
