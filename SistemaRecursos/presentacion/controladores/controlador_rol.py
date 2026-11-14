from __future__ import annotations
from dominio.validaciones import version_matriz
from flask import Blueprint, flash, g, render_template, request
from mysql.connector import IntegrityError
from presentacion.formularios import error_formulario
from presentacion.seguridad import redirigir_segun_permiso, requiere_permiso
from servicios.servicio_rol import ServicioAplicacionRol


class ControladorRol:
    def __init__(self, servicio: ServicioAplicacionRol):
        self.servicio: ServicioAplicacionRol = servicio
        self.blueprint = Blueprint("roles", __name__, url_prefix="/roles")
        self.blueprint.add_url_rule("", "consultar_roles", self.consultar_roles, methods=["GET"])
        self.blueprint.add_url_rule("/cuentas/<string:dni>/rol", "actualizar_rol_cuenta", self.actualizar_rol_cuenta, methods=["POST"])
        self.blueprint.add_url_rule(
            "/permisos", "actualizar_matriz_permisos", self.actualizar_matriz_permisos, methods=["POST"]
        )

    @requiere_permiso("ROLES_CONSULTAR")
    def consultar_roles(self):
        return self._mostrar_consulta()

    def _mostrar_consulta(self, error=None):
        termino = request.form.get("q", "") if request.method == "POST" else request.args.get("q", "")
        return self._renderizar_consulta(
            self.servicio.consultar_roles(),
            self.servicio.consultar_permisos(),
            cuentas=self.servicio.consultar_cuentas_para_roles(termino), termino=termino, error=error,
        )

    @requiere_permiso("ROLES_GESTIONAR")
    def actualizar_matriz_permisos(self):
        datos = dict(request.form)
        for campo in request.form:
            if campo.startswith('permisos_'):
                datos[campo] = request.form.getlist(campo)
        self.servicio.actualizar_matriz_permisos(datos)
        self._renderizar_mensaje("Permisos de los roles actualizados.")
        return redirigir_segun_permiso("roles.consultar_roles", "ROLES_CONSULTAR")

    @requiere_permiso("ROLES_GESTIONAR")
    @requiere_permiso("ROLES_CONSULTAR")
    def actualizar_rol_cuenta(self, dni):
        try:
            self.servicio.actualizar_rol_cuenta(dni, request.form.get("nombre_rol"), g.usuario.id_usuario)
        except LookupError as error:
            return self._mostrar_consulta(error=str(error))
        except (ValueError, IntegrityError) as error:
            return self._mostrar_consulta(error=error_formulario(error, "No se pudo actualizar el rol de esta cuenta."))
        self._renderizar_mensaje("Rol de la cuenta actualizado.")
        return redirigir_segun_permiso("roles.consultar_roles", "ROLES_CONSULTAR", q=dni, _anchor="asignar-roles")

    def _renderizar_consulta(self, roles, permisos, cuentas=None, termino="", error=None):
        return render_template(
            "vista_rol.html", roles=roles, permisos=permisos,
            cuentas=cuentas or [], termino=termino, error=error, version=version_matriz(roles, permisos)
        )

    def _renderizar_mensaje(self, mensaje):
        flash(mensaje, "success")
