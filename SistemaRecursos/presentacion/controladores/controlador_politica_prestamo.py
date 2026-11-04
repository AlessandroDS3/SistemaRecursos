from __future__ import annotations
from servicios.servicio_politica_prestamo import ServicioAplicacionPoliticaPrestamo
from mysql.connector import IntegrityError
from presentacion.formularios import error_formulario
from flask import Blueprint, request, redirect, url_for, g
from dominio.gestion_personas_usuarios.nombre_rol import NombreRol
from presentacion.seguridad import requiere_permiso
from presentacion.vistas.vista_politica_prestamo import VistaPoliticaPrestamo


class ControladorPoliticaPrestamo:
    def __init__(self, servicio: ServicioAplicacionPoliticaPrestamo):
        self.servicio: ServicioAplicacionPoliticaPrestamo = servicio
        self.vista = VistaPoliticaPrestamo()
        self.blueprint = Blueprint("politicas", __name__, url_prefix="/politicas")
        self.blueprint.add_url_rule("/limites", "actualizar_limites_articulos", self.actualizar_limites_articulos, methods=["POST"])
        self.blueprint.add_url_rule("/horario", "actualizar_horario_atencion", self.actualizar_horario_atencion, methods=["POST"])
        self.blueprint.add_url_rule("/vencimientos", "actualizar_vencimientos", self.actualizar_vencimientos, methods=["POST"])
        self.blueprint.add_url_rule("", "consultar_politicas", self.consultar_politicas, methods=["GET"])
        self.blueprint.add_url_rule("", "registrar_politica", self.registrar_politica, methods=["POST"])
        self.blueprint.add_url_rule("/<int:id_politica>/editar", "mostrar_edicion_politica", self.mostrar_edicion_politica, methods=["GET"])
        self.blueprint.add_url_rule(
            "/<int:id_politica>/editar", "actualizar_politica", self.actualizar_politica, methods=["POST"]
        )
        self.blueprint.add_url_rule(
            "/<int:id_politica>/eliminar", "eliminar_politica", self.eliminar_politica, methods=["POST"]
        )

    @requiere_permiso("POLITICAS_GESTIONAR")
    def registrar_politica(self):
        try:
            self.servicio.registrar_politica(request.form)
        except (ValueError, IntegrityError) as error:
            return self._mostrar_error_politica(error)
        self.vista.mostrar_mensaje("Política guardada. Ya puede aplicarse a nuevas entregas.")
        return redirect(url_for("politicas.consultar_politicas", _anchor=f"politica-categoria-{request.form.get('id_categoria_ref', '')}"))

    @requiere_permiso("POLITICAS_GESTIONAR")
    def consultar_politicas(self):
        return self._mostrar_consulta()

    @requiere_permiso('POLITICAS_GESTIONAR')
    def mostrar_edicion_politica(self, id_politica):
        politica = self.servicio.consultar_politica(id_politica)
        return redirect(url_for("politicas.consultar_politicas", _anchor=f"politica-categoria-{politica.id_categoria_ref}"))

    @requiere_permiso('POLITICAS_GESTIONAR')
    def actualizar_politica(self, id_politica):
        self.servicio.consultar_politica(id_politica)
        try:
            self.servicio.actualizar_politica(dict(request.form, id_politica=id_politica))
        except (ValueError, IntegrityError) as error:
            return self._mostrar_error_politica(error)
        self.vista.mostrar_mensaje(
            "Política actualizada. Los plazos de entregas anteriores se conservan."
        )
        return redirect(url_for("politicas.consultar_politicas", _anchor=f"politica-categoria-{request.form.get('id_categoria_ref', '')}"))

    @requiere_permiso("POLITICAS_GESTIONAR")
    def eliminar_politica(self, id_politica):
        self.servicio.eliminar_politica(id_politica)
        self.vista.mostrar_mensaje("Política sin préstamos asociados eliminada.")
        return redirect(url_for("politicas.consultar_politicas"))

    def _mostrar_error_politica(self, error):
        mensaje = error_formulario(error, "Ya existe una política para esta categoría y tipo de persona.")
        return self._mostrar_consulta(error=mensaje)

    @requiere_permiso("POLITICAS_GESTIONAR")
    def actualizar_vencimientos(self):
        try:
            self.servicio.actualizar_politica_vencimiento_reserva(request.form)
        except ValueError as error:
            return self._mostrar_consulta(error_vencimiento=str(error))
        self.vista.mostrar_mensaje("Vencimientos generales actualizados para nuevas solicitudes y preparaciones.")
        return redirect(url_for("politicas.consultar_politicas", _anchor="politicas-vencimiento"))

    def _mostrar_consulta(self, error=None, error_horario=None, error_vencimiento=None, error_limites=None):
        return self.vista.mostrar_consulta(
            self.servicio.consultar_politicas(), self.servicio.consultar_categorias(),
            error=error, horario=self.servicio.consultar_horario_atencion(), error_horario=error_horario,
            vencimientos=self.servicio.consultar_politica_vencimiento_reserva(), error_vencimiento=error_vencimiento,
            limites=self.servicio.consultar_limites_articulos(), error_limites=error_limites)

    @requiere_permiso('POLITICAS_GESTIONAR')
    def actualizar_horario_atencion(self):
        try:
            self.servicio.actualizar_horario_atencion(request.form)
        except ValueError as error:
            return self._mostrar_consulta(error_horario=str(error))
        self.vista.mostrar_mensaje('Horario general de atención actualizado.')
        return redirect(url_for('politicas.consultar_politicas', _anchor='horario-atencion'))

    @requiere_permiso('POLITICAS_GESTIONAR')
    def actualizar_limites_articulos(self):
        if g.usuario.rol.nombre != NombreRol.ADMINISTRADOR:
            raise PermissionError('Solo el administrador puede cambiar el máximo de artículos.')
        try:
            self.servicio.actualizar_limites_articulos(request.form)
        except ValueError as error:
            return self._mostrar_consulta(error_limites=str(error))
        self.vista.mostrar_mensaje('Máximos generales de artículos actualizados.')
        return redirect(url_for('politicas.consultar_politicas', _anchor='limites-articulos'))
