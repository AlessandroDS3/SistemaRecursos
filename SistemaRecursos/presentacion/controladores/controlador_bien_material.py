from __future__ import annotations

from flask import Blueprint, g, redirect, request, url_for
from mysql.connector import IntegrityError

from presentacion.formularios import error_formulario
from presentacion.seguridad import redirigir_segun_permiso, requiere_permiso
from presentacion.vistas.vista_bien_material import VistaBienMaterial
from servicios.servicio_bien_material import ServicioAplicacionBienMaterial
from servicios.servicio_recurso import ServicioAplicacionRecurso


class ControladorBienMaterial:

    MSG_CODIGO_DUPLICADO = "Ya existe un bien con ese código de inventario."

    # Preparar los servicios, la vista y las rutas.
    def __init__(
        self,
        servicio: ServicioAplicacionBienMaterial,
        recursos: ServicioAplicacionRecurso,
    ):
        self.servicio: ServicioAplicacionBienMaterial = servicio
        self.recursos: ServicioAplicacionRecurso = recursos
        self.vista = VistaBienMaterial()
        self.blueprint = Blueprint("bienes", __name__, url_prefix="/bienes")
        self._registrar_rutas()

    def _registrar_rutas(self):
        rutas = [
            # Consultas de bienes.
            ("", "consultar_bienes_materiales", self.consultar_bienes_materiales, ["GET"]),
            ("/<int:id_bien>", "consultar_detalle_bien_material", self.consultar_detalle_bien_material, ["GET"]),
            # Registro y edición.
            ("/nuevo", "mostrar_formulario_bien_material", self.mostrar_formulario_bien_material, ["GET"]),
            ("/nuevo", "registrar_bien_material", self.registrar_bien_material, ["POST"]),
            ("/<int:id_bien>/editar", "mostrar_edicion_bien_material", self.mostrar_edicion_bien_material, ["GET"]),
            ("/<int:id_bien>/editar", "actualizar_bien_material", self.actualizar_bien_material, ["POST"]),

            (
                "/<int:id_bien>/eliminar",
                "eliminar_bien_material",
                self.eliminar_bien_material,
                ["POST"],
            ),
            ("/<int:id_bien>/estado", "cambiar_estado_bien_material", self.cambiar_estado_bien_material, ["POST"]),
        ]
        for ruta, nombre, metodo_controlador, metodos_http in rutas:
            self.blueprint.add_url_rule(
                ruta, nombre, metodo_controlador, methods=metodos_http
            )

    # Consultar Y el detalle de los bienes.
    @requiere_permiso("RECURSOS_GESTIONAR")
    def consultar_bienes_materiales(self):
        resultado = self.servicio.consultar_bienes_materiales(request.args)
        return self.vista.mostrar_consulta(
            resultado["bienes"],
            resultado["resumen"],
        )

    @requiere_permiso("RECURSOS_GESTIONAR")
    def consultar_detalle_bien_material(self, id_bien):
        detalle = self.servicio.consultar_detalle_bien_material(id_bien)
        bien = detalle["bien"]
        recurso = self.recursos.consultar_recurso(bien.id_recurso_ref)

        return self.vista.mostrar_detalle(
            bien,
            recurso,
            detalle["historial"],
            detalle["registros"],
            detalle["prestamo_pendiente"],
        )

    # Mostrar el formulario y registrar un nuevo bien.
    @requiere_permiso("RECURSOS_GESTIONAR")
    def mostrar_formulario_bien_material(self):
        id_recurso = request.args.get("recurso")
        recurso = self.recursos.consultar_recurso(id_recurso)
        return self.vista.mostrar_formulario(recurso)

    @requiere_permiso("RECURSOS_GESTIONAR")
    def registrar_bien_material(self):
        id_recurso = request.form.get("id_recurso_ref")
        recurso = self.recursos.consultar_recurso(id_recurso)
        try:
            self.servicio.registrar_bien_material(request.form)
        except (ValueError, IntegrityError) as error:
            mensaje = error_formulario(error, self.MSG_CODIGO_DUPLICADO)
            return self.vista.mostrar_formulario(recurso, error=mensaje)

        self.vista.mostrar_mensaje("Ejemplar registrado como disponible.")
        return redirect(
            url_for(
                "recursos.consultar_administracion_recursos",
                recurso=recurso.id_recurso,
                _anchor="continuar-registro",
            )
        )

    # 4. Mostrar los datos actuales y guardar su edición.
    @requiere_permiso("RECURSOS_GESTIONAR")
    def mostrar_edicion_bien_material(self, id_bien):
        bien = self.servicio.consultar_bien_material(id_bien)
        recurso = self.recursos.consultar_recurso(bien.id_recurso_ref)
        return self.vista.mostrar_formulario(recurso, bien)

    @requiere_permiso("RECURSOS_GESTIONAR")
    def actualizar_bien_material(self, id_bien):
        bien = self.servicio.consultar_bien_material(id_bien)
        recurso = self.recursos.consultar_recurso(bien.id_recurso_ref)
        datos_bien = dict(request.form, id_bien=id_bien)
        try:
            self.servicio.actualizar_bien_material(datos_bien)
        except (ValueError, IntegrityError) as error:
            mensaje = error_formulario(error, self.MSG_CODIGO_DUPLICADO)
            return self.vista.mostrar_formulario(recurso, bien, error=mensaje)

        self.vista.mostrar_mensaje("Datos del bien actualizados.")
        return redirect(url_for("bienes.consultar_detalle_bien_material", id_bien=id_bien))

    # 5. Eliminar un bien.
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

    # 6. Cambiar el estado del bien.
    @requiere_permiso("RECURSOS_GESTIONAR")
    def cambiar_estado_bien_material(self, id_bien):
        datos_bien = dict(request.form, id_bien=id_bien)
        dni_responsable = g.usuario.persona.dni
        self.servicio.cambiar_estado_bien_material(datos_bien, dni_responsable)
        self.vista.mostrar_mensaje("Estado actualizado.")
        return redirect(url_for("bienes.consultar_detalle_bien_material", id_bien=id_bien))
