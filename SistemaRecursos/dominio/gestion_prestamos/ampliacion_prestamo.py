#!/usr/bin/python
# -*- coding: utf-8 -*-


from enum import Enum


class EstadoAmpliacion(Enum):
    PENDIENTE = 1
    APROBADA = 2
    RECHAZADA = 3


class AmpliacionPrestamo:
    def __init__(self):
        self.id_ampliacion = None
        self.dni_solicitante = None
        self.id_detalle_ref = None
        self.fecha_solicitud = None
        self.fecha_limite_anterior = None
        self.fecha_limite_nueva = None
        self.motivo = None
        self.estado = None

    def aprobar(
        self,
    ):
        pass

    def rechazar(
        self,
    ):
        pass
