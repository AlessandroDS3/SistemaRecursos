from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from presentacion.seguridad import requiere_permiso
from presentacion.navegacion import obtener_url_del_detalle_de_prestamo, obtener_url_de_regreso_a_prestamos
from presentacion.formularios import recuperar_formulario_tras_error


class ControladorSancion:
    def __init__(self, servicio):
        self.servicio = servicio
        self.blueprint = Blueprint('sanciones', __name__, url_prefix='/sanciones')
        self.blueprint.add_url_rule('', 'consultar_sanciones', self.consultar_sanciones)
        self.blueprint.add_url_rule(
            '/<int:identificador>', 'consultar_sancion', self.consultar_sancion
        )
        self.blueprint.add_url_rule(
            '/<int:identificador>/levantar',
            'levantar_sancion',
            self.levantar_sancion,
            methods=['POST'],
        )
        for ruta, nombre, funcion in (
            ('/configuracion', 'guardar_configuracion_sanciones', self.guardar_configuracion_sanciones),
            ('/<int:identificador>/evaluar', 'evaluar_sancion', self.evaluar_sancion),
            ('/<int:identificador>/regularizar', 'regularizar_sancion', self.regularizar_sancion),
            ('/<int:identificador>/anular', 'anular_sancion', self.anular_sancion),
            ('/<int:identificador>/recuperar-original', 'registrar_recuperacion_del_bien_original', self.registrar_recuperacion_del_bien_original),
        ):
            self.blueprint.add_url_rule(ruta, nombre, funcion, methods=['POST'])
        self.blueprint.add_url_rule(
            '/prestamos/<int:prestamo_id>/detalles/<int:detalle_id>',
            'aplicar_sancion_a_bien_prestado', self.aplicar_sancion_a_bien_prestado, methods=['POST'],
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def consultar_sanciones(self):
        estado = request.args.get('estado') or 'ACTIVA'
        consulta = request.values.get('q', '').strip()
        configuracion, version = (
            self.servicio.consultar_configuracion_sanciones() if g.usuario.rol == 'ADMINISTRADOR' else ({}, '')
        )
        return render_template(
            'control/vista_sancion.html',
            modo='lista',
            sanciones=self.servicio.consultar_sanciones(dict(estado=estado, q=consulta)),
            estado_actual=estado,
            consulta=consulta,
            configuracion=configuracion,
            version_configuracion=version,
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def consultar_sancion(self, identificador):
        sancion = self.servicio.consultar_sancion(identificador)
        return render_template(
            'control/vista_sancion.html',
            modo='detalle',
            sancion=sancion,
            volver=obtener_url_de_regreso_a_prestamos(),
            prestamo_url=obtener_url_del_detalle_de_prestamo(sancion['id_prestamo']) + '#devolucion',
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    @recuperar_formulario_tras_error(
        lambda self, identificador: (
            self.consultar_sancion(identificador)
            if request.form.get('origen') == 'prestamo'
            else self.consultar_sanciones()
        )
    )
    def levantar_sancion(self, identificador):
        sancion = (
            self.servicio.consultar_sancion(identificador)
            if request.form.get('origen') == 'prestamo'
            else None
        )
        self.servicio.levantar_sancion(
            identificador, request.form.get('justificacion'), g.usuario.id_usuario
        )
        flash('Sanción levantada.')
        if sancion is not None:
            return redirect(obtener_url_del_detalle_de_prestamo(sancion['id_prestamo']) + '#devolucion')
        return redirect(url_for('sanciones.consultar_sanciones', q=request.form.get('q', '')))

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self: self.consultar_sanciones())
    def guardar_configuracion_sanciones(self):
        self.servicio.guardar_configuracion_sanciones(
            request.form, request.form.get('version'), g.usuario.id_usuario
        )
        flash('Plazos actualizados.')
        return redirect(url_for('sanciones.consultar_sanciones'))

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self, identificador: self.consultar_sancion(identificador))
    def evaluar_sancion(self, identificador):
        self.servicio.evaluar_sancion(identificador, request.form, g.usuario.id_usuario)
        flash('Evaluación registrada.')
        return redirect(url_for('sanciones.consultar_sancion', identificador=identificador))

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self, identificador: self.consultar_sancion(identificador))
    def regularizar_sancion(self, identificador):
        self.servicio.regularizar_sancion(identificador, request.form, g.usuario.id_usuario)
        flash('Regularización aceptada.')
        return redirect(url_for('sanciones.consultar_sancion', identificador=identificador))

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def aplicar_sancion_a_bien_prestado(self, prestamo_id, detalle_id):
        identificador = self.servicio.aplicar_sancion_a_bien_prestado(
            prestamo_id, detalle_id, request.form, g.usuario.id_usuario,
        )
        flash('Sanción registrada.')
        return redirect(url_for('sanciones.consultar_sancion', identificador=identificador))

    @requiere_permiso('USUARIOS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self, identificador: self.consultar_sancion(identificador))
    def anular_sancion(self, identificador):
        self.servicio.anular_sancion(identificador, request.form.get('motivo'), g.usuario.id_usuario)
        flash('Sanción anulada. El préstamo conserva sus pendientes de devolución o regularización.')
        return redirect(url_for('sanciones.consultar_sancion', identificador=identificador))

    @requiere_permiso('USUARIOS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self, identificador: self.consultar_sancion(identificador))
    def registrar_recuperacion_del_bien_original(self, identificador):
        self.servicio.registrar_recuperacion_del_bien_original(identificador, request.form.get('motivo'), g.usuario.id_usuario)
        flash('Original recuperado y enviado a revisión. El bien de reposición se conserva.')
        return redirect(url_for('sanciones.consultar_sancion', identificador=identificador))
