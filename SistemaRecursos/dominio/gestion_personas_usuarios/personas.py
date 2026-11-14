"""Personas: datos institucionales, validación y contrato de persistencia."""
from __future__ import annotations
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypedDict


# Tipo persona

class TipoPersona(str, Enum):
    ESTUDIANTE = "ESTUDIANTE"
    DOCENTE = "DOCENTE"
    ADMINISTRATIVO = "ADMINISTRATIVO"


# Validacion persona

TIPOS = ("ESTUDIANTE", "DOCENTE", "ADMINISTRATIVO")


CORREO = re.compile(r"[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+")


CAMPOS_TIPO = {
    "DOCENTE": (
        ("codigo_docente", "Código de docente", 20),
        ("departamento_academico", "Departamento académico", 100),
        ("facultad", "Facultad", 100),
        ("escuela_profesional", "Escuela profesional", 100),
    ),
    "ADMINISTRATIVO": (
        ("codigo_empleado", "Código de empleado", 20),
        ("area", "Área", 100),
    ),
}


class ValidacionPersonaError(ValueError):
    def __init__(self, errores):
        self.errores = errores
        super().__init__(next(iter(errores.values())))


def _validar_texto(errores, datos, campo, etiqueta, limite):
    valor = datos.get(campo)
    if not isinstance(valor, str) or not valor.strip():
        errores[campo] = f"{etiqueta}: este campo es obligatorio."
    elif len(valor.strip()) > limite:
        errores[campo] = f"{etiqueta}: máximo {limite} caracteres."


def validar_datos_persona(datos):
    errores = {}
    tipo = datos.get("tipo")

    try:
        validar_dni(datos.get("dni"))
    except ValueError as error:
        errores["dni"] = str(error)
    if tipo == "ESTUDIANTE":
        cui = datos.get("cui")
        if not isinstance(cui, str) or not re.fullmatch(r"[0-9]{8}", cui):
            errores["cui"] = "El CUI debe tener exactamente 8 dígitos."

    for campo, etiqueta, limite in CAMPOS_TIPO.get(tipo, ()):
        _validar_texto(errores, datos, campo, etiqueta, limite)

    _validar_texto(errores, datos, "nombres", "Nombres", 100)
    _validar_texto(errores, datos, "apellidos", "Apellidos", 100)

    correo = datos.get("correo")
    if not isinstance(correo, str) or len(correo.strip()) > 120 or not CORREO.fullmatch(correo.strip()):
        errores["correo"] = "Ingresa un correo válido, por ejemplo nombre@dominio.com."

    telefono = datos.get("telefono", "")
    if not isinstance(telefono, str) or len(telefono) > 20:
        errores["telefono"] = "El teléfono admite hasta 20 caracteres."

    if tipo not in TIPOS:
        errores["tipo"] = "Selecciona un tipo de persona."

    if tipo == "ESTUDIANTE":
        if datos.get("estado_matricula") not in ("VIGENTE", "NO_VIGENTE"):
            errores["estado_matricula"] = "Selecciona Vigente o No vigente."

        ciclo = datos.get("ciclo")
        if ciclo not in (None, ""):
            texto = str(ciclo)
            if not re.fullmatch(r"[0-9]+", texto) or not 1 <= int(texto) <= 2147483647:
                errores["ciclo"] = "El ciclo debe ser un entero positivo o quedar vacío."


    if errores:
        raise ValidacionPersonaError(errores)


def validar_dni(valor):
    if not isinstance(valor, str) or not re.fullmatch(r"[0-9]{8}", valor):
        raise ValueError("El DNI debe tener exactamente 8 dígitos.")
    return valor


# Persona

class EstadoPersona(str, Enum):
    ACTIVA = "ACTIVA"
    INACTIVA = "INACTIVA"


@dataclass(kw_only=True)
class Persona:
    dni: str
    nombres: str
    apellidos: str
    correo: str
    telefono: str = ""
    estado: EstadoPersona = EstadoPersona.ACTIVA

    def __post_init__(self):
        self.estado = EstadoPersona(self.estado)
        validar_datos_persona(dict(vars(self), tipo=self.tipo))
        self.nombres = self.nombres.strip()
        self.apellidos = self.apellidos.strip()
        self.correo = self.correo.strip()
        self.telefono = self.telefono.strip()

    @property
    def documento_identidad(self):
        return self.dni

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"

    def esta_activa(self):
        return self.estado == EstadoPersona.ACTIVA


