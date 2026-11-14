"""Préstamos: entrega, devolución, ampliación y colaboración transaccional."""
from __future__ import annotations
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from dominio.gestion_control.control import HorarioAtencion, LimiteArticulosPrestamo
from dominio.gestion_personas_usuarios.personas import tiene_matricula_vigente, validar_dni
from dominio.gestion_recursos.recursos import CondicionBien, EstadoBienMaterial
from dominio.compartido.validaciones import entero, instante_utc, texto
from enum import Enum
from typing import TypedDict


# Tipo prestamo

class TipoPrestamo(str, Enum):
    INDIVIDUAL = "INDIVIDUAL"
    GRUPAL = "GRUPAL"


# Validacion prestamo

class ConflictoPrestamoError(ValueError):
    pass


def validar_persona(persona):
    if persona.get("estado") != "ACTIVA":
        raise ValueError("La persona seleccionada está inactiva.")
    if persona.get("tipo") not in {"ESTUDIANTE", "DOCENTE", "ADMINISTRATIVO"}:
        raise ValueError("La persona no tiene un tipo institucional registrado.")
    if persona["tipo"] == "ESTUDIANTE" and not tiene_matricula_vigente(
        persona.get("estado_matricula")
    ):
        raise ValueError(
            "El estudiante debe tener matrícula vigente para participar en un préstamo."
        )


def lista_ids(valores, campo):
    if not isinstance(valores, (list, tuple)) or len(valores) > 100:
        raise ValueError(f"{campo}: selecciona hasta 100 elementos.")
    ids = [entero(v, campo) for v in valores]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{campo}: no se permiten elementos repetidos.")
    return ids


def lista_dnis(valores):
    if not isinstance(valores, (list, tuple)) or len(valores) > 100:
        raise ValueError("Selecciona hasta 100 participantes.")
    dnis = [validar_dni(valor) for valor in valores]
    if len(set(dnis)) != len(dnis):
        raise ValueError("No se permiten participantes repetidos.")
    return dnis


# Detalle prestamo

@dataclass(kw_only=True)
class DetallePrestamo:
    id_bien: int
    id_politica: int
    fecha_limite_devolucion: datetime
    condicion_entrega: CondicionBien = CondicionBien.BUENO
    observaciones_entrega: str = ""
    fecha_devolucion: datetime | None = None
    dni_encargado_devolucion: str | None = None
    condicion_devolucion: CondicionBien | None = None
    observaciones_devolucion: str | None = None
    id_detalle: int | None = None

    def __post_init__(self):
        self.id_bien = entero(self.id_bien, "Bien")
        self.id_politica = entero(self.id_politica, "Política")
        self.condicion_entrega = CondicionBien(self.condicion_entrega)
        self.observaciones_entrega = texto(self.observaciones_entrega, "Observaciones de entrega", 255)
        if self.fecha_devolucion is None:
            if any(valor is not None for valor in (self.dni_encargado_devolucion,
                    self.condicion_devolucion, self.observaciones_devolucion)):
                raise ValueError("La devolución debe tener fecha, encargado y condición juntos.")
        else:
            if not isinstance(self.fecha_devolucion, datetime):
                raise ValueError("La fecha de devolución no es válida.")
            self.dni_encargado_devolucion = validar_dni(self.dni_encargado_devolucion)
            self.condicion_devolucion = CondicionBien(self.condicion_devolucion)
            self.observaciones_devolucion = texto(self.observaciones_devolucion, "Observaciones de devolución", 255) or None

    def pendiente(self):
        return self.fecha_devolucion is None


# Participante prestamo

@dataclass(kw_only=True)
class ParticipantePrestamo:
    dni_persona: str
    rol_participacion: str = "Integrante"
    responsable: bool = False
    id_participante: int | None = None

    def __post_init__(self):
        self.dni_persona = validar_dni(self.dni_persona)
        self.rol_participacion = texto(self.rol_participacion, "Rol de participación", 60, True)


# Devolucion

