from datetime import date
from flask import render_template, flash


class VistaRecurso:
    def _mostrar(self, modo, **datos):
        datos.setdefault("politicas_por_categoria", {})
        return render_template("vista_recurso.html", modo=modo, **datos)

    def mostrar_administracion(
        self,
        datos,
        categoria=None,
        error=None,
        seccion_error=None,
        datos_recurso=None,
        datos_categoria=None,
    ):
        return self._mostrar(
            "administracion",
            **datos,
            categoria=categoria,
            error=error,
            seccion_error=seccion_error,
            datos_recurso=datos_recurso or {},
            datos_categoria=datos_categoria or {},
            fecha_hoy=date.today().isoformat()
        )

    def mostrar_edicion_recurso(self, categorias, recurso, error=None):
        return self._mostrar(
            "editar_recurso",
            categorias=categorias,
            recurso=recurso,
            error=error,
            fecha_hoy=date.today().isoformat(),
        )

    def mostrar_consulta(self, recursos, categorias, categoria_catalogo=None, opciones_filtro=None):
        return self._mostrar(
            "consulta", recursos=recursos, categorias=categorias,
            categoria_catalogo=categoria_catalogo,
            opciones_filtro=opciones_filtro or {'recursos': [], 'bienes': []},
        )

    def mostrar_detalle(self, disponibilidad, categoria, politicas_por_categoria=None):
        return self._mostrar("detalle", categoria=categoria, politicas_por_categoria=politicas_por_categoria or {}, **disponibilidad)

    def mostrar_mensaje(self, mensaje):
        flash(mensaje, "success")
