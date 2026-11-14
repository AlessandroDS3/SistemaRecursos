"""Catálogo y ejemplares físicos: datos, estados y contratos."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from dominio.compartido.validaciones import entero, fecha, texto
from enum import Enum
from typing import Any, TypedDict


class ConflictoRecursoError(ValueError):
    pass


# Categoria recurso

@dataclass(kw_only=True)
class CategoriaRecurso:
    nombre: str
    descripcion: str = ""
    id_categoria: int | None = None

    def __post_init__(self):
        self.nombre = texto(self.nombre, "Nombre de categoría", 80, True)
        self.descripcion = texto(self.descripcion, "Descripción", 255)


# Recurso

@dataclass(kw_only=True)
class Recurso:
    nombre: str
    id_categoria: int
    marca: str = ""
    modelo: str = ""
    descripcion: str | None = None
    id_recurso: int | None = None

    def __post_init__(self):
        self.nombre = texto(self.nombre, "Nombre del recurso", 120, True)
        self.id_categoria = entero(self.id_categoria, "Categoría")
        self.marca = texto(self.marca, "Marca", 80)
        self.modelo = texto(self.modelo, "Modelo", 80)
        self.descripcion = texto(self.descripcion, "Descripción", 255) or None

    def clasificar(self, categoria):
        self.id_categoria = entero(categoria.id_categoria, "Categoría")


# Bien material

class EstadoBienMaterial(str, Enum):
    DISPONIBLE = "DISPONIBLE"
    PRESTADO = "PRESTADO"
    RESERVADO = "RESERVADO"
    DANADO = "DANADO"
    MANTENIMIENTO = "MANTENIMIENTO"
    PERDIDO = "PERDIDO"


ESTADOS_FUERA_SERVICIO = frozenset({
    EstadoBienMaterial.DANADO,
    EstadoBienMaterial.MANTENIMIENTO,
    EstadoBienMaterial.PERDIDO,
})


ESTADOS_CAMBIO_MANUAL = ESTADOS_FUERA_SERVICIO | {
    EstadoBienMaterial.DISPONIBLE
}


ESTADOS_GESTION_PRESTAMOS = frozenset({
    EstadoBienMaterial.PRESTADO,
    EstadoBienMaterial.RESERVADO,
})


class CondicionBien(str, Enum):
    BUENO = "BUENO"
    DANADO = "DANADO"


ESTADOS_TRAS_RECEPCION = frozenset({
    EstadoBienMaterial.DISPONIBLE,
    EstadoBienMaterial.DANADO,
    EstadoBienMaterial.MANTENIMIENTO,
})


TRANSICIONES_PERMITIDAS = {
    EstadoBienMaterial.DISPONIBLE: (
        ESTADOS_FUERA_SERVICIO | ESTADOS_GESTION_PRESTAMOS
    ),
    EstadoBienMaterial.PRESTADO: (
        ESTADOS_TRAS_RECEPCION | {EstadoBienMaterial.PERDIDO}
    ),
    EstadoBienMaterial.RESERVADO: {
        EstadoBienMaterial.DISPONIBLE,
        EstadoBienMaterial.PRESTADO,
    },
    EstadoBienMaterial.DANADO: {
        EstadoBienMaterial.DISPONIBLE,
        EstadoBienMaterial.MANTENIMIENTO,
        EstadoBienMaterial.PERDIDO,
    },
    EstadoBienMaterial.MANTENIMIENTO: {
        EstadoBienMaterial.DISPONIBLE,
        EstadoBienMaterial.DANADO,
        EstadoBienMaterial.PERDIDO,
    },
    EstadoBienMaterial.PERDIDO: ESTADOS_TRAS_RECEPCION,
}


@dataclass(kw_only=True)
class BienMaterial:
    id_recurso: int
    codigo_inventario: str
    fecha_adquisicion: date | None = None
    numero_serie: str = ""
    descripcion_bien: str | None = None
    ubicacion: str = ""
    estado: EstadoBienMaterial = EstadoBienMaterial.DISPONIBLE
    id_bien: int | None = None

    def __post_init__(self):
        self.id_recurso = entero(self.id_recurso, "Recurso")
        self.codigo_inventario = texto(self.codigo_inventario, "Código de inventario", 40, True)
        self.numero_serie = texto(self.numero_serie, "Número de serie", 60)
        self.descripcion_bien = texto(self.descripcion_bien, "Descripción del bien", 255) or None
        self.ubicacion = texto(self.ubicacion, "Ubicación", 120)
        self.fecha_adquisicion = (None if self.fecha_adquisicion in (None, "")
                                  else fecha(self.fecha_adquisicion, "Fecha de adquisición"))
        if self.fecha_adquisicion is not None and self.fecha_adquisicion > date.today():
            raise ValueError("La fecha de adquisición no puede ser futura.")
        self.estado = EstadoBienMaterial(self.estado)

    def esta_disponible(self):
        return self.estado == EstadoBienMaterial.DISPONIBLE

    def validar_disponible(self):
        if not self.esta_disponible():
            raise ValueError("El bien no está disponible.")

    def cambiar_estado(self, estado):
        try:
            nuevo = EstadoBienMaterial(estado)
        except (ValueError, TypeError):
            raise ValueError("El estado solicitado no es válido.") from None
        if nuevo not in TRANSICIONES_PERMITIDAS[self.estado]:
            raise ValueError(f"No se puede cambiar de {self.estado.value} a {nuevo.value}.")
        self.estado = nuevo


# Fabrica recurso

def crear_recurso(datos):
    return Recurso(
        nombre=datos.get("nombre"),
        id_categoria=datos.get("id_categoria"),
        marca=datos.get("marca", ""),
        modelo=datos.get("modelo", ""),
        descripcion=datos.get("descripcion", ""),
        id_recurso=datos.get("id_recurso"),
    )


# Fabrica bien material

def crear_bien_material(datos):
    return BienMaterial(
        id_recurso=datos.get("id_recurso"),
        codigo_inventario=datos.get("codigo_inventario"),
        fecha_adquisicion=datos.get("fecha_adquisicion"),
        numero_serie=datos.get("numero_serie", ""),
        descripcion_bien=datos.get("descripcion_bien", ""),
        ubicacion=datos.get("ubicacion", ""),
        estado=datos.get("estado", "DISPONIBLE"),
        id_bien=datos.get("id_bien"),
    )


# I repositorio recurso

class IRepositorioRecurso(ABC):
    @abstractmethod
    def registrar_recurso(self, recurso) -> Recurso:
        """Guarda un nuevo recurso."""
        raise NotImplementedError

    @abstractmethod
    def registrar_recurso_con_bien(self, recurso, datos_bien) -> Recurso:
        """Guarda un nuevo recurso junto con su primer bien."""
        raise NotImplementedError

    @abstractmethod
    def consultar_recurso(self, id_recurso) -> Recurso | None:
        """Busca un recurso por su ID; devuelve None si no existe."""
        raise NotImplementedError

    @abstractmethod
    def actualizar_recurso(self, recurso) -> Recurso:
        """Actualiza los datos de un recurso."""
        raise NotImplementedError

    @abstractmethod
    def eliminar_recurso(self, id_recurso) -> None:
        """Elimina un recurso."""
        raise NotImplementedError

    @abstractmethod
    def consultar_recursos(self, filtros=None) -> list[RecursoListado]:
        """Lista los recursos según los filtros."""
        raise NotImplementedError

    @abstractmethod
    def consultar_categorias(self) -> list[CategoriaRecurso]:
        """Lista las categorías de recursos."""
        raise NotImplementedError

    @abstractmethod
    def consultar_categoria(self, id_categoria) -> CategoriaRecurso | None:
        """Busca una categoría por su ID; devuelve None si no existe."""
        raise NotImplementedError

    @abstractmethod
    def registrar_categoria(self, categoria) -> CategoriaRecurso:
        """Guarda una nueva categoría."""
        raise NotImplementedError

    @abstractmethod
    def actualizar_categoria(self, categoria) -> CategoriaRecurso:
        """Actualiza los datos de una categoría."""
        raise NotImplementedError

    @abstractmethod
    def eliminar_categoria(self, id_categoria) -> None:
        """Elimina una categoría."""
        raise NotImplementedError


# I repositorio bien material

class IRepositorioBienMaterial(ABC):
    @abstractmethod
    def registrar_bien_material(self, bien_material) -> BienMaterial:
        """Guarda un nuevo bien."""
        raise NotImplementedError

    @abstractmethod
    def existen_por_recurso(self, id_recurso) -> bool:
        """Indica si el recurso tiene bienes registrados."""
        raise NotImplementedError

    @abstractmethod
    def consultar_bien_material(self, id_bien) -> BienMaterial | None:
        """Busca un bien por su ID; devuelve None si no existe."""
        raise NotImplementedError

    @abstractmethod
    def actualizar_bien_material(self, bien_material) -> BienMaterial:
        """Actualiza los datos de un bien."""
        raise NotImplementedError

    @abstractmethod
    def eliminar_bien_material(self, id_bien) -> None:
        """Elimina un bien."""
        raise NotImplementedError

    @abstractmethod
    def contar_disponibles(self) -> int:
        """Cuenta los bienes disponibles."""
        raise NotImplementedError

    @abstractmethod
    def consultar_bienes_por_recurso(self, id_recurso=None) -> list[BienListado]:
        """Lista los bienes de un recurso, o todos si no se indica uno."""
        raise NotImplementedError

    @abstractmethod
    def consultar_bienes_materiales(self, filtros) -> ResultadoBienes:
        """Consulta los bienes y su resumen según los filtros."""
        raise NotImplementedError

    @abstractmethod
    def consultar_bienes_disponibles(self, texto="", id_recurso=None) -> list[BienDisponible]:
        """Busca bienes disponibles por texto y recurso."""
        raise NotImplementedError

    @abstractmethod
    def cambiar_estado_bien_material(
        self,
        id_bien,
        estado,
        motivo,
        dni_responsable,
        estado_esperado,
    ) -> BienMaterial:
        """Cambia el estado de un bien y registra el motivo y el responsable."""
        raise NotImplementedError

    @abstractmethod
    def consultar_prestamo_pendiente(self, id_bien) -> int | None:
        """Devuelve el ID del préstamo pendiente del bien, o None si no tiene."""
        raise NotImplementedError

    @abstractmethod
    def consultar_historial_bien_material(self, id_bien) -> list[dict[str, Any]]:
        """Consulta el historial de estados del bien."""
        raise NotImplementedError


# Resultados de consulta

class RecursoListado(TypedDict):
    id_recurso: int
    id_categoria: int
    nombre: str
    marca: str | None
    modelo: str | None
    descripcion: str | None
    categoria_nombre: str
    total_bienes: int
    disponibles: int | Decimal


class BienListado(TypedDict):
    id_bien: int
    id_recurso: int
    codigo_inventario: str
    estado: str
    fecha_adquisicion: date | None
    recurso_nombre: str
    numero_serie: str | None
    ubicacion: str | None
    descripcion_bien: str | None


class BienDisponible(TypedDict):
    id_categoria: int
    id_bien: int
    id_recurso: int
    codigo_inventario: str
    ubicacion: str | None
    recurso_nombre: str


class ResumenBienes(TypedDict):
    total: int
    disponibles: int
    prestados: int
    mantenimiento: int


class ResultadoBienes(TypedDict):
    bienes: list[BienListado]
    resumen: ResumenBienes


class ResultadoRecursos(TypedDict):
    recursos: list[RecursoListado]
