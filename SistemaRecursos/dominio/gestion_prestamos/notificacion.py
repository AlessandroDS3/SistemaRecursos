#!/usr/bin/python
# -*- coding: utf-8 -*-


from enum import Enum


class EstadoNotificacionPrestamo(Enum):
    PENDIENTE = 1
    ENVIADA = 2
    LEIDA = 3


class Notificacion:
    def __init__(self):
        self.id_notificacion = None
        self.id_detalle_ref = None
        self.dni_persona = None
        self.tipo = None
        self.fecha_programada = None
        self.fecha_envio = None
        self.mensaje = None
        self.estado = None

    def enviar(
        self,
    ):
        pass
