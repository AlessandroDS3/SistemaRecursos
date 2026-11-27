from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from dominio.gestion_prestamos.reserva import ESTADOS_POR_ACCION, ESTADOS_RESERVA
from presentacion.seguridad import requiere_permiso
from presentacion.formularios import recuperar_formulario_tras_error


class ControladorReserva:
    def __init__(self, servicio):
        self.servicio = servicio
        self.blueprint = Blueprint('reservas', __name__, url_prefix='/reservas')
        self.blueprint.context_processor(self._proporcionar_estados_de_reserva)
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
    def _proporcionar_estados_de_reserva():
        return dict(estados_reserva=ESTADOS_RESERVA, estados_por_accion=ESTADOS_POR_ACCION)

    @requiere_permiso('RESERVAS_PROPIAS_GESTIONAR', 'PRESTAMOS_GESTIONAR')
    def consultar_reservas(self):
        gestionar = g.usuario.tiene_permiso('PRESTAMOS_GESTIONAR')
        return render_template(
            'prestamos/vista_reserva.html',
            modo='lista',
            gestionar=gestionar,
            reservas=self.servicio.consultar_reservas(
                None if gestionar else g.usuario.dni, request.args
            ),
        )

    @requiere_permiso('RESERVAS_PROPIAS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self: self._mostrar_formulario_reserva())
    def registrar_reserva(self):
        if request.method == 'POST':
            datos = request.form.to_dict()
            recursos = request.form.getlist('id_recurso')
            cantidades = request.form.getlist('cantidad')
            if cantidades or len(recursos) > 1:
                if len(recursos) != len(cantidades):
                    raise ValueError('Indica una cantidad para cada recurso.')
                datos['recursos'] = list(zip(recursos, cantidades))
            datos['participantes'] = datos.get('participantes', '').replace(',', ' ').split()
            identificador = self.servicio.registrar_reserva(datos, g.usuario.id_usuario)
            flash('Reserva registrada.')
            return redirect(url_for('reservas.consultar_reserva', identificador=identificador))
        return self._mostrar_formulario_reserva()

    def _mostrar_formulario_reserva(self):
        recursos = request.form.getlist('id_recurso')
        cantidades = request.form.getlist('cantidad')
        lineas = [(recurso, cantidades[i] if i < len(cantidades) else '1')
                  for i, recurso in enumerate(recursos[:100])]
        return render_template(
            'prestamos/vista_reserva.html',
            modo='formulario',
            recursos=self.servicio.consultar_recursos_para_reserva(g.usuario.dni),
            lineas=lineas or [(request.args.get('id_recurso', ''), '1')],
            tipo_prestamo=request.form.get('tipo_prestamo', 'INDIVIDUAL'),
            participantes=request.form.get('participantes', ''),
        )

    @requiere_permiso('RESERVAS_PROPIAS_GESTIONAR', 'PRESTAMOS_GESTIONAR')
    def consultar_reserva(self, identificador):
        gestionar = g.usuario.tiene_permiso('PRESTAMOS_GESTIONAR')
        reserva = self.servicio.consultar_reserva(identificador, g.usuario.dni, gestionar)
        recursos_reservados = {bien['id_recurso'] for bien in reserva.get('bienes', [reserva])}
        condiciones = [
            recurso for recurso in self.servicio.consultar_recursos_para_reserva(reserva['dni_persona'])
            if recurso['id_recurso'] in recursos_reservados
        ]
        return render_template(
            'prestamos/vista_reserva.html',
            modo='detalle',
            gestionar=gestionar,
            reserva=reserva,
            condiciones=condiciones,
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def preparar_reserva(self, identificador):
        return self._ejecutar_accion_reserva_y_redirigir(identificador, self.servicio.preparar_reserva)

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def entregar_reserva(self, identificador):
        return self._ejecutar_accion_reserva_y_redirigir(identificador, self.servicio.entregar_reserva)

    @requiere_permiso('RESERVAS_PROPIAS_GESTIONAR', 'PRESTAMOS_GESTIONAR')
    def cancelar_reserva(self, identificador):
        return self._ejecutar_accion_reserva_y_redirigir(identificador, self.servicio.cancelar_reserva)

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def rechazar_reserva(self, identificador):
        return self._ejecutar_accion_reserva_y_redirigir(identificador, self.servicio.rechazar_reserva)

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def expirar_reserva(self, identificador):
        return self._ejecutar_accion_reserva_y_redirigir(identificador, self.servicio.expirar_reserva)

    @recuperar_formulario_tras_error(
        lambda self, identificador, operacion: self.consultar_reserva(identificador)
    )
    def _ejecutar_accion_reserva_y_redirigir(self, identificador, operacion):
        prestamo = operacion(identificador, request.form.to_dict(), g.usuario.id_usuario)
        mensajes = {
            'reservas.preparar_reserva': 'Reserva preparada.',
            'reservas.entregar_reserva': 'Préstamo registrado.',
            'reservas.cancelar_reserva': 'Reserva cancelada.',
            'reservas.rechazar_reserva': 'Reserva rechazada.',
            'reservas.expirar_reserva': 'Reserva vencida.',
        }
        flash(mensajes[request.endpoint])
        if prestamo:
            return redirect(url_for('prestamos.consultar_prestamo', identificador=prestamo))
        return redirect(url_for('reservas.consultar_reserva', identificador=identificador))
