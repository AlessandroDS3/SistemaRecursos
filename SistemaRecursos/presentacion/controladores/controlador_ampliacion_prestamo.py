from flask import Blueprint, g, redirect, render_template, request, url_for, flash

from dominio.gestion_prestamos.ampliacion_prestamo import ConflictoAmpliacionError
from presentacion.seguridad import requiere_permiso
from servicios.servicio_ampliacion_prestamo import ServicioAplicacionAmpliacionPrestamo


class ControladorAmpliacionPrestamo:
    def __init__(self, servicio: ServicioAplicacionAmpliacionPrestamo):
        self.servicio = servicio
        self.blueprint = Blueprint('ampliaciones', __name__, url_prefix='/prestamos')
        for ruta, nombre, metodo in (
            ('/<int:id_prestamo>/detalles/<int:id_detalle>/ampliaciones', 'solicitar_ampliacion', self.solicitar_ampliacion),
            ('/<int:id_prestamo>/ampliaciones/<int:id_ampliacion>/aprobar', 'aprobar_ampliacion', self.aprobar_ampliacion),
            ('/<int:id_prestamo>/ampliaciones/<int:id_ampliacion>/rechazar', 'rechazar_ampliacion', self.rechazar_ampliacion),
        ):
            self.blueprint.add_url_rule(ruta, nombre, metodo, methods=['POST'])

    def _ejecutar(self, id_prestamo, operacion, mensaje):
        try:
            operacion()
        except ConflictoAmpliacionError as error:
            return render_template('base.html', mensaje_error=str(error)), 409
        except ValueError as error:
            return render_template('base.html', mensaje_error=str(error)), 400
        except LookupError as error:
            return render_template('base.html', mensaje_error=str(error)), 404
        flash(mensaje, 'success')
        return redirect(url_for('prestamos.consultar_prestamo', id_prestamo=id_prestamo, _anchor='ampliaciones'))

    @requiere_permiso('AMPLIACIONES_SOLICITAR')
    def solicitar_ampliacion(self, id_prestamo, id_detalle):
        return self._ejecutar(id_prestamo, lambda: self.servicio.solicitar_ampliacion(
            id_prestamo, id_detalle, request.form.get('fecha_limite_nueva'),
            request.form.get('motivo'), g.usuario.persona.dni),
            'Ampliación solicitada. La fecha actual se mantiene hasta que el encargado la apruebe.')

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def aprobar_ampliacion(self, id_prestamo, id_ampliacion):
        return self._ejecutar(id_prestamo, lambda: self.servicio.aprobar_ampliacion(
            id_prestamo, id_ampliacion, g.usuario.id_usuario, request.form.get('observacion', '')),
            'Ampliación aprobada. Se actualizó la fecha de devolución del bien.')

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def rechazar_ampliacion(self, id_prestamo, id_ampliacion):
        return self._ejecutar(id_prestamo, lambda: self.servicio.rechazar_ampliacion(
            id_prestamo, id_ampliacion, g.usuario.id_usuario, request.form.get('observacion', '')),
            'Ampliación rechazada. Se conserva la fecha de devolución anterior.')