@dataclass(kw_only=True)
class Devolucion:
    id_detalle: int
    dni_encargado: str
    condicion_devolucion: CondicionBien = CondicionBien.BUENO
    observaciones: str = ""

    def __post_init__(self):
        self.id_detalle = entero(self.id_detalle, "Detalle del préstamo")
        self.dni_encargado = validar_dni(self.dni_encargado)
        try:
            self.condicion_devolucion = CondicionBien(self.condicion_devolucion)
        except (ValueError, TypeError):
            raise ValueError("Selecciona bueno o dañado. Un bien perdido sigue pendiente de devolución.") from None
        self.observaciones = texto(self.observaciones, "Observaciones de devolución", 255)
        if self.condicion_devolucion == CondicionBien.DANADO and not self.observaciones:
            raise ValueError("Describe los daños del bien recibido.")

    @property
    def estado_bien(self):
        return (EstadoBienMaterial.DISPONIBLE if self.condicion_devolucion == CondicionBien.BUENO
                else EstadoBienMaterial.DANADO)


# Prestamo

class EstadoPrestamo(str, Enum):
    ACTIVO = "ACTIVO"
    VENCIDO = "VENCIDO"
    DEVUELTO = "DEVUELTO"
    PARCIALMENTE_DEVUELTO = "PARCIALMENTE_DEVUELTO"


@dataclass(kw_only=True)
class Prestamo:
    dni_persona: str
    dni_encargado: str
    tipo_prestamo: TipoPrestamo = TipoPrestamo.INDIVIDUAL
    observaciones: str = ""
    id_prestamo: int | None = None
    fecha_solicitud: datetime | None = None
    fecha_entrega: datetime | None = None
    estado: EstadoPrestamo = EstadoPrestamo.ACTIVO
    detalles: list = field(default_factory=list)
    participantes: list = field(default_factory=list)
    salida_solicitada: bool = False

    def __post_init__(self):
        self.dni_persona = validar_dni(self.dni_persona)
        self.dni_encargado = validar_dni(self.dni_encargado)
        try:
            self.tipo_prestamo = TipoPrestamo(self.tipo_prestamo)
            self.estado = EstadoPrestamo(self.estado)
        except (ValueError, TypeError):
            raise ValueError("El tipo o estado del préstamo no es válido.") from None
        self.observaciones = texto(self.observaciones, "Observaciones", 255)

    def agregar_detalle(self, detalle):
        for detalle_registrado in self.detalles:
            if detalle_registrado.id_bien == detalle.id_bien:
                raise ValueError("No se puede incluir el mismo bien dos veces.")
        self.detalles.append(detalle)

    def validar(self):
        if not self.detalles:
            raise ValueError("Selecciona al menos un bien para el préstamo.")
        ids_bienes = []
        for detalle in self.detalles:
            ids_bienes.append(detalle.id_bien)
        if len(set(ids_bienes)) != len(ids_bienes):
            raise ValueError("No se puede incluir el mismo bien dos veces.")
        dnis_participantes = []
        for participante in self.participantes:
            dnis_participantes.append(participante.dni_persona)
        if len(set(dnis_participantes)) != len(dnis_participantes):
            raise ValueError("Un participante no puede repetirse.")
        if self.tipo_prestamo == TipoPrestamo.INDIVIDUAL and self.participantes:
            raise ValueError("Los préstamos individuales no tienen participantes adicionales.")
        if self.tipo_prestamo == TipoPrestamo.GRUPAL:
            responsables = []
            for participante in self.participantes:
                if participante.responsable:
                    responsables.append(participante)
            if (
                len(dnis_participantes) < 2
                or len(responsables) != 1
                or responsables[0].dni_persona != self.dni_persona
            ):
                raise ValueError(
                    "El préstamo grupal necesita al solicitante como responsable y al menos otro participante."
                )

    def estado_actual(self, ahora=None):
        ahora = ahora or datetime.now(timezone.utc).replace(tzinfo=None)
        pendientes = []
        for detalle in self.detalles:
            if detalle.pendiente():
                pendientes.append(detalle)
        if not pendientes:
            return EstadoPrestamo.DEVUELTO
        for detalle in pendientes:
            if detalle.fecha_limite_devolucion < ahora:
                return EstadoPrestamo.VENCIDO
        if len(pendientes) < len(self.detalles):
            return EstadoPrestamo.PARCIALMENTE_DEVUELTO
        return EstadoPrestamo.ACTIVO

    def marcar_vencido(self, ahora=None):
        self.estado = self.estado_actual(ahora)
        return self.estado

    def registrar_devolucion(self, id_detalle, condicion, ahora=None, *, dni_encargado, observaciones=""):
        detalle = next((d for d in self.detalles if d.id_detalle == id_detalle), None)
        if detalle is None or not detalle.pendiente():
            raise ValueError("El bien no pertenece al préstamo o ya fue devuelto.")
        condicion = CondicionBien(condicion)
        detalle.dni_encargado_devolucion = validar_dni(dni_encargado)
        detalle.condicion_devolucion = condicion
        detalle.fecha_devolucion = ahora or datetime.now(timezone.utc).replace(tzinfo=None)
        detalle.observaciones_devolucion = texto(observaciones, "Observaciones de devolución", 255) or None
        self.estado = self.estado_actual(ahora)

    def validar_recepcion(self, devoluciones, estados_bienes):
        if not devoluciones or len({d.id_detalle for d in devoluciones}) != len(devoluciones):
            raise ValueError('Selecciona bienes distintos para registrar la devolución.')
        detalles = {d.id_detalle: d for d in self.detalles}
        for devolucion in devoluciones:
            detalle = detalles.get(devolucion.id_detalle)
            if detalle is None or not detalle.pendiente():
                raise ConflictoPrestamoError('Uno de los bienes no pertenece a este préstamo o ya fue devuelto. No se registró ninguna devolución.')
            if estados_bienes[detalle.id_bien] not in {'PRESTADO', 'PERDIDO'}:
                raise ConflictoPrestamoError('El estado actual de un bien no corresponde a un préstamo pendiente.')

    def validar_perdida(self, id_detalle, estados_bienes):
        detalle = next((d for d in self.detalles if d.id_detalle == id_detalle), None)
        if detalle is None or not detalle.pendiente() or estados_bienes[detalle.id_bien] != 'PRESTADO':
            raise ConflictoPrestamoError('Solo se puede reportar la pérdida de un bien prestado y pendiente de devolución.')
        return detalle


