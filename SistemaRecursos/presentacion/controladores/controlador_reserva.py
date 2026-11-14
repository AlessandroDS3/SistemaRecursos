from __future__ import annotations
from dominio.reservas import EstadoReserva
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from presentacion.seguridad import requiere_permiso
from servicios.servicio_persona import ServicioAplicacionPersona
from servicios.servicio_politica_prestamo import ServicioAplicacionPoliticaPrestamo
from servicios.servicio_recurso import ServicioAplicacionRecurso
from servicios.servicio_reserva import ServicioAplicacionReserva


class ControladorReserva:
    def __init__(self, servicio: ServicioAplicacionReserva, recursos: ServicioAplicacionRecurso,
                 politicas: ServicioAplicacionPoliticaPrestamo, personas: ServicioAplicacionPersona):
        self.servicio: ServicioAplicacionReserva = servicio
        self.recursos: ServicioAplicacionRecurso = recursos
        self.politicas: ServicioAplicacionPoliticaPrestamo = politicas
        self.personas = personas
        self.blueprint = Blueprint("reservas", __name__, url_prefix="/reservas")
        for ruta, nombre, vista, metodos in [
            ("", "consultar_reservas", self.consultar_reservas, ["GET"]),
            ('/nueva', "mostrar_formulario_reserva", self.mostrar_formulario_reserva, ["GET"]),
            ('/nueva', 'registrar_reserva', self.registrar_reserva, ["POST"]),
            ("/<int:id_reserva>", "consultar_reserva", self.consultar_reserva, ["GET"]),
            ("/<int:id_reserva>/preparar", "preparar_reserva", self.preparar_reserva, ["POST"]),
            ("/<int:id_reserva>/entregar", "entregar_reserva", self.entregar_reserva, ["POST"]),
            ("/<int:id_reserva>/cancelar", "cancelar_reserva", self.cancelar_reserva, ["POST"]),
            ("/<int:id_reserva>/rechazar", "rechazar_reserva", self.rechazar_reserva, ["POST"]),
            ("/<int:id_reserva>/expirar", "expirar_reserva", self.expirar_reserva, ["POST"]),
        ]:
            self.blueprint.add_url_rule(ruta, nombre, vista, methods=metodos)

    @staticmethod
    def _alcance():
        gestionar = g.usuario.rol.tiene_permiso("PRESTAMOS_GESTIONAR")
        if not gestionar and not g.usuario.rol.tiene_permiso("RESERVAS_PROPIAS_GESTIONAR"):
            abort(403)
        return gestionar

    @requiere_permiso()
    def consultar_reservas(self):
        gestionar = self._alcance()
        resultado = self.servicio.consultar_reservas(request.args, g.usuario.persona.dni, gestionar)
        return render_template("vista_reserva.html", modo="consulta", gestionar=gestionar,
                               estados=EstadoReserva, **resultado)

    @requiere_permiso()
    def mostrar_formulario_reserva(self):
        gestionar = self._alcance()
        if not request.args.get("recurso"):
            return redirect(url_for("recursos.consultar_recursos"))
        recurso = self.recursos.consultar_recurso(request.args["recurso"])
        tipo_persona = self.personas.consultar_persona(g.usuario.persona.dni).tipo
        politicas = [p for p in self.politicas.consultar_politicas() if p.id_categoria == recurso.id_categoria
                      and p.tipo_persona == tipo_persona]
        return render_template("vista_reserva.html", modo="formulario", gestionar=gestionar,
                               recurso=recurso, politicas=politicas, tipo_persona=tipo_persona)

    @requiere_permiso()
    def registrar_reserva(self):
        gestionar = self._alcance()
        nuevo = self.servicio.registrar_reserva(request.form, g.usuario.persona.dni)
        flash("Solicitud registrada.", "success")
        return redirect(url_for("reservas.consultar_reserva", id_reserva=nuevo))

    @requiere_permiso()
    def consultar_reserva(self, id_reserva):
        gestionar = self._alcance()
        reserva = self.servicio.consultar_reserva(id_reserva, g.usuario.persona.dni, gestionar)
        recurso = self.recursos.consultar_recurso(reserva["id_recurso"])
        politicas = [p for p in self.politicas.consultar_politicas()
                     if p.id_categoria == recurso.id_categoria
                      and p.tipo_persona == reserva["tipo_persona"]]
        return render_template("vista_reserva.html", modo="detalle", gestionar=gestionar,
                               reserva=reserva, politicas=politicas)

    @requiere_permiso()
    def preparar_reserva(self, id_reserva):
        gestionar = self._alcance()
        prestamo = self.servicio.preparar_reserva(id_reserva, request.form, g.usuario.persona.dni, gestionar)
        return self._respuesta_accion_reserva(id_reserva, prestamo)

    @requiere_permiso()
    def entregar_reserva(self, id_reserva):
        gestionar = self._alcance()
        prestamo = self.servicio.entregar_reserva(id_reserva, request.form, g.usuario.persona.dni, gestionar)
        return self._respuesta_accion_reserva(id_reserva, prestamo)

    @requiere_permiso()
    def cancelar_reserva(self, id_reserva):
        gestionar = self._alcance()
        prestamo = self.servicio.cancelar_reserva(id_reserva, request.form, g.usuario.persona.dni, gestionar)
        return self._respuesta_accion_reserva(id_reserva, prestamo)

    @requiere_permiso()
    def rechazar_reserva(self, id_reserva):
        gestionar = self._alcance()
        prestamo = self.servicio.rechazar_reserva(id_reserva, request.form, g.usuario.persona.dni, gestionar)
        return self._respuesta_accion_reserva(id_reserva, prestamo)

    @requiere_permiso()
    def expirar_reserva(self, id_reserva):
        gestionar = self._alcance()
        prestamo = self.servicio.expirar_reserva(id_reserva, request.form, g.usuario.persona.dni, gestionar)
        return self._respuesta_accion_reserva(id_reserva, prestamo)

    @staticmethod
    def _respuesta_accion_reserva(id_reserva, prestamo):
        flash("Entrega registrada." if prestamo else "Estado de la solicitud actualizado.", "success")
        return redirect(url_for("prestamos.consultar_prestamo", id_prestamo=prestamo) if prestamo else
                        url_for("reservas.consultar_reserva", id_reserva=id_reserva))
