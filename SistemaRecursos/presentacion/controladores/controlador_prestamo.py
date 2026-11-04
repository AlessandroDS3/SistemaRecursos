from __future__ import annotations
from servicios.servicio_prestamo import ServicioAplicacionPrestamo
from servicios.servicio_politica_prestamo import ServicioAplicacionPoliticaPrestamo
from servicios.servicio_sancion import ServicioAplicacionSancion
from flask import Blueprint, request, redirect, url_for, g, abort, jsonify
from presentacion.seguridad import requiere_permiso
from presentacion.vistas.vista_prestamo import VistaPrestamo


class ControladorPrestamo:
    def __init__(self, servicio: ServicioAplicacionPrestamo, politicas: ServicioAplicacionPoliticaPrestamo, sanciones: ServicioAplicacionSancion):
        self.servicio: ServicioAplicacionPrestamo = servicio
        self.politicas: ServicioAplicacionPoliticaPrestamo = politicas
        self.sanciones: ServicioAplicacionSancion = sanciones
        self.vista = VistaPrestamo()
        self.blueprint = Blueprint("prestamos", __name__, url_prefix="/prestamos")
        for ruta, nombre, vista, metodos in [
            ("", "consultar_prestamos", self.consultar_prestamos, ["GET"]),
            ("/vencimientos/actualizar", "actualizar_prestamos_vencidos", self.actualizar_prestamos_vencidos, ["POST"]),
            ('/nuevo', "mostrar_formulario_prestamo", self.mostrar_formulario_prestamo, ["GET"]),
            ('/nuevo', 'registrar_prestamo', self.registrar_prestamo, ["POST"]),
            ("/personas/buscar", "consultar_solicitantes", self.consultar_solicitantes, ["GET"]),
            ("/bienes/buscar", "consultar_bienes_disponibles", self.consultar_bienes_disponibles, ["GET"]),
            ("/<int:id_prestamo>", "consultar_prestamo", self.consultar_prestamo, ["GET"]),
            ("/<int:id_prestamo>/detalles/<int:id_detalle>/sancion/quitar", "levantar_sancion_vencimiento", self.levantar_sancion_vencimiento, ["POST"]),
            ("/<int:id_prestamo>/devolver", "registrar_devolucion", self.registrar_devolucion, ["POST"]),
            ("/<int:id_prestamo>/perdida", "reportar_perdida", self.reportar_perdida, ["POST"]),
        ]:
            self.blueprint.add_url_rule(ruta, nombre, vista, methods=metodos)

    @staticmethod
    def _puede_consultar():
        gestionar = g.usuario.rol.tiene_permiso("PRESTAMOS_GESTIONAR")
        if not gestionar and not g.usuario.rol.tiene_permiso("PRESTAMOS_PROPIOS_CONSULTAR"):
            abort(403)
        return gestionar

    @requiere_permiso()
    def consultar_prestamos(self):
        gestionar = self._puede_consultar()
        prestamos = self.servicio.consultar_prestamos(
            request.args,
            g.usuario.persona.dni,
            gestionar,
        )
        return self.vista.mostrar_consulta(
            prestamos["prestamos"], gestionar
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def mostrar_formulario_prestamo(self):
        bien = None
        recurso = request.args.get("recurso", "")
        if "bien" in request.args:
            bien = self.servicio.seleccionar_bien_para_prestamo(request.args["bien"])
            recurso = bien["id_recurso_ref"]
        return self.vista.mostrar_formulario(
            self.politicas.consultar_politicas(),
            recurso_seleccionado=recurso,
            bien_seleccionado=bien,
            horario=self.politicas.consultar_horario_atencion(),
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def registrar_prestamo(self):
        prestamo = self.servicio.registrar_prestamo(request.form, g.usuario.persona.dni)
        self.vista.mostrar_mensaje(
            "Préstamo registrado. Los bienes quedaron prestados y sus fechas de devolución se calcularon según las políticas."
        )
        return redirect(url_for("prestamos.consultar_prestamo", id_prestamo=prestamo.id_prestamo))

    @requiere_permiso("PRESTAMOS_GESTIONAR")
    def consultar_solicitantes(self):
        resultados = self.servicio.consultar_solicitantes(request.args.get("q", ""))
        return jsonify({"resultados": resultados, "limite": 20})

    @requiere_permiso("PRESTAMOS_GESTIONAR")
    def consultar_bienes_disponibles(self):
        resultados = self.servicio.consultar_bienes_disponibles(
            request.args.get("q", ""), request.args.get("recurso")
        )
        return jsonify({"resultados": resultados})

    @requiere_permiso()
    def consultar_prestamo(self, id_prestamo):
        gestionar = self._puede_consultar()
        prestamo = self.servicio.consultar_prestamo(
            id_prestamo, g.usuario.persona.dni, gestionar
        )
        return self.vista.mostrar_detalle(prestamo, gestionar)

    @requiere_permiso("PRESTAMOS_GESTIONAR")
    def registrar_devolucion(self, id_prestamo):
        self.servicio.registrar_devolucion(id_prestamo, request.form, g.usuario.persona.dni)
        self.vista.mostrar_mensaje(
            "Devolución registrada. Los bienes recibidos y el estado del préstamo se actualizaron."
        )
        return redirect(url_for("prestamos.consultar_prestamo", id_prestamo=id_prestamo))

    @requiere_permiso("PRESTAMOS_GESTIONAR")
    def reportar_perdida(self, id_prestamo):
        self.servicio.reportar_perdida(
            id_prestamo,
            request.form.get("id_detalle"),
            request.form.get("motivo"),
            g.usuario.persona.dni,
        )
        self.vista.mostrar_mensaje("Pérdida registrada. El bien continúa pendiente de devolución.")
        return redirect(url_for("prestamos.consultar_prestamo", id_prestamo=id_prestamo))

    @requiere_permiso("PRESTAMOS_GESTIONAR")
    def actualizar_prestamos_vencidos(self):
        self.servicio.actualizar_prestamos_vencidos(g.usuario.persona.dni)
        self.vista.mostrar_mensaje("Vencimientos registrados en el historial.")
        return redirect(url_for("prestamos.consultar_prestamos"))

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def levantar_sancion_vencimiento(self, id_prestamo, id_detalle):
        self.sanciones.levantar_sancion_vencimiento(
            id_prestamo, id_detalle, request.form.get('justificacion', ''), g.usuario.persona.dni)
        self.vista.mostrar_mensaje('Sanción por tardanza retirada. La justificación quedó registrada.')
        return redirect(url_for('prestamos.consultar_prestamo', id_prestamo=id_prestamo, _anchor='devolucion'))
