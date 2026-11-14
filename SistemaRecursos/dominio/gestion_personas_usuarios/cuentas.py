"""Cuentas: identidad de acceso, roles, permisos y contratos."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TypedDict


# Nombre rol

class NombreRol(str, Enum):
    USUARIO = "USUARIO"
    ENCARGADO_PRESTAMOS = "ENCARGADO_PRESTAMOS"
    ADMINISTRADOR = "ADMINISTRADOR"


# Permiso

@dataclass(frozen=True)
class Permiso:
    codigo: str
    descripcion: str = ""


CATALOGO_PERMISOS = {'PERSONAS_CONSULTAR': 'Consultar el directorio de personas',
 'PERSONAS_GESTIONAR': 'Registrar, editar y desactivar personas',
 'USUARIOS_GESTIONAR': 'Crear cuentas y asignar roles',
 'ROLES_CONSULTAR': 'Consultar los roles y sus permisos',
 'ROLES_GESTIONAR': 'Asignar y revocar permisos de los roles',
 'CATALOGO_CONSULTAR': 'Consultar el catálogo de recursos',
 'PRESTAMOS_PROPIOS_CONSULTAR': 'Consultar préstamos propios',
 'RESERVAS_PROPIAS_GESTIONAR': 'Solicitar préstamos y gestionar reservas propias',
 'PRESTAMOS_GESTIONAR': 'Registrar entregas y devoluciones',
 'RECURSOS_GESTIONAR': 'Gestionar recursos y bienes',
 'POLITICAS_GESTIONAR': 'Gestionar políticas de préstamo',
 'REPORTES_CONSULTAR': 'Consultar y descargar reportes de préstamos y devoluciones'}


def consultar_catalogo_permisos():
    return [Permiso(codigo=codigo, descripcion=descripcion)
            for codigo, descripcion in sorted(CATALOGO_PERMISOS.items())]


# Rol

PERMISOS_ADMINISTRACION = frozenset({"ROLES_CONSULTAR", "ROLES_GESTIONAR"})


@dataclass(kw_only=True)
class Rol:
    nombre: NombreRol
    permisos: list[Permiso] = field(default_factory=list)

    def __post_init__(self):
        self.nombre = NombreRol(self.nombre)

    def tiene_permiso(self, codigo):
        return any(permiso.codigo == codigo for permiso in self.permisos)


def validar_permisos_administrador(roles, permisos, matriz):
    administrador = NombreRol.ADMINISTRADOR.value
    if administrador not in matriz:
        raise ValueError("La matriz debe incluir el rol Administrador.")
    if not PERMISOS_ADMINISTRACION.issubset(matriz[administrador]):
        raise ValueError("El rol Administrador debe conservar los permisos para consultar y gestionar roles.")


# Usuario sistema

@dataclass(repr=False)
class Credenciales:
    nombre_usuario: str
    contrasena_hash: str


class EstadoCuenta(str, Enum):
    ACTIVA = "ACTIVA"
    INACTIVA = "INACTIVA"
    BLOQUEADA = "BLOQUEADA"


@dataclass(kw_only=True)
class IdentidadAcceso:
    """Datos de identidad para acceder; la ficha de persona se consulta aparte."""
    dni: str
    nombres: str
    apellidos: str
    estado: str = 'ACTIVA'

    @property
    def nombre_completo(self):
        return f'{self.nombres} {self.apellidos}'

    def esta_activa(self):
        return self.estado == 'ACTIVA'


@dataclass(kw_only=True)
class UsuarioSistema:
    persona: IdentidadAcceso
    rol: Rol
    credenciales: Credenciales
    id_usuario: int | None = None
    ultimo_acceso: datetime | None = None
    estado_cuenta: EstadoCuenta = EstadoCuenta.ACTIVA

    def __post_init__(self):
        self.estado_cuenta = EstadoCuenta(self.estado_cuenta)

    @property
    def activo(self):
        return self.estado_cuenta == EstadoCuenta.ACTIVA

    def puede_acceder(self):
        return (
            self.activo
            and self.persona.esta_activa()
        )


class IRepositorioAcceso(ABC):
    """Operaciones necesarias para iniciar sesión y recuperar una sesión existente."""

    @abstractmethod
    def consultar_por_nombre_usuario(self, nombre_usuario) -> UsuarioSistema | None:
        raise NotImplementedError

    @abstractmethod
    def consultar_cuenta_por_id(self, id_usuario) -> UsuarioSistema | None:
        raise NotImplementedError

    @abstractmethod
    def registrar_acceso(self, id_usuario) -> None:
        raise NotImplementedError


class IRepositorioCuenta(ABC):
    """Operaciones de administración de cuentas y asignación de roles."""

    @abstractmethod
    def consultar_cuenta_persona(self, dni) -> UsuarioSistema | None:
        raise NotImplementedError

    @abstractmethod
    def consultar_resumen_cuentas(self, dnis_persona) -> dict[str, dict[str, bool]]:
        raise NotImplementedError

    @abstractmethod
    def registrar_cuenta(self, usuario) -> UsuarioSistema:
        raise NotImplementedError

    @abstractmethod
    def actualizar_cuenta(self, id_usuario, nombre_usuario=None, rol=None,
                         contrasena_hash=None, activar=None, id_usuario_actor=None) -> UsuarioSistema:
        raise NotImplementedError

    @abstractmethod
    def consultar_cuentas_para_roles(self, termino: str, limite: int = 20) -> list[CuentaParaRol]:
        raise NotImplementedError

    @abstractmethod
    def actualizar_rol_cuenta(self, id_usuario: int, rol: str, id_usuario_actor: int) -> UsuarioSistema:
        raise NotImplementedError


def es_administrador_activo(cuenta):
    return (cuenta["rol"] == NombreRol.ADMINISTRADOR
            and cuenta["estado_cuenta"] == EstadoCuenta.ACTIVA
            and cuenta["estado_persona"] == "ACTIVA")


def validar_baja_persona(dni, id_usuario_actor, cuentas):
    cuentas_persona = []
    for cuenta in cuentas:
        if cuenta["dni_persona"] == dni:
            cuentas_persona.append(cuenta)

    for cuenta in cuentas_persona:
        if cuenta["id_usuario"] == id_usuario_actor:
            raise ValueError("No puedes desactivar la persona de la cuenta con la que estás trabajando.")

    tiene_cuenta_administradora = False
    for cuenta in cuentas_persona:
        if es_administrador_activo(cuenta):
            tiene_cuenta_administradora = True
            break
    if not tiene_cuenta_administradora:
        return

    for cuenta in cuentas:
        if cuenta["dni_persona"] != dni and es_administrador_activo(cuenta):
            return
    raise ValueError("Debe conservarse al menos una cuenta administradora activa.")


def validar_conservacion_administrador(cuenta_actual, cuenta_nueva, cuentas):
    """Impide quitar acceso a la ultima cuenta administradora activa."""
    era_administrador = es_administrador_activo(cuenta_actual)
    seguira_siendo_administrador = es_administrador_activo(cuenta_nueva)
    if era_administrador and not seguira_siendo_administrador:
        hay_otro_administrador = False
        for cuenta in cuentas:
            if cuenta["id_usuario"] == cuenta_actual["id_usuario"]:
                continue
            if es_administrador_activo(cuenta):
                hay_otro_administrador = True
                break
        if not hay_otro_administrador:
            raise ValueError("Debe conservarse al menos una cuenta administradora activa.")


# I repositorio rol

class IRepositorioRol(ABC):
    @abstractmethod
    def consultar_rol(self, nombre_rol) -> Rol | None:
        raise NotImplementedError

    @abstractmethod
    def consultar_roles(self) -> list[Rol]:
        raise NotImplementedError

    @abstractmethod
    def consultar_permisos(self) -> list[Permiso]:
        raise NotImplementedError

    @abstractmethod
    def actualizar_matriz_permisos(self, permisos_por_rol, *, version) -> None:
        """Escritura explícita. Devuelve None y propaga errores de validación o integridad."""
        raise NotImplementedError


# Resultados de consulta

class CuentaParaRol(TypedDict):
    id_usuario: int
    dni_persona: str
    nombres: str
    apellidos: str
    cui: str | None
    nombre_usuario: str
    nombre_rol: str
    estado_cuenta: str
