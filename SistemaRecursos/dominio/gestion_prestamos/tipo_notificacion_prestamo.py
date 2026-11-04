#!/usr/bin/python
# -*- coding: utf-8 -*-

from enum import Enum


class TipoNotificacionPrestamo(Enum):
    VENCIMIENTO_PROXIMO = 1
    PRESTAMO_VENCIDO = 2