# Estudiante

ESTADOS_MATRICULA_VIGENTE = ("VIGENTE",)


def tiene_matricula_vigente(estado):
    return isinstance(estado, str) and estado == "VIGENTE"


@dataclass(kw_only=True)
class Estudiante(Persona):
    cui: str
    estado_matricula: str
    ciclo: int | None = None
    tipo = "ESTUDIANTE"

    def matricula_vigente(self):
        return self.esta_activa() and tiene_matricula_vigente(self.estado_matricula)


# Docente

@dataclass(kw_only=True)
class Docente(Persona):
    codigo_docente: str | None = None
    departamento_academico: str | None = None
    facultad: str | None = None
    escuela_profesional: str | None = None
    tipo = "DOCENTE"


# Administrativo

@dataclass(kw_only=True)
class Administrativo(Persona):
    codigo_empleado: str | None = None
    area: str | None = None
    tipo = "ADMINISTRATIVO"


# Fabrica persona

class FabricaPersona:
    @classmethod
    def construir(cls, datos):
        datos = dict(datos)
        if "dni" not in datos and "documento_identidad" in datos:
            datos["dni"] = datos["documento_identidad"]
        if datos.get("telefono") is None:
            datos["telefono"] = ""
        validar_datos_persona(datos)

        if datos["tipo"] == "ESTUDIANTE":
            ciclo = datos.get("ciclo")
            if ciclo in (None, ""):
                ciclo = None
            else:
                ciclo = int(ciclo)
            return Estudiante(
                dni=datos["dni"],
                nombres=datos["nombres"],
                apellidos=datos["apellidos"],
                correo=datos["correo"],
                telefono=datos.get("telefono", ""),
                cui=datos["cui"],
                estado=datos.get("estado", "ACTIVA"),
                estado_matricula=datos["estado_matricula"],
                ciclo=ciclo,
            )

        if datos["tipo"] == "DOCENTE":
            return Docente(
                dni=datos["dni"],
                nombres=datos["nombres"],
                apellidos=datos["apellidos"],
                correo=datos["correo"],
                telefono=datos.get("telefono", ""),
                estado=datos.get("estado", "ACTIVA"),
                codigo_docente=datos["codigo_docente"],
                departamento_academico=datos["departamento_academico"],
                facultad=datos["facultad"],
                escuela_profesional=datos["escuela_profesional"],
            )

        return Administrativo(
            dni=datos["dni"],
            nombres=datos["nombres"],
            apellidos=datos["apellidos"],
            correo=datos["correo"],
            telefono=datos.get("telefono", ""),
            estado=datos.get("estado", "ACTIVA"),
            codigo_empleado=datos["codigo_empleado"],
            area=datos["area"],
        )


# I repositorio persona

class IRepositorioPersona(ABC):
    @abstractmethod
    def registrar_persona(self, persona) -> Persona:
        """Escritura explícita. Devuelve Persona y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def consultar_persona(self, dni) -> Persona | None:
        raise NotImplementedError

    @abstractmethod
    def consultar_personas(self, filtros) -> ResultadoPersonas:
        raise NotImplementedError

    @abstractmethod
    def consultar_solicitantes(self, texto, limite=20) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def actualizar_persona(self, persona, dni_actual, id_usuario_actor=None, *, version) -> Persona:
        """Escritura explícita. Devuelve Persona y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def desactivar_persona(self, dni, id_usuario_actor=None) -> None:
        """Escritura explícita. Devuelve None y propaga errores de validación o integridad."""
        raise NotImplementedError


# Resultados de consulta

class ResumenPersonas(TypedDict):
    total: int
    activas: int
    inactivas: int


class ResultadoPersonas(TypedDict):
    personas: list[Persona]
    resumen: ResumenPersonas
    pagina: int
    paginas: int
    aviso: str
