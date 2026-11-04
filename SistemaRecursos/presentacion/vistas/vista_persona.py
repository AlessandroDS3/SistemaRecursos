from flask import render_template, flash


class VistaPersona:
    def mostrar_formulario(self, persona=None, error=None, errores=None):
        return render_template("vista_persona.html", modo="formulario", persona=persona, error=error, errores=errores or {})

    def mostrar_consulta(
        self, personas, cuentas_por_persona=None, filtros=None, resumen=None
    ):
        return render_template(
            "vista_persona.html",
            modo="consulta",
            personas=personas,
            cuentas_por_persona=cuentas_por_persona or {},
            filtros=filtros or {},
            resumen=resumen or {"total": len(personas), "activas": 0, "inactivas": 0},
        )

    def mostrar_detalle(self, persona, cuenta=None, error=None):
        return render_template(
            "vista_persona.html", modo="detalle", persona=persona, cuenta=cuenta, error=error
        )

    def mostrar_formulario_cuenta(self, persona, cuenta, error=None):
        return render_template(
            "vista_persona.html", modo="cuenta", persona=persona, cuenta=cuenta, error=error
        )

    def mostrar_mensaje(self, mensaje):
        flash(mensaje, "success")

    def mostrar_confirmacion_desactivacion(self, persona):
        return render_template("vista_persona.html", modo="desactivar", persona=persona)
