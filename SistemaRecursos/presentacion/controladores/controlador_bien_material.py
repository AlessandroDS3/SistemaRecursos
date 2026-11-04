from __future__ import annotations
from servicios.servicio_bien_material import ServicioAplicacionBienMaterial
from servicios.servicio_recurso import ServicioAplicacionRecurso
from flask import Blueprint, request, redirect, url_for, g
from mysql.connector import IntegrityError
from presentacion.formularios import error_formulario
from presentacion.seguridad import requiere_permiso, redirigir_segun_permiso
from presentacion.vistas.vista_bien_material import VistaBienMaterial


class ControladorBienMaterial:
    MSG_CODIGO_DUPLICADO = "Ya existe un bien con ese código de inventario."

    def __init__(self, servicio: ServicioAplicacionBienMaterial, recursos: ServicioAplicacionRecurso):
        self.servicio: ServicioAplicacionBienMaterial = servicio
        self.recursos: ServicioAplicacionRecurso = recursos
        self.vista = VistaBienMaterial()
        self.blueprint = Blueprint("bienes", __name__, url_prefix="/bienes")

        for ruta, nombre, vista, metodos in [
            ("", "consultar_bienes_materiales", self.consultar_bienes_materiales, ["GET"]),
            ('/nuevo', "mostrar_formulario_bien_material", self.mostrar_formulario_bien_material, ["GET"]),
            ('/nuevo', 'registrar_bien_material', self.registrar_bien_material, ["POST"]),
            ("/<int:id_bien>", "consultar_detalle_bien_material", self.consultar_detalle_bien_material, ["GET"]),
            ('/<int:id_bien>/editar', "mostrar_edicion_bien_material", self.mostrar_edicion_bien_material, ["GET"]),
            ('/<int:id_bien>/editar', 'actualizar_bien_material', self.actualizar_bien_material, ["POST"]),
            (
                "/<int:id_bien>/eliminar",
                "eliminar_bien_material",
                self.eliminar_bien_material,
                ["POST"],
            ),
            ("/<int:id_bien>/estado", "cambiar_estado_bien_material", self.cambiar_estado_bien_material, ["POST"]),
        ]:
            self.blueprint.add_url_rule(ruta, nombre, vista, methods=metodos)

    @requiere_permiso("RECURSOS_GESTIONAR")
    def consultar_bienes_materiales(self):
        resultado = self.servicio.consultar_bienes_materiales(request.args)
        return self.vista.mostrar_consulta(
            resultado["bienes"],
            resultado["resumen"],
        )

    @requiere_permiso('RECURSOS_GESTIONAR')
    def mostrar_formulario_bien_material(self):
        recurso = self.recursos.consultar_recurso(request.args.get("recurso"))
        return self.vista.mostrar_formulario(recurso)

    @requiere_permiso('RECURSOS_GESTIONAR')
    def registrar_bien_material(self):
        recurso = self.recursos.consultar_recurso(request.form.get("id_recurso_ref"))
        try:
            self.servicio.registrar_bien_material(request.form)
        except (ValueError, IntegrityError) as error:
            mensaje = error_formulario(
                error, self.MSG_CODIGO_DUPLICADO
            )
            formulario = self.vista.mostrar_formulario(
                recurso, error=mensaje
            )
            return formulario
        self.vista.mostrar_mensaje("Ejemplar registrado como disponible.")
        return redirect(
            url_for(
                "recursos.consultar_administracion_recursos",
                recurso=recurso.id_recurso,
                _anchor="continuar-registro",
            )
        )

    @requiere_permiso("RECURSOS_GESTIONAR")
    def consultar_detalle_bien_material(self, id_bien):
        detalle = self.servicio.consultar_detalle_bien_material(id_bien)
        bien = detalle["bien"]

        return self.vista.mostrar_detalle(
            bien,
            self.recursos.consultar_recurso(bien.id_recurso_ref),
            detalle["historial"],
            detalle["registros"],
            detalle["prestamo_pendiente"],
        )

    @requiere_permiso('RECURSOS_GESTIONAR')
    def mostrar_edicion_bien_material(self, id_bien):
        bien = self.servicio.consultar_bien_material(id_bien)
        recurso = self.recursos.consultar_recurso(bien.id_recurso_ref)
        return self.vista.mostrar_formulario(recurso, bien)

    @requiere_permiso('RECURSOS_GESTIONAR')
    def actualizar_bien_material(self, id_bien):
        bien = self.servicio.consultar_bien_material(id_bien)
        recurso = self.recursos.consultar_recurso(bien.id_recurso_ref)
        try:
            self.servicio.actualizar_bien_material(
                dict(request.form, id_bien=id_bien)
            )
        except (ValueError, IntegrityError) as error:
            mensaje = error_formulario(
                error, self.MSG_CODIGO_DUPLICADO
            )
            formulario = self.vista.mostrar_formulario(
                recurso, bien, error=mensaje
            )
            return formulario
        self.vista.mostrar_mensaje("Datos del bien actualizados.")
        return redirect(url_for("bienes.consultar_detalle_bien_material", id_bien=id_bien))

    @requiere_permiso("RECURSOS_GESTIONAR")
    def eliminar_bien_material(self, id_bien):
        bien = self.servicio.consultar_bien_material(id_bien)
        self.servicio.eliminar_bien_material(id_bien)
        self.vista.mostrar_mensaje("Bien sin historial eliminado.")

        return redirigir_segun_permiso(
            "recursos.consultar_recurso",
            "CATALOGO_CONSULTAR",
            id_recurso=bien.id_recurso_ref,
        )

    def _guardar_estado(self, id_bien, accion):
        accion(
            dict(request.form, id_bien=id_bien),
            g.usuario.persona.dni,
        )
        self.vista.mostrar_mensaje(
            "Estado actualizado."
        )
        return redirect(url_for("bienes.consultar_detalle_bien_material", id_bien=id_bien))

    @requiere_permiso("RECURSOS_GESTIONAR")
    def cambiar_estado_bien_material(self, id_bien):
        return self._guardar_estado(id_bien, self.servicio.cambiar_estado_bien_material)
