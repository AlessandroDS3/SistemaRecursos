from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from dominio.gestion_personas_usuarios.rol import PERMISOS, ROLES
from presentacion.seguridad import requiere_permiso


class ControladorRol:
    def __init__(self, servicio, cuentas):
        self.servicio, self.cuentas = servicio, cuentas
        self.blueprint = Blueprint('roles', __name__, url_prefix='/roles')
        self.blueprint.add_url_rule('', 'consultar_roles', self.consultar_roles, methods=['GET'])
        self.blueprint.add_url_rule(
            '/permisos', 'guardar_matriz_permisos', self.guardar_matriz_permisos, methods=['POST']
        )
        self.blueprint.add_url_rule(
            '/asignar', 'asignar_rol_cuenta', self.asignar_rol_cuenta, methods=['POST']
        )

    @requiere_permiso('ROLES_CONSULTAR')
    def consultar_roles(self):
        matriz, version = self.servicio.consultar_matriz_permisos()
        busqueda = request.args.get('q', '').strip()
        return render_template(
            'vista_rol.html',
            matriz=matriz,
            version=version,
            roles=ROLES,
            permisos=PERMISOS,
            cuentas=self.cuentas.buscar_cuentas(busqueda) if len(busqueda) >= 2 else [],
        )

    @requiere_permiso('ROLES_GESTIONAR')
    def guardar_matriz_permisos(self):
        matriz = {rol: request.form.getlist('permisos_' + rol) for rol in ROLES}
        self.servicio.guardar_matriz_permisos(
            matriz, request.form.get('version'), g.usuario.id_usuario
        )
        flash('Permisos actualizados.')
        return redirect(url_for('roles.consultar_roles'))

    @requiere_permiso('ROLES_GESTIONAR')
    def asignar_rol_cuenta(self):
        self.cuentas.asignar_rol_cuenta(
            request.form.get('dni'), request.form.get('rol'), g.usuario.id_usuario
        )
        flash('Rol asignado.')
        return redirect(url_for('roles.consultar_roles'))
