from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from dominio.gestion_personas_usuarios.rol import PERMISOS, ROLES
from presentacion.seguridad import requiere_permiso
from presentacion.formularios import recuperar_formulario


class ControladorRol:
    def __init__(self, servicio, cuentas):
        self.servicio, self.cuentas = servicio, cuentas
        self.blueprint = Blueprint('roles', __name__, url_prefix='/roles')
        self.blueprint.add_url_rule('', 'consultar_roles', self.consultar_roles, methods=['GET'])
        self.blueprint.add_url_rule(
            '/asignar', 'asignar_rol_cuenta', self.asignar_rol_cuenta, methods=['POST']
        )

    @requiere_permiso('ROLES_CONSULTAR')
    def consultar_roles(self):
        matriz = self.servicio.consultar_matriz_permisos()
        busqueda = (request.args.get('q') or request.form.get('dni', '')).strip()
        return render_template(
            'personas_usuarios/vista_rol.html',
            matriz=matriz,
            roles=ROLES,
            permisos=PERMISOS,
            cuentas=self.cuentas.buscar_cuentas(busqueda) if len(busqueda) >= 2 else [],
        )

    @requiere_permiso('ROLES_GESTIONAR')
    @recuperar_formulario(lambda self: self.consultar_roles())
    def asignar_rol_cuenta(self):
        self.cuentas.asignar_rol_cuenta(
            request.form.get('dni'), request.form.get('rol'), g.usuario.id_usuario
        )
        flash('Rol asignado.')
        return redirect(url_for('roles.consultar_roles'))