# Fabrica prestamo

class FabricaPrestamo:
    @classmethod
    def construir(cls, datos):
        prestamo = Prestamo(
            dni_persona=datos.get("dni_persona"),
            dni_encargado=datos.get("dni_encargado"),
            tipo_prestamo=datos.get("tipo_prestamo", "INDIVIDUAL"),
            observaciones=datos.get("observaciones", ""),
            salida_solicitada=datos.get("salida_solicitada", False),
        )
        for datos_detalle in datos.get("detalles", []):
            if isinstance(datos_detalle, DetallePrestamo):
                detalle = datos_detalle
            else:
                detalle = DetallePrestamo(**datos_detalle)
            prestamo.agregar_detalle(detalle)

        for datos_participante in datos.get("participantes", []):
            if isinstance(datos_participante, ParticipantePrestamo):
                participante = datos_participante
            else:
                participante = ParticipantePrestamo(**datos_participante)
            prestamo.participantes.append(participante)

        prestamo.validar()
        return prestamo


# Solicitud prestamo

@dataclass(kw_only=True)
class SolicitudPrestamo:
    dni_persona: str
    dni_encargado: str
    ids_bienes: list
    tipo_prestamo: TipoPrestamo = TipoPrestamo.INDIVIDUAL
    observaciones: str = ""
    participantes: list = field(default_factory=list)
    salida_solicitada: bool = False

    def __post_init__(self):
        self.dni_persona = validar_dni(self.dni_persona)
        self.dni_encargado = validar_dni(self.dni_encargado)
        self.ids_bienes = lista_ids(self.ids_bienes, "Bienes")
        if not self.ids_bienes:
            raise ValueError("Selecciona al menos un bien disponible.")
        self.tipo_prestamo = TipoPrestamo(self.tipo_prestamo)
        self.observaciones = texto(self.observaciones, "Observaciones", 255)
        self.participantes = [p if isinstance(p, ParticipantePrestamo) else ParticipantePrestamo(**p)
                              for p in self.participantes]

    def construir_prestamo(self, bienes, politicas, ahora, horario=None):
        return FabricaPrestamo.construir({
            "dni_persona": self.dni_persona, "dni_encargado": self.dni_encargado,
            "tipo_prestamo": self.tipo_prestamo, "observaciones": self.observaciones,
            "participantes": self.participantes, "salida_solicitada": self.salida_solicitada,
            "detalles": [{"id_bien": bien["id_bien"],
                          "id_politica": politicas[bien["id_categoria"]].id_politica,
                          "fecha_limite_devolucion": politicas[bien["id_categoria"]].fecha_limite(ahora, horario),
                          "condicion_entrega": "BUENO"} for bien in bienes],
        })


# Contexto entrega

