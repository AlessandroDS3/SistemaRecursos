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

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def consultar_sanciones(self):
        estado = request.args.get('estado') or 'ACTIVA'
        consulta = request.values.get('q', '').strip()
        return render_template(
            'vista_sancion.html',
            modo='lista',
            sanciones=self.servicio.consultar_sanciones(dict(estado=estado, q=consulta)),
            estado_actual=estado,
            consulta=consulta,
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
        flash('Sanción levantada para todos los participantes del préstamo.')
        if sancion is not None:
            return redirect(detalle_prestamo(sancion['id_prestamo']) + '#devolucion')
        return redirect(url_for('sanciones.consultar_sanciones', q=request.form.get('q', '')))
