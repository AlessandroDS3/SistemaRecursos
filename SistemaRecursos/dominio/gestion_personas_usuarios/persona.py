"""Datos y reglas de una persona, incluidos sus datos institucionales."""

from dataclasses import asdict, dataclass, fields
import re
from typing import TypedDict

from dominio.compartido.codigos import Codigo
from dominio.compartido.validacion import validar_dni, validar_entero, validar_texto

TIPOS_PERSONA = ('ESTUDIANTE', 'DOCENTE', 'ADMINISTRATIVO')
ESTADOS_PERSONA = ('ACTIVA', 'INACTIVA')


class EstadoMatricula(Codigo):
    VIGENTE = 'VIGENTE'
    NO_VIGENTE = 'NO_VIGENTE'


ESTADOS_MATRICULA = tuple(EstadoMatricula)
LONGITUD_CODIGO_INSTITUCIONAL = 20
CAMPOS_TIPO = {
    'ESTUDIANTE': ('cui', 'ciclo', 'estado_matricula'),
    'DOCENTE': ('codigo_docente', 'departamento_academico', 'facultad', 'escuela_profesional'),
    'ADMINISTRATIVO': ('codigo_empleado', 'area'),
}


@dataclass(kw_only=True)
class Persona:
    dni: str
    nombres: str
    apellidos: str
    correo: str
    tipo: str
    estado: str = 'ACTIVA'
    telefono: str = ''
    cui: str = ''
    ciclo: int | None = None
    estado_matricula: EstadoMatricula = EstadoMatricula.VIGENTE
    codigo_docente: str = ''
    departamento_academico: str = ''
    facultad: str = ''
    escuela_profesional: str = ''
    codigo_empleado: str = ''
    area: str = ''

    def __post_init__(self):
        self.dni = validar_dni(self.dni)
        self.nombres = validar_texto(self.nombres, 'Nombres', 100, True)
        self.apellidos = validar_texto(self.apellidos, 'Apellidos', 100, True)
        self.correo = validar_texto(self.correo, 'Correo', 120, self.tipo != 'ESTUDIANTE')
        self.telefono = validar_texto(self.telefono, 'Teléfono', 20)
        if self.correo and not re.fullmatch(r'[^\s@]+@[^.\s@]+(?:\.[^.\s@]+)+', self.correo):
            raise ValueError('Introduce un correo válido.')
        if self.tipo not in TIPOS_PERSONA or self.estado not in ESTADOS_PERSONA:
            raise ValueError('Tipo o estado de persona inválido.')
        if self.tipo == 'ESTUDIANTE':
            self.cui = validar_dni(self.cui)
            self.ciclo = validar_entero(self.ciclo, 'Ciclo') if self.ciclo not in (None, '') else None
            if self.estado_matricula not in ESTADOS_MATRICULA:
                raise ValueError('Selecciona una matrícula válida.')
            self.estado_matricula = EstadoMatricula(self.estado_matricula)
        else:
            for campo in CAMPOS_TIPO[self.tipo]:
                setattr(
                    self,
                    campo,
                    validar_texto(
                        getattr(self, campo),
                        campo.replace('_', ' ').capitalize(),
                        LONGITUD_CODIGO_INSTITUCIONAL if campo.startswith('codigo_') else 100,
                        True,
                    ),
                )

    @classmethod
    def desde_datos(cls, datos: dict) -> 'Persona':
        permitidos = {campo.name for campo in fields(cls)}
        valores = {k: v for k, v in datos.items() if k in permitidos and v is not None}
        for campo in ('dni', 'nombres', 'apellidos', 'correo', 'tipo'):
            valores.setdefault(campo, None)
        return cls(**valores)

    @property
    def nombre_completo(self) -> str:
        return f'{self.nombres} {self.apellidos}'

    def como_diccionario(self) -> dict:
        return asdict(self)


class PersonaParaPrestamo(TypedDict):
    dni: str
    nombres: str
    apellidos: str
    estado: str
    tipo: str | None
    estado_matricula: str | None


def validar_elegibilidad_del_solicitante(persona: PersonaParaPrestamo | None) -> PersonaParaPrestamo:
    if persona is None or persona['estado'] != 'ACTIVA':
        raise ValueError('La persona debe estar activa.')
    if persona.get('tipo') not in TIPOS_PERSONA:
        raise ValueError('La persona no tiene un tipo institucional válido.')
    if persona['tipo'] == 'ESTUDIANTE' and persona.get('estado_matricula') != EstadoMatricula.VIGENTE:
        raise ValueError('El estudiante debe tener matrícula vigente.')
    return persona
