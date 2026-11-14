"""Catálogo fijo de roles y permisos; la asignación se administra en MySQL."""

from typing import Protocol
from dominio.compartido.contratos import IRepositorioTransaccional

ROLES = ('USUARIO', 'ENCARGADO_PRESTAMOS', 'ADMINISTRADOR')
PERMISOS = {
    'CATALOGO_CONSULTAR': 'Consultar catálogo',
    'RESERVAS_PROPIAS_GESTIONAR': 'Reservar y cancelar reservas propias',
    'PRESTAMOS_PROPIOS_CONSULTAR': 'Consultar préstamos propios',
    'PRESTAMOS_GESTIONAR': 'Gestionar préstamos, devoluciones y ampliaciones',
    'PERSONAS_CONSULTAR': 'Consultar personas',
    'PERSONAS_GESTIONAR': 'Gestionar personas',
    'USUARIOS_GESTIONAR': 'Administrar cuentas',
    'ROLES_CONSULTAR': 'Consultar roles',
    'ROLES_GESTIONAR': 'Administrar roles y permisos',
    'RECURSOS_GESTIONAR': 'Gestionar recursos y bienes',
    'POLITICAS_GESTIONAR': 'Administrar políticas',
    'REPORTES_CONSULTAR': 'Consultar reportes y descargar CSV',
}


def validar_matriz(matriz):
    if set(matriz) != set(ROLES):
        raise ValueError('Incluye los tres roles.')
    if any(set(permisos) - PERMISOS.keys() for permisos in matriz.values()):
        raise ValueError('La matriz contiene permisos inexistentes.')
    if not {'ROLES_CONSULTAR', 'ROLES_GESTIONAR'} <= set(matriz['ADMINISTRADOR']):
        raise ValueError('El administrador debe conservar la administración de roles.')


class IRepositorioRol(IRepositorioTransaccional, Protocol):
    def consultar_matriz(self, bloquear=False) -> dict: ...
    def guardar_matriz(self, matriz: dict): ...
