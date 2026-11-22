from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from presentacion.seguridad import requiere_permiso
from presentacion.navegacion import detalle_prestamo, regreso_prestamos
from presentacion.formularios import recuperar_formulario


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
            ('/configuracion', 'guardar_configuracion', self.guardar_configuracion),
            ('/<int:identificador>/evaluar', 'evaluar_sancion', self.evaluar_sancion),
            ('/<int:identificador>/regularizar', 'regularizar_sancion', self.regularizar_sancion),
        ):
            self.blueprint.add_url_rule(ruta, nombre, funcion, methods=['POST'])
        self.blueprint.add_url_rule(
            '/prestamos/<int:prestamo_id>/detalles/<int:detalle_id>',
            'registrar_sancion_detalle', self.registrar_sancion_detalle, methods=['POST'],
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def consultar_sanciones(self):
        estado = request.args.get('estado') or 'ACTIVA'
        consulta = request.values.get('q', '').strip()
        configuracion, version = (
            self.servicio.consultar_configuracion() if g.usuario.rol == 'ADMINISTRADOR' else ({}, '')
        )
        return render_template(
            'vista_sancion.html',
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
            'vista_sancion.html',
            modo='detalle',
            sancion=sancion,
            volver=regreso_prestamos(),
            prestamo_url=detalle_prestamo(sancion['id_prestamo']) + '#devolucion',
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    @recuperar_formulario(
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
        flash('Sanción levantada. Las demás sanciones y pendientes se conservan.')
        if sancion is not None:
            return redirect(detalle_prestamo(sancion['id_prestamo']) + '#devolucion')
        return redirect(url_for('sanciones.consultar_sanciones', q=request.form.get('q', '')))

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    @recuperar_formulario(lambda self: self.consultar_sanciones())
    def guardar_configuracion(self):
        self.servicio.guardar_configuracion(request.form, request.form.get('version'), g.usuario.id_usuario)
        flash('Plazos actualizados; las sanciones existentes conservan sus valores.')
        return redirect(url_for('sanciones.consultar_sanciones'))

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    @recuperar_formulario(lambda self, identificador: self.consultar_sancion(identificador))
    def evaluar_sancion(self, identificador):
        self.servicio.evaluar_sancion(identificador, request.form, g.usuario.id_usuario)
        flash('Evaluación registrada en el historial de la sanción.')
        return redirect(url_for('sanciones.consultar_sancion', identificador=identificador))

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    @recuperar_formulario(lambda self, identificador: self.consultar_sancion(identificador))
    def regularizar_sancion(self, identificador):
        self.servicio.regularizar_sancion(identificador, request.form, g.usuario.id_usuario)
        flash('Regularización aceptada. El plazo de sanción continúa hasta su cumplimiento.')
        return redirect(url_for('sanciones.consultar_sancion', identificador=identificador))

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def registrar_sancion_detalle(self, prestamo_id, detalle_id):
        identificador = self.servicio.registrar_sancion_detalle(
            prestamo_id, detalle_id, request.form, g.usuario.id_usuario,
        )
        flash('Falta evaluada y sanción registrada.')
        return redirect(url_for('sanciones.consultar_sancion', identificador=identificador))
