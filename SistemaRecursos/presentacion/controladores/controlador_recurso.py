from __future__ import annotations

from flask import Blueprint, g, redirect, request, url_for
from mysql.connector import IntegrityError

from presentacion.formularios import error_formulario
from presentacion.seguridad import redirigir_segun_permiso, requiere_permiso
from presentacion.vistas.vista_recurso import VistaRecurso
from servicios.servicio_politica_prestamo import ServicioAplicacionPoliticaPrestamo
from servicios.servicio_recurso import ServicioAplicacionRecurso


MSG_BIEN_DUPLICADO = "Ya existe un bien con ese código de inventario."
MSG_CATEGORIA_DUPLICADA = "Ya existe una categoría con ese nombre."
MSG_CATEGORIA_CON_RECURSOS = "La categoría tiene recursos asociados y debe conservarse."


class ControladorRecurso:
    """Recibe las peticiones, llama a los servicios y muestra las vistas."""

    # Preparar los servicios, la vista y las rutas.
    def __init__(
        self,
        servicio: ServicioAplicacionRecurso,
        politicas: ServicioAplicacionPoliticaPrestamo,
    ):
        self.servicio: ServicioAplicacionRecurso = servicio
        self.politicas: ServicioAplicacionPoliticaPrestamo = politicas
        self.vista = VistaRecurso()
        self.blueprint = Blueprint("recursos", __name__, url_prefix="/recursos")
        self._registrar_rutas()

    def _registrar_rutas(self):
        rutas = [
            # Consultas del catálogo.
            ("", "consultar_recursos", self.consultar_recursos, ["GET"]),
            ("/<int:id_recurso>", "consultar_recurso", self.consultar_recurso, ["GET"]),
            # Administración de recursos.
            ("/administracion", "consultar_administracion_recursos", self.consultar_administracion_recursos, ["GET"]),
            ("/nuevo", "registrar_recurso", self.registrar_recurso, ["POST"]),
            ("/<int:id_recurso>/editar", "mostrar_edicion_recurso", self.mostrar_edicion_recurso, ["GET"]),
            ("/<int:id_recurso>/editar", "actualizar_recurso", self.actualizar_recurso, ["POST"]),
            ("/<int:id_recurso>/eliminar", "eliminar_recurso", self.eliminar_recurso, ["POST"]),
            # Administración de categorías.
            ("/categorias/nueva", "registrar_categoria", self.registrar_categoria, ["POST"]),
            ("/categorias/<int:id_categoria>/editar", "actualizar_categoria", self.actualizar_categoria, ["POST"]),
            ("/categorias/<int:id_categoria>/eliminar", "eliminar_categoria", self.eliminar_categoria, ["POST"]),
        ]
        for ruta, nombre, metodo_controlador, metodos_http in rutas:
            self.blueprint.add_url_rule(
                ruta, nombre, metodo_controlador, methods=metodos_http
            )

    #  Consultar el catálogo y el detalle de un recurso.
    @requiere_permiso("CATALOGO_CONSULTAR")
    def consultar_recursos(self):
        """Muestra el catálogo con los filtros de la dirección web."""
        id_categoria = request.args.get("id_categoria_ref")
        categoria_catalogo = None
        if id_categoria:
            categoria_catalogo = self.servicio.consultar_categoria(id_categoria)

        resultado = self.servicio.consultar_recursos(request.args)
        categorias = self.servicio.consultar_categorias()
        opciones_filtro = self.servicio.opciones_catalogo(request.args)
        return self.vista.mostrar_consulta(
            resultado["recursos"],
            categorias,
            categoria_catalogo=categoria_catalogo,
            opciones_filtro=opciones_filtro,
        )

    @requiere_permiso("CATALOGO_CONSULTAR")
    def consultar_recurso(self, id_recurso):
        """Muestra el recurso, sus bienes y su disponibilidad."""
        disponibilidad = self.servicio.consultar_disponibilidad_recurso(id_recurso)
        recurso = disponibilidad["recurso"]
        categoria = self.servicio.consultar_categoria(recurso.id_categoria_ref)
        politicas = self._consultar_politicas_por_categoria()
        return self.vista.mostrar_detalle(disponibilidad, categoria, politicas)

    # Registrar, editar y eliminar recursos.
    @requiere_permiso("RECURSOS_GESTIONAR")
    def consultar_administracion_recursos(self):
        """Muestra la página para administrar recursos y categorías."""
        return self._mostrar_administracion()

    @requiere_permiso("RECURSOS_GESTIONAR")
    def registrar_recurso(self):
        """Recibe el formulario y registra el recurso."""
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

    @requiere_permiso("RECURSOS_GESTIONAR")
    def mostrar_edicion_recurso(self, id_recurso):
        """Carga los datos del recurso en el formulario de edición."""
        recurso = self.servicio.consultar_recurso(id_recurso)
        categorias = self.servicio.consultar_categorias()
        return self.vista.mostrar_edicion_recurso(categorias, recurso)

    @requiere_permiso("RECURSOS_GESTIONAR")
    def actualizar_recurso(self, id_recurso):
        """Guarda los cambios o vuelve a mostrar el formulario con el error."""
        recurso = self.servicio.consultar_recurso(id_recurso)
        datos_recurso = dict(request.form, id_recurso=id_recurso)
        try:
            self.servicio.actualizar_recurso(datos_recurso)
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
        """Solicita al servicio eliminar el recurso."""
        self.servicio.eliminar_recurso(id_recurso)
        self.vista.mostrar_mensaje("Recurso eliminado.")
        return redirigir_segun_permiso("recursos.consultar_recursos", "CATALOGO_CONSULTAR")

    # 4. Registrar, editar y eliminar categorías.
    @requiere_permiso("RECURSOS_GESTIONAR")
    def registrar_categoria(self):
        """Registra la categoría enviada en el formulario."""
        try:
            self.servicio.registrar_categoria(request.form)
        except (LookupError, ValueError, IntegrityError) as error:
            return self._mostrar_error_administracion(error, "categoria")
        self.vista.mostrar_mensaje("Categoría guardada.")
        return redirect(url_for("recursos.consultar_administracion_recursos", _anchor="categorias"))

    @requiere_permiso("RECURSOS_GESTIONAR")
    def actualizar_categoria(self, id_categoria):
        """Actualiza la categoría seleccionada."""
        datos_categoria = dict(request.form, id_categoria=id_categoria)
        try:
            self.servicio.actualizar_categoria(datos_categoria)
        except (LookupError, ValueError, IntegrityError) as error:
            return self._mostrar_error_administracion(error, "categoria", id_categoria=id_categoria)
        self.vista.mostrar_mensaje("Categoría guardada.")
        return redirect(url_for("recursos.consultar_administracion_recursos", _anchor="categorias"))

    @requiere_permiso("RECURSOS_GESTIONAR")
    def eliminar_categoria(self, id_categoria):
        """Solicita al servicio eliminar la categoría."""
        try:
            self.servicio.eliminar_categoria(id_categoria)
        except (LookupError, ValueError, IntegrityError) as error:
            return self._mostrar_error_administracion(error, "categoria")
        self.vista.mostrar_mensaje("Categoría eliminada.")
        return redirect(url_for("recursos.consultar_administracion_recursos", _anchor="categorias"))

    # Preparar los mensajes y los datos que necesitan las vistas.
    def _mostrar_error_administracion(self, error, seccion, id_categoria=None):
        """Prepara el mensaje de error y conserva los datos del formulario."""
        if isinstance(error, LookupError):
            mensaje = str(error)
        elif isinstance(error, IntegrityError) and error.errno == 1451:

            mensaje = MSG_CATEGORIA_CON_RECURSOS
        else:
            if seccion == "recurso":
                mensaje_duplicado = MSG_BIEN_DUPLICADO
            else:
                mensaje_duplicado = MSG_CATEGORIA_DUPLICADA
            mensaje = error_formulario(error, mensaje_duplicado)

        datos_categoria = None
        if id_categoria:
            datos_categoria = dict(request.form, id_categoria=id_categoria)
        return self._mostrar_administracion(mensaje, seccion, datos_categoria)

    def _mostrar_administracion(self, error=None, seccion_error=None, datos_categoria=None):
        """Reúne los recursos, categorías y formularios para la administración."""
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

        # Si hubo un error, conserva lo que se escribió en ese formulario.
        formulario_recurso = {}
        formulario_categoria = {}
        if seccion_error == "recurso":
            formulario_recurso = dict(request.form)
        if seccion_error == "categoria":
            formulario_categoria = datos_categoria or dict(request.form)

        return self.vista.mostrar_administracion(
            datos,
            categoria=categoria,
            error=error,
            seccion_error=seccion_error,
            datos_recurso=formulario_recurso,
            datos_categoria=formulario_categoria,
        )

    def _consultar_politicas_por_categoria(self):
        resumen = {}
        if not g.usuario.rol.tiene_permiso("POLITICAS_GESTIONAR"):
            return resumen

        for politica in self.politicas.consultar_politicas():
            id_categoria = politica.id_categoria_ref
            if id_categoria not in resumen:
                resumen[id_categoria] = []
            resumen[id_categoria].append(politica)
        return resumen
