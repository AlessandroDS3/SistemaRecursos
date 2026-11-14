from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from presentacion.seguridad import requiere_permiso


class ControladorReserva:
    def __init__(self, servicio):
        self.servicio = servicio
        self.blueprint = Blueprint('reservas', __name__, url_prefix='/reservas')
        self.blueprint.add_url_rule('', 'listar', self.listar)
        self.blueprint.add_url_rule('/nueva', 'nueva', self.nueva, methods=['GET', 'POST'])
        self.blueprint.add_url_rule('/<int:identificador>', 'detalle', self.detalle)
        self.blueprint.add_url_rule(
            '/<int:identificador>/<accion>', 'actuar', self.actuar, methods=['POST']
        )

    @requiere_permiso('RESERVAS_PROPIAS_GESTIONAR', 'PRESTAMOS_GESTIONAR')
    def listar(self):
        gestionar = g.usuario.permite('PRESTAMOS_GESTIONAR')
        return render_template(
            'vista_reserva.html',
            modo='lista',
            gestionar=gestionar,
            reservas=self.servicio.listar(None if gestionar else g.usuario.dni, request.args),
        )

    @requiere_permiso('RESERVAS_PROPIAS_GESTIONAR')
    def nueva(self):
        if request.method == 'POST':
            identificador = self.servicio.registrar(request.form.to_dict(), g.usuario.id_usuario)
            flash('Solicitud registrada. Consulta su estado para recoger el bien.')
            return redirect(url_for('reservas.detalle', identificador=identificador))
        return render_template(
            'vista_reserva.html',
            modo='formulario',
            recursos=self.servicio.opciones(g.usuario.dni),
            seleccionado=request.args.get('id_recurso', ''),
        )

    @requiere_permiso('RESERVAS_PROPIAS_GESTIONAR', 'PRESTAMOS_GESTIONAR')
    def detalle(self, identificador):
        gestionar = g.usuario.permite('PRESTAMOS_GESTIONAR')
        return render_template(
            'vista_reserva.html',
            modo='detalle',
            gestionar=gestionar,
            reserva=self.servicio.consultar(identificador, g.usuario.dni, gestionar),
        )

    @requiere_permiso('RESERVAS_PROPIAS_GESTIONAR', 'PRESTAMOS_GESTIONAR')
    def actuar(self, identificador, accion):
        prestamo = self.servicio.actuar(
            identificador, accion, request.form.to_dict(), g.usuario.id_usuario
        )
        flash('Reserva actualizada.')
        if prestamo:
            return redirect(url_for('prestamos.detalle', identificador=prestamo))
        return redirect(url_for('reservas.detalle', identificador=identificador))
