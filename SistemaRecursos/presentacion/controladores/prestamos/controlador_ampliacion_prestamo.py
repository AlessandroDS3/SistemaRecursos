from datetime import datetime, timezone
from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for
from dominio.compartido.validacion import Conflicto
from presentacion.seguridad import requiere_permiso
from presentacion.navegacion import detalle_prestamo, regreso_prestamos
from presentacion.formularios import recuperar_formulario


def _regreso_solicitudes():
    """Vuelve a la ficha del préstamo o a la lista; nunca a una dirección externa."""
    volver = request.form.get('volver', '')
    if volver.startswith('/') and not volver.startswith('//') and '\\' not in volver:
        return volver
    return url_for('ampliaciones.consultar_solicitudes')


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
        self.blueprint.add_url_rule(
            '/prestamos/<int:identificador>/detalles/<int:detalle_id>/solicitar-ampliacion',
            'solicitar_ampliacion',
            self.solicitar_ampliacion,
            methods=['POST'],
        )
        self.blueprint.add_url_rule(
            '/ampliaciones/solicitudes', 'consultar_solicitudes', self.consultar_solicitudes
        )
        self.blueprint.add_url_rule(
            '/ampliaciones/solicitudes/<int:identificador>/aprobar',
            'aprobar_solicitud',
            self.aprobar_solicitud,
            methods=['POST'],
        )
        self.blueprint.add_url_rule(
            '/ampliaciones/solicitudes/<int:identificador>/rechazar',
            'rechazar_solicitud',
            self.rechazar_solicitud,
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

    @requiere_permiso('PRESTAMOS_PROPIOS_CONSULTAR')
    @recuperar_formulario(
        lambda self, identificador, detalle_id: self._mostrar_prestamo(identificador, False)
    )
    def solicitar_ampliacion(self, identificador, detalle_id):
        self.servicio.solicitar_ampliacion(
            identificador, detalle_id, request.form.to_dict(), g.usuario.id_usuario
        )
        flash('Solicitud enviada. El encargado la revisará.')
        return redirect(detalle_prestamo(identificador))

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def consultar_solicitudes(self):
        estado = request.args.get('estado', 'PENDIENTE')
        if estado not in ('PENDIENTE', 'APROBADA', 'RECHAZADA', ''):
            estado = 'PENDIENTE'
        return render_template(
            'prestamos/vista_solicitudes_ampliacion.html',
            solicitudes=self.servicio.consultar_solicitudes_ampliacion(estado),
            estado=estado,
            ahora=datetime.now(timezone.utc).replace(tzinfo=None),
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    @recuperar_formulario(lambda self, identificador: self.consultar_solicitudes())
    def aprobar_solicitud(self, identificador):
        self.servicio.aprobar_solicitud_ampliacion(
            identificador, request.form.to_dict(), g.usuario.id_usuario
        )
        flash('Solicitud aprobada; el plazo se actualizó.')
        return redirect(_regreso_solicitudes())

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    @recuperar_formulario(lambda self, identificador: self.consultar_solicitudes())
    def rechazar_solicitud(self, identificador):
        self.servicio.rechazar_solicitud_ampliacion(
            identificador, request.form.to_dict(), g.usuario.id_usuario
        )
        flash('Solicitud rechazada.')
        return redirect(_regreso_solicitudes())

    def _mostrar_prestamo(self, identificador, gestionar=True):
        return render_template(
            'prestamos/vista_prestamo.html',
            modo='detalle',
            gestionar=gestionar,
            prestamo=self.prestamos.consultar_prestamo(identificador, g.usuario.dni, gestionar),
            solicitudes=self.servicio.consultar_solicitudes_prestamo(identificador),
            ahora=datetime.now(timezone.utc).replace(tzinfo=None),
            volver=regreso_prestamos(),
        )
