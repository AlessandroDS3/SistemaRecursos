from flask import Blueprint, g, redirect, render_template, request, url_for, flash

from dominio.gestion_prestamos.ampliacion_prestamo import ConflictoAmpliacionError
from presentacion.seguridad import requiere_permiso
from servicios.servicio_ampliacion_prestamo import ServicioAplicacionAmpliacionPrestamo


class ControladorAmpliacionPrestamo:
    def __init__(self, servicio: ServicioAplicacionAmpliacionPrestamo):
        self.servicio = servicio
        self.blueprint = Blueprint('ampliaciones', __name__, url_prefix='/prestamos')
        self.blueprint.add_url_rule('/<int:id_prestamo>/detalles/<int:id_detalle>/ampliar',
                                    'ampliar_plazo', self.ampliar_plazo, methods=['POST'])

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def ampliar_plazo(self, id_prestamo, id_detalle):
        try:
            self.servicio.ampliar_plazo(
                id_prestamo, id_detalle, request.form.get('cantidad'), request.form.get('unidad'),
                request.form.get('fecha_actual'), g.usuario.id_usuario, request.form.get('motivo', ''))
        except ConflictoAmpliacionError as error:
            return render_template('base.html', mensaje_error=str(error)), 409
        except ValueError as error:
            return render_template('base.html', mensaje_error=str(error)), 400
        except LookupError as error:
            return render_template('base.html', mensaje_error=str(error)), 404
        flash('Plazo ampliado. La nueva fecha de devolución ya está vigente.', 'success')
        return redirect(url_for('prestamos.consultar_prestamo', id_prestamo=id_prestamo, _anchor='ampliaciones'))
