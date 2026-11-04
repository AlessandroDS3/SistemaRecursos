from __future__ import annotations
from servicios.servicio_rol import ServicioAplicacionRol
from flask import Blueprint, request, g
from mysql.connector import IntegrityError
from presentacion.formularios import error_formulario
from presentacion.seguridad import requiere_permiso, redirigir_segun_permiso
from presentacion.vistas.vista_rol import VistaRol


class ControladorRol:
    def __init__(self, servicio: ServicioAplicacionRol):
        self.servicio: ServicioAplicacionRol = servicio
        self.vista = VistaRol()
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
        return self.vista.mostrar_consulta(
            self.servicio.consultar_roles(),
            self.servicio.consultar_permisos(),
            cuentas=self.servicio.consultar_cuentas_para_roles(termino), termino=termino, error=error,
        )

    @requiere_permiso("ROLES_GESTIONAR")
    def actualizar_matriz_permisos(self):
        self.servicio.actualizar_matriz_permisos(request.form)
        self.vista.mostrar_mensaje("Permisos de los roles actualizados.")
        return redirigir_segun_permiso("roles.consultar_roles", "ROLES_CONSULTAR")

    @requiere_permiso("ROLES_GESTIONAR")
    @requiere_permiso("ROLES_CONSULTAR")
    def actualizar_rol_cuenta(self, dni):
        try:
            self.servicio.actualizar_rol_cuenta(dni, request.form.get("id_rol"), g.usuario.id_usuario)
        except LookupError as error:
            return self._mostrar_consulta(error=str(error))
        except (ValueError, IntegrityError) as error:
            return self._mostrar_consulta(error=error_formulario(error, "No se pudo actualizar el rol de esta cuenta."))
        self.vista.mostrar_mensaje("Rol de la cuenta actualizado.")
        return redirigir_segun_permiso("roles.consultar_roles", "ROLES_CONSULTAR", q=dni, _anchor="asignar-roles")
