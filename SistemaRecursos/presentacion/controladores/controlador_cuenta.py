from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from presentacion.seguridad import requiere_permiso


class ControladorCuenta:
    def __init__(self, servicio):
        self.servicio = servicio
        self.blueprint = Blueprint('cuentas', __name__, url_prefix='/cuentas')
        self.blueprint.add_url_rule(
            '/<documento>/nueva', 'nueva', self.nueva, methods=['GET', 'POST']
        )
        self.blueprint.add_url_rule(
            '/<documento>/editar', 'editar', self.editar, methods=['GET', 'POST']
        )

    @requiere_permiso('USUARIOS_GESTIONAR')
    def nueva(self, documento):
        if request.method == 'POST':
            self.servicio.crear(
                documento,
                request.form.get('nombre_usuario'),
                request.form.get('clave'),
                g.usuario.id_usuario,
            )
            flash('Cuenta creada con el rol Usuario.')
            return redirect(url_for('personas.detalle', documento=documento))
        return render_template('vista_cuenta.html', documento=documento, cuenta={}, nueva=True)

    @requiere_permiso('USUARIOS_GESTIONAR')
    def editar(self, documento):
        cuenta = self.servicio.consultar(documento)
        if request.method == 'POST':
            self.servicio.actualizar(documento, request.form.to_dict(), g.usuario.id_usuario)
            flash('Cuenta actualizada.')
            return redirect(url_for('personas.detalle', documento=documento))
        return render_template('vista_cuenta.html', documento=documento, cuenta=cuenta, nueva=False)
