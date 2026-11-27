from datetime import datetime, timezone
from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for
from dominio.compartido.validacion import Conflicto
from presentacion.seguridad import requiere_permiso
from presentacion.navegacion import obtener_url_del_detalle_de_prestamo, obtener_url_de_regreso_a_prestamos
from presentacion.formularios import recuperar_formulario_tras_error


def _volver_a_prestamo_o_solicitudes_de_ampliacion():
    """Vuelve a la ficha del préstamo o a la lista; nunca a una dirección externa."""
    volver = request.form.get('volver', '')
    if volver.startswith('/') and not volver.startswith('//') and '\\' not in volver:
        return volver
    return url_for('ampliaciones.consultar_solicitudes_ampliacion')


class ControladorAmpliacionPrestamo:
    def __init__(self, servicio, prestamos):
        self.servicio, self.prestamos = servicio, prestamos
        self.blueprint = Blueprint('ampliaciones', __name__)
        self.blueprint.add_url_rule(
            '/prestamos/<int:identificador>/detalles/<int:detalle_id>/ampliacion-previa',
            'previsualizar_ampliacion_prestamo',
            self.previsualizar_ampliacion_prestamo,
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
            '/ampliaciones/solicitudes', 'consultar_solicitudes_ampliacion', self.consultar_solicitudes_ampliacion
        )
        self.blueprint.add_url_rule(
            '/ampliaciones/solicitudes/<int:identificador>/aprobar',
            'aprobar_solicitud_ampliacion',
            self.aprobar_solicitud_ampliacion,
            methods=['POST'],
        )
        self.blueprint.add_url_rule(
            '/ampliaciones/solicitudes/<int:identificador>/rechazar',
            'rechazar_solicitud_ampliacion',
            self.rechazar_solicitud_ampliacion,
            methods=['POST'],
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def previsualizar_ampliacion_prestamo(self, identificador, detalle_id):
        try:
            nueva = self.servicio.previsualizar_ampliacion_prestamo(
                identificador, detalle_id, request.args, g.usuario.id_usuario
            )
        except ValueError as error:
            return jsonify(error=str(error)), 409 if isinstance(error, Conflicto) else 400
        return jsonify(fecha=nueva.replace(tzinfo=timezone.utc).isoformat())

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    @recuperar_formulario_tras_error(
        lambda self, identificador, detalle_id: self._mostrar_ficha_del_prestamo(identificador)
    )
    def ampliar_prestamo(self, identificador, detalle_id):
        self.servicio.ampliar_prestamo(
            identificador, detalle_id, request.form.to_dict(), g.usuario.id_usuario
        )
        flash('Plazo ampliado.')
        return redirect(obtener_url_del_detalle_de_prestamo(identificador))

    @requiere_permiso('PRESTAMOS_PROPIOS_CONSULTAR')
    @recuperar_formulario_tras_error(
        lambda self, identificador, detalle_id: self._mostrar_ficha_del_prestamo(identificador, False)
    )
    def solicitar_ampliacion(self, identificador, detalle_id):
        self.servicio.solicitar_ampliacion(
            identificador, detalle_id, request.form.to_dict(), g.usuario.id_usuario
        )
        flash('Solicitud enviada. El encargado la revisará.')
        return redirect(obtener_url_del_detalle_de_prestamo(identificador))

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def consultar_solicitudes_ampliacion(self):
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
    @recuperar_formulario_tras_error(lambda self, identificador: self.consultar_solicitudes_ampliacion())
    def aprobar_solicitud_ampliacion(self, identificador):
        self.servicio.aprobar_solicitud_ampliacion(
            identificador, request.form.to_dict(), g.usuario.id_usuario
        )
        flash('Solicitud aprobada; el plazo se actualizó.')
        return redirect(_volver_a_prestamo_o_solicitudes_de_ampliacion())

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self, identificador: self.consultar_solicitudes_ampliacion())
    def rechazar_solicitud_ampliacion(self, identificador):
        self.servicio.rechazar_solicitud_ampliacion(
            identificador, request.form.to_dict(), g.usuario.id_usuario
        )
        flash('Solicitud rechazada.')
        return redirect(_volver_a_prestamo_o_solicitudes_de_ampliacion())

    def _mostrar_ficha_del_prestamo(self, identificador, gestionar=True):
        return render_template(
            'prestamos/vista_prestamo.html',
            modo='detalle',
            gestionar=gestionar,
            prestamo=self.prestamos.consultar_prestamo(identificador, g.usuario.dni, gestionar),
            solicitudes=self.servicio.consultar_solicitudes_de_ampliacion_del_prestamo(identificador),
            ahora=datetime.now(timezone.utc).replace(tzinfo=None),
            volver=obtener_url_de_regreso_a_prestamos(),
        )
