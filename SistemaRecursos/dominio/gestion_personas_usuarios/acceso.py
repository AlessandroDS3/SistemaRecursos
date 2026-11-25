"""Cuenta mínima para autenticación; no contiene una ficha institucional."""

from dataclasses import dataclass, field
from hashlib import sha256


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
    debe_cambiar_clave: bool = False
    permisos: frozenset[str] = frozenset()

    @property
    def nombre_completo(self):
        return f'{self.nombres} {self.apellidos}'

    @property
    def version_credenciales(self):
        datos = f'{self.contrasena_hash}:{int(self.debe_cambiar_clave)}:{self.rol}:{self.dni}'
        return sha256(datos.encode()).hexdigest()

    def puede_acceder(self):
        return self.estado_cuenta == self.estado_persona == 'ACTIVA'

    def permite(self, codigo):
        return not self.debe_cambiar_clave and codigo in self.permisos


def exigir_permiso(cuenta_actor, permiso):
    """Valida el diccionario de una operación y devuelve el mismo actor autorizado."""
    if (
        cuenta_actor is None
        or cuenta_actor['estado_cuenta'] != 'ACTIVA'
        or cuenta_actor['estado_persona'] != 'ACTIVA'
        or cuenta_actor.get('debe_cambiar_clave', False)
        or permiso not in cuenta_actor['permisos']
    ):
        raise PermissionError('La cuenta no tiene permiso para esta operación.')
    return cuenta_actor
