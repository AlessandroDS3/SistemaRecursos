from __future__ import annotations
from servicios.servicio_recurso import ServicioAplicacionRecurso
from servicios.servicio_politica_prestamo import ServicioAplicacionPoliticaPrestamo
from flask import Blueprint, request, redirect, url_for, g
from mysql.connector import IntegrityError
from presentacion.formularios import error_formulario
from presentacion.seguridad import requiere_permiso, redirigir_segun_permiso
from presentacion.vistas.vista_recurso import VistaRecurso


MSG_BIEN_DUPLICADO = "Ya existe un bien con ese código de inventario."
MSG_CATEGORIA_DUPLICADA = "Ya existe una categoría con ese nombre."
MSG_CATEGORIA_CON_RECURSOS = "La categoría tiene recursos asociados y debe conservarse."


class ControladorRecurso:
    def __init__(self, servicio: ServicioAplicacionRecurso, politicas: ServicioAplicacionPoliticaPrestamo):
        self.servicio: ServicioAplicacionRecurso = servicio
        self.politicas: ServicioAplicacionPoliticaPrestamo = politicas
        self.vista = VistaRecurso()
        self.blueprint = Blueprint("recursos", __name__, url_prefix="/recursos")
        for ruta, nombre, vista, metodos in [
            ("", "consultar_recursos", self.consultar_recursos, ["GET"]),
            ("/administracion", "consultar_administracion_recursos", self.consultar_administracion_recursos, ["GET"]),
            ("/nuevo", "registrar_recurso", self.registrar_recurso, ["POST"]),
            ("/<int:id_recurso>", "consultar_recurso", self.consultar_recurso, ["GET"]),
            ('/<int:id_recurso>/editar', "mostrar_edicion_recurso", self.mostrar_edicion_recurso, ["GET"]),
            ('/<int:id_recurso>/editar', 'actualizar_recurso', self.actualizar_recurso, ["POST"]),
            ("/<int:id_recurso>/eliminar", "eliminar_recurso", self.eliminar_recurso, ["POST"]),
            ("/categorias/nueva", "registrar_categoria", self.registrar_categoria, ["POST"]),
            ("/categorias/<int:id_categoria>/editar", "actualizar_categoria", self.actualizar_categoria, ["POST"]),
            ("/categorias/<int:id_categoria>/eliminar", "eliminar_categoria", self.eliminar_categoria, ["POST"]),
        ]:
            self.blueprint.add_url_rule(ruta, nombre, vista, methods=metodos)

    @requiere_permiso("CATALOGO_CONSULTAR")
    def consultar_recursos(self):
        categoria_catalogo = (
            self.servicio.consultar_categoria(request.args['id_categoria_ref'])
            if request.args.get('id_categoria_ref') else None
        )
        resultado = self.servicio.consultar_recursos(request.args)
        return self.vista.mostrar_consulta(
            resultado["recursos"],
            self.servicio.consultar_categorias(),

            categoria_catalogo=categoria_catalogo,
            opciones_filtro=self.servicio.opciones_catalogo(request.args),
        )

    @requiere_permiso("CATALOGO_CONSULTAR")
    def consultar_recurso(self, id_recurso):
        disponibilidad = self.servicio.consultar_disponibilidad_recurso(id_recurso)
        recurso = disponibilidad["recurso"]
        categoria = self.servicio.consultar_categoria(recurso.id_categoria_ref)
        return self.vista.mostrar_detalle(disponibilidad, categoria, self._consultar_politicas_por_categoria())

    @requiere_permiso("RECURSOS_GESTIONAR")
    def registrar_recurso(self):
        try:
            recurso = self.servicio.registrar_recurso(request.form)
        except (LookupError, ValueError, IntegrityError) as error:
            return self._mostrar_error_administracion(error, "recurso")
        self.vista.mostrar_mensaje("Recurso registrado. Puedes agregar sus bienes físicos.")
        return redirect(
            url_for(
                "recursos.consultar_administracion_recursos",
                recurso=recurso.id_recurso,
                _anchor="continuar-registro",
            )
        )

    @requiere_permiso('RECURSOS_GESTIONAR')
    def mostrar_edicion_recurso(self, id_recurso):
        recurso = self.servicio.consultar_recurso(id_recurso)
        return self.vista.mostrar_edicion_recurso(self.servicio.consultar_categorias(), recurso)

    @requiere_permiso('RECURSOS_GESTIONAR')
    def actualizar_recurso(self, id_recurso):
        recurso = self.servicio.consultar_recurso(id_recurso)
        try:
            self.servicio.actualizar_recurso(dict(request.form, id_recurso=id_recurso))
        except (ValueError, IntegrityError) as error:
            mensaje = error_formulario(error, "Ya existe un recurso con esos datos únicos.")
            formulario = self.vista.mostrar_edicion_recurso(
                self.servicio.consultar_categorias(), recurso, error=mensaje
            )
            return formulario
        self.vista.mostrar_mensaje("Recurso actualizado.")
        return redirigir_segun_permiso(
            "recursos.consultar_recurso", "CATALOGO_CONSULTAR", id_recurso=id_recurso
        )

    @requiere_permiso("RECURSOS_GESTIONAR")
    def eliminar_recurso(self, id_recurso):
        self.servicio.eliminar_recurso(id_recurso)
        self.vista.mostrar_mensaje("Recurso eliminado.")
        return redirigir_segun_permiso("recursos.consultar_recursos", "CATALOGO_CONSULTAR")

    @requiere_permiso("RECURSOS_GESTIONAR")
    def consultar_administracion_recursos(self):
        return self._mostrar_administracion()

    @requiere_permiso("RECURSOS_GESTIONAR")
    def registrar_categoria(self):
        try:
            self.servicio.registrar_categoria(request.form)
        except (LookupError, ValueError, IntegrityError) as error:
            return self._mostrar_error_administracion(error, "categoria")
        self.vista.mostrar_mensaje("Categoría guardada.")
        return redirect(url_for("recursos.consultar_administracion_recursos", _anchor="categorias"))

    @requiere_permiso("RECURSOS_GESTIONAR")
    def actualizar_categoria(self, id_categoria):
        try:
            self.servicio.actualizar_categoria(dict(request.form, id_categoria=id_categoria))
        except (LookupError, ValueError, IntegrityError) as error:
            return self._mostrar_error_administracion(error, "categoria", id_categoria=id_categoria)
        self.vista.mostrar_mensaje("Categoría guardada.")
        return redirect(url_for("recursos.consultar_administracion_recursos", _anchor="categorias"))

    @requiere_permiso("RECURSOS_GESTIONAR")
    def eliminar_categoria(self, id_categoria):
        try:
            self.servicio.eliminar_categoria(id_categoria)
        except (LookupError, ValueError, IntegrityError) as error:
            return self._mostrar_error_administracion(error, "categoria")
        self.vista.mostrar_mensaje("Categoría eliminada.")
        return redirect(url_for("recursos.consultar_administracion_recursos", _anchor="categorias"))

    def _mostrar_error_administracion(self, error, seccion, id_categoria=None):
        if isinstance(error, LookupError):
            mensaje = str(error)
        elif isinstance(error, IntegrityError) and error.errno == 1451:
            mensaje = MSG_CATEGORIA_CON_RECURSOS
        else:
            duplicado = MSG_BIEN_DUPLICADO if seccion == "recurso" else MSG_CATEGORIA_DUPLICADA
            mensaje = error_formulario(error, duplicado)
        datos_categoria = dict(request.form, id_categoria=id_categoria) if id_categoria else None
        return self._mostrar_administracion(mensaje, seccion, datos_categoria)

    def _mostrar_administracion(self, error=None, seccion_error=None, datos_categoria=None):
        categoria = None
        recurso_continuacion = None
        if request.method == "GET":
            if request.args.get("editar_categoria"):
                categoria = self.servicio.consultar_categoria(request.args["editar_categoria"])
            if request.args.get("recurso"):
                recurso_continuacion = self.servicio.consultar_recurso(request.args["recurso"])

        datos = self.servicio.consultar_administracion_recursos(request.args)
        datos["recurso_continuacion"] = recurso_continuacion
        datos["politicas_por_categoria"] = self._consultar_politicas_por_categoria()
        return self.vista.mostrar_administracion(
            datos,
            categoria=categoria,
            error=error,
            seccion_error=seccion_error,
            datos_recurso=dict(request.form) if seccion_error == "recurso" else {},
            datos_categoria=(datos_categoria or dict(request.form)) if seccion_error == "categoria" else {},
        )

    def _consultar_politicas_por_categoria(self):
        resumen = {}
        if g.usuario.rol.tiene_permiso("POLITICAS_GESTIONAR"):
            for politica in self.politicas.consultar_politicas():
                resumen.setdefault(politica.id_categoria_ref, []).append(politica)
        return resumen
