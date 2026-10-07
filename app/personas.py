"""Dominio y aplicación del registro inicial de personas."""
from dataclasses import dataclass
from .domain import texto, ValidationError
import re

TIPOS = ('ESTUDIANTE', 'DOCENTE', 'ADMINISTRATIVO')
CAMPOS = {
    'ESTUDIANTE': ('codigoEstudiante', 'matricula', 'ciclo', 'semestreAcademico', 'estadoMatricula'),
    'DOCENTE': ('codigoDocente', 'departamentoAcademico', 'facultad', 'escuelaProfesional'),
    'ADMINISTRATIVO': ('codigoEmpleado', 'area'),
}

@dataclass(frozen=True)
class Persona:
    nombres: str
    apellidos: str
    documentoIdentidad: str
    correo: str
    telefono: str
    tipo: str
    detalles: dict
    estado: str = 'ACTIVA'

    @classmethod
    def desde_datos(cls, data):
        if not isinstance(data, dict):
            raise ValidationError('Se requiere una persona válida.')
        tipo = texto(data, 'tipo')
        if tipo not in TIPOS:
            raise ValidationError('Selecciona un tipo de persona válido.')
        documento = texto(data, 'documentoIdentidad', 20).upper()
        if not re.fullmatch(r'[A-Z0-9][A-Z0-9-]{3,19}', documento):
            raise ValidationError('Documento: entre 4 y 20 letras, números o guiones.')
        correo = texto(data, 'correo', 160)
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', correo):
            raise ValidationError('Escribe un correo válido.')
        telefono = texto(data, 'telefono', 25, False)
        if telefono and not re.fullmatch(r'[+0-9 ()-]{6,25}', telefono):
            raise ValidationError('El teléfono no tiene un formato válido.')
        detalles = {}
        for campo in CAMPOS[tipo]:
            if campo == 'ciclo':
                valor = data.get(campo)
                if type(valor) is not int or not 1 <= valor <= 20:
                    raise ValidationError('El ciclo debe ser un número entre 1 y 20.')
            else:
                valor = texto(data, campo, 120, campo == CAMPOS[tipo][0])
                if campo == CAMPOS[tipo][0]:
                    valor = valor.upper()
            detalles[campo] = valor
        # Las nuevas personas se registran activas; no existen cuentas de acceso todavía.
        return cls(texto(data, 'nombres'), texto(data, 'apellidos'), documento,
                   correo, telefono, tipo, detalles)

class GestionPersonasService:
    def __init__(self, repository):
        self.repository = repository

    def registrar(self, data):
        return self.repository.crear_persona(Persona.desde_datos(data))