@dataclass
class ContextoEntrega:
    personas: dict
    tiene_vencidos: bool
    tiene_sanciones: bool
    limite: LimiteArticulosPrestamo
    pendientes: int
    bienes: list
    tiene_entregas_pendientes: bool
    politicas: dict
    horario: HorarioAtencion | None
    ahora: datetime

    def construir_prestamo(self, solicitud, id_bien_reservado=None):
        participantes = {solicitud.dni_persona, *(p.dni_persona for p in solicitud.participantes)}
        if set(self.personas) != participantes | {solicitud.dni_encargado}:
            raise ValueError('Una de las personas seleccionadas ya no existe.')
        if self.personas[solicitud.dni_encargado]['estado'] != 'ACTIVA':
            raise ValueError('El encargado está inactivo.')
        for dni in participantes:
            validar_persona(self.personas[dni])
        if self.tiene_vencidos:
            raise ConflictoPrestamoError('La persona tiene un préstamo vencido pendiente de devolución.')
        if self.tiene_sanciones:
            raise ConflictoPrestamoError('El solicitante o un participante tiene una sanción activa.')
        self.limite.validar_entrega(self.pendientes, len(solicitud.ids_bienes))
        if {b['id_bien'] for b in self.bienes} != set(solicitud.ids_bienes):
            raise ValueError('Uno de los bienes seleccionados ya no existe.')
        for bien in self.bienes:
            esperado = 'RESERVADO' if bien['id_bien'] == id_bien_reservado else 'DISPONIBLE'
            if bien['estado'] != esperado:
                raise ConflictoPrestamoError('Uno de los bienes dejó de estar disponible. No se registró la entrega.')
        if self.tiene_entregas_pendientes:
            raise ConflictoPrestamoError('Uno de los bienes tiene una entrega pendiente, aunque su inventario indique disponible. Revisa su préstamo antes de una nueva entrega.')
        if {b['id_categoria'] for b in self.bienes} != set(self.politicas):
            raise ValueError('Falta una política para el tipo de persona y una de las categorías seleccionadas.')
        if solicitud.salida_solicitada and any(not p.permite_salida for p in self.politicas.values()):
            raise ValueError('Una de las políticas no permite sacar el bien de la institución.')
        if self.horario is None:
            raise ValueError('Configura el horario general de atención en Políticas antes de registrar entregas.')
        self.horario.cierre_para_entrega(self.ahora)
        return solicitud.construir_prestamo(self.bienes, self.politicas, self.ahora, self.horario)


# Ampliacion prestamo

class ConflictoAmpliacionError(ValueError):
    pass


@dataclass(kw_only=True)
class AmpliacionPrestamo:
    """Regla de ampliación directa; no representa una tabla ni una solicitud."""
    cantidad: int
    unidad: str
    fecha_limite_anterior: datetime
    motivo: str = ''

    def __post_init__(self):
        try:
            self.cantidad = entero(self.cantidad, 'Tiempo adicional')
        except ValueError:
            raise ValueError('Indica una cantidad entera y positiva de tiempo adicional.') from None
        if self.unidad not in ('HORAS', 'DIAS'):
            raise ValueError('Selecciona horas o días para la ampliación.')
        self.fecha_limite_anterior = instante_utc(self.fecha_limite_anterior, 'Fecha actual de devolución')
        self.motivo = texto(self.motivo, 'Observación de la ampliación', 120)

    def calcular_fecha(self, detalle, ahora, politica, horario=None):
        if detalle['fecha_devolucion'] is not None or detalle['estado_actual'] != 'PRESTADO':
            raise ConflictoAmpliacionError('Solo se pueden ampliar bienes prestados y pendientes de devolución.')
        actual = detalle['fecha_limite_devolucion']
        if actual != self.fecha_limite_anterior:
            raise ConflictoAmpliacionError('El plazo cambió. Recarga el préstamo antes de ampliar de nuevo.')
        if actual <= ahora:
            raise ConflictoAmpliacionError('El plazo del bien ya venció; no se puede ampliar.')
        segundos = self.cantidad * (3600 if self.unidad == 'HORAS' else 86400)
        maximo = politica.plazo_maximo * (3600 if politica.unidad_plazo == 'HORAS' else 86400)
        if segundos > maximo:
            raise ValueError('La ampliación puede añadir como máximo otro plazo de la política del recurso.')
        if politica.unidad_plazo == 'HORAS' and horario is None:
            raise ValueError('Configura el horario de atención antes de ampliar un préstamo por horas.')
        try:
            nueva = actual + timedelta(seconds=segundos)
            limite = politica.fecha_limite(actual, horario)
        except OverflowError:
            raise ValueError('La nueva fecha de devolución está fuera del rango permitido.') from None
        if nueva > limite:
            raise ValueError('La ampliación debe respetar el cierre de atención.')
        return nueva


