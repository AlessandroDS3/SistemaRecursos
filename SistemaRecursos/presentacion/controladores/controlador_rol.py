from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from dominio.gestion_personas_usuarios.rol import PERMISOS, ROLES
from presentacion.seguridad import requiere_permiso


class ControladorRol:
    def __init__(self, servicio, cuentas):
        self.servicio, self.cuentas = servicio, cuentas
        self.blueprint = Blueprint('roles', __name__, url_prefix='/roles')
        self.blueprint.add_url_rule('', 'listar', self.listar, methods=['GET'])
        self.blueprint.add_url_rule('/permisos', 'guardar', self.guardar, methods=['POST'])
        self.blueprint.add_url_rule('/asignar', 'asignar', self.asignar, methods=['POST'])

    @requiere_permiso('ROLES_CONSULTAR')
    def listar(self):
        matriz, version = self.servicio.consultar()
        return render_template(
            'vista_rol.html',
            matriz=matriz,
            version=version,
            roles=ROLES,
            permisos=PERMISOS,
            cuentas=self.cuentas.buscar(request.args.get('q', '')),
        )

    @requiere_permiso('ROLES_GESTIONAR')
    def guardar(self):
        matriz = {rol: request.form.getlist('permisos_' + rol) for rol in ROLES}
        self.servicio.guardar(matriz, request.form.get('version'), g.usuario.id_usuario)
        flash('Permisos actualizados.')
        return redirect(url_for('roles.listar'))

    @requiere_permiso('ROLES_GESTIONAR')
    def asignar(self):
        self.cuentas.asignar_rol(
            request.form.get('dni'), request.form.get('rol'), g.usuario.id_usuario
        )
        flash('Rol asignado.')
        return redirect(url_for('roles.listar'))
