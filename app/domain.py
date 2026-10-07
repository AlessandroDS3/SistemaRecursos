"""Reglas del catálogo, independientes de HTTP y de la base de datos."""
from dataclasses import dataclass
from datetime import date
from enum import Enum
import re
from uuid import uuid4


class TipoRecurso(str, Enum):
    LIBRO = "LIBRO"
    LAPTOP = "LAPTOP"
    PROYECTOR = "PROYECTOR"
    CARGADOR = "CARGADOR"
    MOUSE = "MOUSE"
    TABLET = "TABLET"
    OTRO = "OTRO"


class EstadoBienMaterial(str, Enum):
    DISPONIBLE = "DISPONIBLE"
    PRESTADO = "PRESTADO"
    RESERVADO = "RESERVADO"
    DANADO = "DANADO"
    MANTENIMIENTO = "MANTENIMIENTO"
    PERDIDO = "PERDIDO"


class ValidationError(ValueError):
    pass


def texto(data, field, maximum=120, required=True):
    value = data.get(field, "")
    if not isinstance(value, str):
        raise ValidationError(f"{field}: debe ser texto.")
    value = value.strip()
    if required and not value:
        raise ValidationError(f"{field}: es obligatorio.")
    if len(value) > maximum:
        raise ValidationError(f"{field}: máximo {maximum} caracteres.")
    return value


@dataclass(frozen=True)
class Recurso:
    nombre: str
    tipo: str
    marca: str
    modelo: str
    descripcion: str
    idCategoriaRef: int

    @classmethod
    def desde_datos(cls, data):
        if not isinstance(data, dict):
            raise ValidationError("El recurso debe ser un objeto.")
        tipo = texto(data, "tipo")
        if tipo not in TipoRecurso._value2member_map_:
            raise ValidationError("Tipo de recurso no válido.")
        categoria = data.get("idCategoriaRef")
        if type(categoria) is not int or categoria < 1:
            raise ValidationError("Selecciona una categoría válida.")
        return cls(texto(data, "nombre"), tipo, texto(data, "marca", 80, False),
                   texto(data, "modelo", 80, False), texto(data, "descripcion", 1000, False), categoria)


@dataclass(frozen=True)
class BienMaterial:
    codigoInventario: str
    numeroSerie: str
    fechaAdquisicion: str
    ubicacion: str
    estado: str = EstadoBienMaterial.DISPONIBLE.value

    @classmethod
    def desde_datos(cls, data):
        if not isinstance(data, dict):
            raise ValidationError("El bien material debe ser un objeto.")
        codigo = texto(data, "codigoInventario", 40).upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9._-]*", codigo):
            raise ValidationError("Código: utiliza letras sin tildes, números, punto, guion o guion bajo.")
        if data.get("estado", "DISPONIBLE") != "DISPONIBLE":
            raise ValidationError("Un nuevo bien inicia DISPONIBLE.")
        # Se generan al guardar; nunca se aceptan fecha o serie del cliente.
        return cls(codigo, "SR-" + uuid4().hex.upper(), date.today().isoformat(), texto(data, "ubicacion"))
