"""Proyecciones de lectura y contenedores. No son entidades para registrar cambios.

Los SELECT pueden incluir columnas adicionales; los campos declarados son el contrato mínimo.
Las consultas individuales de repositorio devuelven None cuando no existe la entidad;
los servicios convierten esa ausencia en LookupError. Los listados vacíos devuelven [].
"""
from datetime import date, datetime
from decimal import Decimal
from typing import TypedDict
from dominio.gestion_personas_usuarios.persona import Persona


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

class ResultadoRecursos(TypedDict):
    recursos: list[RecursoListado]

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

class ReservaConsulta(TypedDict):
    id_reserva: int
    dni_persona: str
    id_recurso: int
    estado: str
    tipo_gestion: str
    fecha_solicitud: datetime
    fecha_requerida: datetime
    solicitante: str
    recurso: str

class ReservaDetalle(ReservaConsulta):
    historial: list[dict[str, object]]

class ResultadoReservas(TypedDict):
    reservas: list[ReservaConsulta]
    total: int


class CuentaParaRol(TypedDict):
    id_usuario: int
    dni_persona: str
    nombres: str
    apellidos: str
    cui: str | None
    nombre_usuario: str
    nombre_rol: str
    estado_cuenta: str


class IntegranteReporte(TypedDict):
    dni: str
    nombre: str
    responsable: bool


class FilaReportePrestamo(TypedDict):
    id_prestamo: int
    id_detalle: int
    tipo_prestamo: str
    estado: str
    dni_persona: str
    solicitante: str
    tipo_persona: str
    codigo_inventario: str
    recurso: str
    fecha_entrega: datetime
    fecha_limite_devolucion: datetime
    fecha_devolucion: datetime | None
    condicion_devolucion: str | None
    situacion: str
    integrantes: list[IntegranteReporte]


class ResumenReportePrestamos(TypedDict):
    prestamos: int
    bienes: int
    devueltos: int
    pendientes: int
    vencidos: int


class ResultadoReportePrestamos(TypedDict):
    filas: list[FilaReportePrestamo]
    resumen: ResumenReportePrestamos
    pagina: int
    paginas: int
