#!/usr/bin/python
# -*- coding: utf-8 -*-

from enum import Enum


class TipoIncidencia(Enum):
    DANIO = 1
    PERDIDA = 2
    RETRASO = 3
    DEVOLUCION_INCOMPLETA = 4
    INCUMPLIMIENTO = 5
