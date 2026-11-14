from datetime import datetime, timezone
from flask import render_template, flash


class VistaPrestamo:
    def mostrar_formulario(self, politicas, recurso_seleccionado="", bien_seleccionado=None, horario=None):
        return render_template(
            "vista_prestamo.html",
            modo="formulario",
            politicas=politicas,
            horario=horario,
            recurso_seleccionado=recurso_seleccionado,
            bien_seleccionado=bien_seleccionado,
        )

    def mostrar_consulta(self, prestamos, gestionar):
        return render_template(
            "vista_prestamo.html",
            modo="consulta",
            prestamos=prestamos,
            gestionar=gestionar,
        )

    def mostrar_detalle(self, prestamo, gestionar):
        return render_template(
            "vista_prestamo.html", modo="detalle", prestamo=prestamo, gestionar=gestionar,
            ahora_utc=datetime.now(timezone.utc).replace(tzinfo=None)
        )

    def mostrar_mensaje(self, mensaje):
        flash(mensaje, "success")
