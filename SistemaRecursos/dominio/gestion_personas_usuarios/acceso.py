"""Cuenta mínima para autenticación; no contiene una ficha institucional."""

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Protocol


@dataclass(frozen=True, kw_only=True)
class CuentaAcceso:
    id_usuario: int
    dni: str
    nombre_usuario: str
    nombres: str
    apellidos: str
    rol: str
    estado_cuenta: str
    estado_persona: str
    contrasena_hash: str = field(repr=False)
    permisos: frozenset[str] = frozenset()

    @property
    def nombre_completo(self):
        return f'{self.nombres} {self.apellidos}'

    @property
    def version_credenciales(self):
        return sha256(self.contrasena_hash.encode()).hexdigest()

    def puede_acceder(self):
        return self.estado_cuenta == self.estado_persona == 'ACTIVA'

    def permite(self, codigo):
        return codigo in self.permisos


class IRepositorioAcceso(Protocol):
    def consultar_cuenta_por_usuario(self, nombre: str) -> CuentaAcceso | None: ...
    def consultar_cuenta_por_id(self, identificador: int) -> CuentaAcceso | None: ...
    def registrar_acceso(self, identificador: int) -> None: ...


def exigir_permiso(cuenta, permiso):
    if (
        cuenta is None
        or cuenta['estado_cuenta'] != 'ACTIVA'
        or cuenta['estado_persona'] != 'ACTIVA'
        or permiso not in cuenta['permisos']
    ):
        raise PermissionError('La cuenta no tiene permiso para esta operación.')
    return cuenta
