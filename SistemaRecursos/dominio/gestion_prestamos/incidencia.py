#!/usr/bin/python
# -*- coding: utf-8 -*-


from enum import Enum


class TipoIncidencia(str, Enum):
    RETRASO = 'RETRASO'
    DANIO = 'DANIO'
    PERDIDA = 'PERDIDA'


class EstadoIncidencia(Enum):
    REGISTRADA = 1
    EN_REVISION = 2
    RESUELTA = 3


class Incidencia:
    def __init__(self):
        self.id_incidencia = None
        self.id_detalle = None
        self.tipo = None
        self.dni_registrador = None
        self.descripcion = None
        self.fecha = None
        self.estado = None
