from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from dominio.gestion_prestamos.reserva import ESTADOS_POR_ACCION, ESTADOS_RESERVA
from presentacion.seguridad import requiere_permiso


class ControladorReserva:
    def __init__(self, servicio):
        self.servicio = servicio
        self.blueprint = Blueprint('reservas', __name__, url_prefix='/reservas')
        self.blueprint.context_processor(self._contexto_estados)
        self.blueprint.add_url_rule('', 'consultar_reservas', self.consultar_reservas)
        self.blueprint.add_url_rule(
            '/nueva', 'registrar_reserva', self.registrar_reserva, methods=['GET', 'POST']
        )
        self.blueprint.add_url_rule(
            '/<int:identificador>', 'consultar_reserva', self.consultar_reserva
        )
        for accion, funcion in (
            ('preparar', self.preparar_reserva),
            ('entregar', self.entregar_reserva),
            ('cancelar', self.cancelar_reserva),
            ('rechazar', self.rechazar_reserva),
            ('expirar', self.expirar_reserva),
        ):
            self.blueprint.add_url_rule(
                '/<int:identificador>/' + accion, accion + '_reserva', funcion, methods=['POST']
            )

    @staticmethod
    def _contexto_estados():
        return dict(estados_reserva=ESTADOS_RESERVA, estados_por_accion=ESTADOS_POR_ACCION)

    @requiere_permiso('RESERVAS_PROPIAS_GESTIONAR', 'PRESTAMOS_GESTIONAR')
    def consultar_reservas(self):
        gestionar = g.usuario.permite('PRESTAMOS_GESTIONAR')
        return render_template(
            'vista_reserva.html',
            modo='lista',
            gestionar=gestionar,
            reservas=self.servicio.consultar_reservas(
                None if gestionar else g.usuario.dni, request.args
            ),
        )

    @requiere_permiso('RESERVAS_PROPIAS_GESTIONAR')
    def registrar_reserva(self):
        if request.method == 'POST':
            identificador = self.servicio.registrar_reserva(
                request.form.to_dict(), g.usuario.id_usuario
            )
            flash('Solicitud registrada. Consulta su estado para recoger el bien.')
            return redirect(url_for('reservas.consultar_reserva', identificador=identificador))
        return render_template(
            'vista_reserva.html',
            modo='formulario',
            recursos=self.servicio.consultar_recursos_para_reserva(g.usuario.dni),
            seleccionado=request.args.get('id_recurso', ''),
        )

    @requiere_permiso('RESERVAS_PROPIAS_GESTIONAR', 'PRESTAMOS_GESTIONAR')
    def consultar_reserva(self, identificador):
        gestionar = g.usuario.permite('PRESTAMOS_GESTIONAR')
        return render_template(
            'vista_reserva.html',
            modo='detalle',
            gestionar=gestionar,
            reserva=self.servicio.consultar_reserva(identificador, g.usuario.dni, gestionar),
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def preparar_reserva(self, identificador):
        return self._resolver_reserva(identificador, self.servicio.preparar_reserva)

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def entregar_reserva(self, identificador):
        return self._resolver_reserva(identificador, self.servicio.entregar_reserva)

    @requiere_permiso('RESERVAS_PROPIAS_GESTIONAR', 'PRESTAMOS_GESTIONAR')
    def cancelar_reserva(self, identificador):
        return self._resolver_reserva(identificador, self.servicio.cancelar_reserva)

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def rechazar_reserva(self, identificador):
        return self._resolver_reserva(identificador, self.servicio.rechazar_reserva)

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def expirar_reserva(self, identificador):
        return self._resolver_reserva(identificador, self.servicio.expirar_reserva)

    def _resolver_reserva(self, identificador, operacion):
        prestamo = operacion(identificador, request.form.to_dict(), g.usuario.id_usuario)
        flash('Reserva actualizada.')
        if prestamo:
            return redirect(url_for('prestamos.consultar_prestamo', identificador=prestamo))
        return redirect(url_for('reservas.consultar_reserva', identificador=identificador))