# I operacion prestamo

class IOperacionPrestamo(ABC):
    """Acceso a datos de una escritura; sus bloqueos duran hasta salir de la transacción."""

    @abstractmethod
    def cargar_entrega(self, solicitud):
        raise NotImplementedError

    @abstractmethod
    def guardar_entrega(self, prestamo, bienes, ahora):
        raise NotImplementedError

    @abstractmethod
    def cargar_recepcion(self, id_prestamo, dni_encargado):
        raise NotImplementedError

    @abstractmethod
    def guardar_devoluciones(self, prestamo, anterior, devoluciones, detalles, dni_encargado, ahora):
        raise NotImplementedError

    @abstractmethod
    def registrar_sancion_vencimiento(self, detalle, ahora):
        raise NotImplementedError

    @abstractmethod
    def guardar_perdida(self, prestamo, detalle, motivo, dni_encargado):
        raise NotImplementedError

    @abstractmethod
    def cargar_vencidos(self, dni=None):
        raise NotImplementedError

    @abstractmethod
    def guardar_estado(self, prestamo, anterior, observacion, dni_encargado):
        raise NotImplementedError

    @abstractmethod
    def ahora(self):
        raise NotImplementedError

    @abstractmethod
    def cargar_cuenta_ampliacion(self, id_usuario):
        raise NotImplementedError

    @abstractmethod
    def cargar_politica_ampliacion(self, id_politica):
        raise NotImplementedError

    @abstractmethod
    def guardar_fecha_limite(self, id_detalle, anterior, nueva):
        raise NotImplementedError


# I repositorio prestamo

class IRepositorioPrestamo(ABC):
    @abstractmethod
    def transaccion(self) -> AbstractContextManager[IOperacionPrestamo]:
        """Abre una operación de escritura sin exponer conexiones ni cursores."""
        raise NotImplementedError

    @abstractmethod
    def consultar_prestamo(self, id_prestamo) -> PrestamoDetalle | None:
        raise NotImplementedError

    @abstractmethod
    def consultar_resumen_prestamos(self, dni=None) -> ResumenPrestamos:
        raise NotImplementedError

    @abstractmethod
    def consultar_prestamos(self, filtros=None, dni=None) -> list[PrestamoListado]:
        raise NotImplementedError


# Resultados de consulta

class PrestamoConsulta(TypedDict):
    id_prestamo: int
    dni_persona: str
    dni_encargado: str
    tipo_prestamo: str
    estado: str
    fecha_solicitud: datetime
    fecha_entrega: datetime | None
    observaciones: str | None
    solicitante: str
    documento_identidad: str
    cui: str | None


class DetalleEntregaConsulta(TypedDict):
    id_detalle: int
    id_bien: int
    id_politica: int
    condicion_entrega: str
    condicion_devolucion: str | None
    fecha_devolucion: datetime | None
    dni_encargado_devolucion: str | None
    observaciones_entrega: str | None
    observaciones_devolucion: str | None
    fecha_limite_devolucion: datetime
    estado_sancion_vencimiento: str | None
    justificacion_levantamiento: str | None
    codigo_inventario: str
    estado_actual: str
    recurso: str


class ParticipanteConsulta(TypedDict):
    dni_persona: str
    nombre: str
    responsable: bool
    rol_participacion: str


class HistorialPrestamoConsulta(TypedDict):
    estado_anterior: str | None
    estado_nuevo: str
    fecha: datetime
    dni_responsable: str
    observacion: str | None
    responsable: str


class PrestamoDetalle(PrestamoConsulta):
    encargado: str
    detalles: list[DetalleEntregaConsulta]
    participantes: list[ParticipanteConsulta]
    historial: list[HistorialPrestamoConsulta]


class PrestamoListado(PrestamoConsulta):
    total: int
    devueltos: int | Decimal
    pendientes: int | Decimal
    perdidos: int | Decimal
    proximo_vencimiento: datetime | None


class ResultadoPrestamos(TypedDict):
    prestamos: list[PrestamoListado]


class ResumenPrestamos(TypedDict):
    prestamos_pendientes: int
    prestamos_vencidos: int
