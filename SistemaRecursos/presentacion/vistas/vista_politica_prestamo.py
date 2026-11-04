from flask import render_template, flash
from dominio.gestion_control.tipo_persona import TipoPersona


class VistaPoliticaPrestamo:
    def mostrar_consulta(self, politicas, categorias, error=None, horario=None, error_horario=None, vencimientos=None, error_vencimiento=None):
        politicas_por_categoria = {}
        for regla in politicas:
            politicas_por_categoria.setdefault(regla.id_categoria_ref, {})[regla.tipo_persona.value] = regla
        return render_template(
            "vista_politica_prestamo.html",
            politicas=politicas,
            politicas_por_categoria=politicas_por_categoria,
            horario=horario,
            error_horario=error_horario,
            vencimientos=vencimientos,
            error_vencimiento=error_vencimiento,
            error=error,
            tipos_persona=TipoPersona,
            categorias=categorias,
        )

    def mostrar_mensaje(self, mensaje):
        flash(mensaje, "success")
