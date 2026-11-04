from datetime import date
from flask import render_template, flash
from dominio.gestion_recursos.bien_material import (
    EstadoBienMaterial, ESTADOS_CAMBIO_MANUAL, ESTADOS_GESTION_PRESTAMOS,
)


def opciones_estado(estados):
    etiquetas = {"DANADO": "Dañado", "MANTENIMIENTO": "En mantenimiento"}
    return [(estado.value, etiquetas.get(estado.value, estado.value.title())) for estado in estados]


class VistaBienMaterial:
    def mostrar_consulta(self, bienes, resumen):
        return render_template(
            "vista_bien_material.html",
            modo="consulta",
            estados=opciones_estado(EstadoBienMaterial),
            bienes=bienes,
            resumen=resumen,
        )

    def mostrar_formulario(self, recurso, bien=None, error=None):
        return render_template(
            "vista_bien_material.html",
            modo="formulario",
            recurso=recurso,
            bien=bien,
            error=error,
            fecha_hoy=date.today().isoformat(),
        )

    def mostrar_detalle(
        self, bien, recurso, historial, registros, prestamo_pendiente=None,
    ):
        return render_template(
            "vista_bien_material.html",
            modo="detalle",
            estados_manual=opciones_estado(
                estado for estado in EstadoBienMaterial if estado in ESTADOS_CAMBIO_MANUAL
            ),
            permite_cambio_manual=bien.estado not in ESTADOS_GESTION_PRESTAMOS,
            bien=bien,
            recurso=recurso,
            historial=historial,
            registros=registros,
            prestamo_pendiente=prestamo_pendiente,
            tiene_movimientos=bool(historial or registros),
        )

    def mostrar_mensaje(self, mensaje):
        flash(mensaje, "success")
