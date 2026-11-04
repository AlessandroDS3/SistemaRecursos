from flask import render_template, flash


class VistaRol:
    def mostrar_consulta(self, roles, permisos, cuentas=None, termino="", error=None):
        return render_template(
            "vista_rol.html", roles=roles, permisos=permisos,
            cuentas=cuentas or [], termino=termino, error=error
        )

    def mostrar_mensaje(self, mensaje):
        flash(mensaje, "success")
