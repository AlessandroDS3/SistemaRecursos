from enum import Enum


class NombreRol(str, Enum):
    USUARIO = "USUARIO"
    ENCARGADO_PRESTAMOS = "ENCARGADO_PRESTAMOS"
    ADMINISTRADOR = "ADMINISTRADOR"
