"""Políticas, horario, incidencias y sanciones."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from dominio.personas import TipoPersona, validar_dni
from dominio.validaciones import entero, texto
from enum import Enum


# Horario atencion

ZONA_INSTITUCION = timezone(timedelta(hours=-5))


def hora_valida(valor):
    if isinstance(valor, timedelta):
        segundos = valor.total_seconds()
        if not 0 <= segundos < 86400 or segundos % 60:
            raise ValueError('El horario debe indicar horas y minutos válidos.')
        valor = time(int(segundos // 3600), int(segundos % 3600 // 60))
    if isinstance(valor, str):
        try:
            valor = time.fromisoformat(valor)
        except ValueError:
            raise ValueError('Indica una hora válida para la atención.') from None
    if not isinstance(valor, time) or valor.tzinfo or valor.second or valor.microsecond:
        raise ValueError('El horario debe indicar horas y minutos válidos.')
    return valor


@dataclass(kw_only=True)
class HorarioAtencion:
    hora_apertura: time = time(8)
    hora_cierre: time = time(16)

    def __post_init__(self):
        self.hora_apertura = hora_valida(self.hora_apertura)
        self.hora_cierre = hora_valida(self.hora_cierre)
        if self.hora_apertura >= self.hora_cierre:
            raise ValueError('La hora de cierre debe ser posterior a la apertura.')

    @property
    def apertura_texto(self):
        return self.hora_apertura.strftime('%H:%M')

    @property
    def cierre_texto(self):
        return self.hora_cierre.strftime('%H:%M')

    def cierre_para_entrega(self, fecha_entrega):
        fecha_utc = fecha_entrega.replace(tzinfo=timezone.utc) if fecha_entrega.tzinfo is None else fecha_entrega
        local = fecha_utc.astimezone(ZONA_INSTITUCION)
        if not self.hora_apertura <= local.time() < self.hora_cierre:
            raise ValueError(f'La atención es de {self.apertura_texto} a {self.cierre_texto}. Registra la entrega dentro de ese horario.')
        cierre = datetime.combine(local.date(), self.hora_cierre, ZONA_INSTITUCION).astimezone(timezone.utc)
        return cierre.replace(tzinfo=None) if fecha_entrega.tzinfo is None else cierre.astimezone(fecha_entrega.tzinfo)

    def limitar_prestamo_por_horas(self, fecha_entrega, fecha_limite):
        return min(fecha_limite, self.cierre_para_entrega(fecha_entrega))


# Politica prestamo

@dataclass(kw_only=True)
class PoliticaPrestamo:
    tipo_persona: TipoPersona
    id_categoria: int
    plazo_maximo: int
    unidad_plazo: str
    permite_salida: bool = False
    id_politica: int | None = None

    def __post_init__(self):
        try:
            self.tipo_persona = TipoPersona(self.tipo_persona)
        except (ValueError, TypeError):
            raise ValueError("Selecciona un tipo de persona válido.") from None
        self.id_categoria = entero(self.id_categoria, "Categoría")
        if self.unidad_plazo not in ("HORAS", "DIAS"):
            raise ValueError("Selecciona horas o días para el plazo.")

        limite = 87600 if self.unidad_plazo == "HORAS" else 3650
        if (
            isinstance(self.plazo_maximo, bool)
            or not isinstance(self.plazo_maximo, int)
            or not 1 <= self.plazo_maximo <= limite
        ):
            unidad = "horas" if self.unidad_plazo == "HORAS" else "días"
            raise ValueError(f"El plazo debe ser un entero entre 1 y {limite} {unidad}.")
        self.permite_salida = bool(self.permite_salida)

    def aplica_a(self, tipo_persona, id_categoria):
        return self.tipo_persona == tipo_persona and self.id_categoria == id_categoria

    @property
    def plazo_texto(self):
        if self.unidad_plazo == "HORAS":
            unidad = "hora" if self.plazo_maximo == 1 else "horas"
        else:
            unidad = "día" if self.plazo_maximo == 1 else "días"
        return f"{self.plazo_maximo} {unidad}"

    def fecha_limite(self, fecha_entrega, horario=None):
        if self.unidad_plazo == "HORAS":
            duracion = timedelta(hours=self.plazo_maximo)
        else:
            duracion = timedelta(days=self.plazo_maximo)
        limite = fecha_entrega + duracion
        if self.unidad_plazo == 'HORAS' and horario is not None:
            return horario.limitar_prestamo_por_horas(fecha_entrega, limite)
        return limite


@dataclass(kw_only=True)
class LimiteArticulosPrestamo:
    tipo_persona: TipoPersona
    maximo_articulos: int | None = None

    def __post_init__(self):
        self.tipo_persona = TipoPersona(self.tipo_persona)
        if self.maximo_articulos is not None:
            self.maximo_articulos = entero(self.maximo_articulos, 'Máximo de artículos')
            if self.maximo_articulos > 2147483647:
                raise ValueError('El máximo de artículos es demasiado grande.')

    def validar_entrega(self, pendientes: int, nuevos: int) -> None:
        if self.maximo_articulos is None:
            raise ValueError(f'El administrador debe configurar el máximo de artículos para {self.tipo_persona.value.lower()} en Políticas.')
        disponibles = max(0, self.maximo_articulos - pendientes)
        if nuevos > disponibles:
            raise ValueError(f'La persona tiene {pendientes} artículo(s) pendiente(s). Su máximo general es {self.maximo_articulos}. '
                             f'Solo puede recibir {disponibles} artículo(s) más; seleccionaste {nuevos}.')


# Politica vencimiento reserva

@dataclass(kw_only=True)
class PoliticaVencimientoReserva:
    plazo_espera: int = 2
    unidad_espera: str = "DIAS"
    plazo_retiro: int = 24
    unidad_retiro: str = "HORAS"

    def __post_init__(self):
        self.plazo_espera = self._validar_plazo(self.plazo_espera, self.unidad_espera, "Solicitudes pendientes")
        self.plazo_retiro = self._validar_plazo(self.plazo_retiro, self.unidad_retiro, "Reservas listas para retiro")

    @staticmethod
    def _validar_plazo(plazo, unidad, nombre):
        if unidad not in ("HORAS", "DIAS"):
            raise ValueError(f"{nombre}: selecciona horas o días.")
        try:
            numero = int(plazo)
            if isinstance(plazo, bool) or str(numero) != str(plazo).strip():
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError(f"{nombre}: introduce un plazo entero válido.") from None
        limite = 720 if unidad == "HORAS" else 30
        if not 1 <= numero <= limite:
            raise ValueError(f"{nombre}: el plazo debe estar entre 1 y {limite} {unidad.lower()}.")
        return numero

    @staticmethod
    def _sumar(fecha, plazo, unidad):
        if not isinstance(fecha, datetime):
            raise ValueError("La fecha inicial del vencimiento no es válida.")
        return fecha + (timedelta(hours=plazo) if unidad == "HORAS" else timedelta(days=plazo))

    def vencimiento_espera(self, fecha_requerida):
        return self._sumar(fecha_requerida, self.plazo_espera, self.unidad_espera)

    def vencimiento_retiro(self, fecha_preparacion):
        return self._sumar(fecha_preparacion, self.plazo_retiro, self.unidad_retiro)


# Fabrica politica prestamo

class FabricaPoliticaPrestamo:
    @staticmethod
    def _entero(valor, mensaje):
        texto = str(valor).strip()
        if not texto.isascii() or not texto.isdecimal():
            raise ValueError(mensaje)
        return int(texto)

    @classmethod
    def construir(cls, datos):
        plazo = cls._entero(
            datos.get("plazo_maximo"), "El plazo máximo debe ser un número entero."
        )
        salida = datos.get("permite_salida", False)
        if salida not in (True, False, 0, 1, "0", "1"):
            raise ValueError("El permiso de salida no es válido.")

        return PoliticaPrestamo(
            tipo_persona=datos.get("tipo_persona"),
            id_categoria=datos.get("id_categoria"),
            plazo_maximo=plazo,
            unidad_plazo=datos.get("unidad_plazo"),
            permite_salida=salida in (True, 1, "1"),
            id_politica=datos.get("id_politica"),
        )


# Sancion

class EstadoSancion(str, Enum):
    ACTIVA = 'ACTIVA'
    CUMPLIDA = 'CUMPLIDA'
    LEVANTADA = 'LEVANTADA'
    ANULADA = 'ANULADA'


@dataclass(kw_only=True)
class Sancion:
    id_sancion: int | None = None
    id_incidencia_ref: int | None = None
    estado: EstadoSancion = EstadoSancion.ACTIVA
    fecha_levantamiento: datetime | None = None
    dni_levantamiento: str | None = None
    justificacion_levantamiento: str | None = None

    def __post_init__(self):
        self.estado = EstadoSancion(self.estado)

    def levantar(self, justificacion, dni_encargado, fecha):
        if self.estado != EstadoSancion.ACTIVA:
            raise ValueError('La sanción por tardanza ya fue retirada.')
        self.justificacion_levantamiento = texto(justificacion, 'Justificación para quitar la sanción', 255, True)
        self.dni_levantamiento = validar_dni(dni_encargado)
        self.fecha_levantamiento = fecha
        self.estado = EstadoSancion.LEVANTADA


# Incidencia

class TipoIncidencia(str, Enum):
    RETRASO = 'RETRASO'
    DANIO = 'DANIO'
    PERDIDA = 'PERDIDA'


class EstadoIncidencia(Enum):
    REGISTRADA = 1
    EN_REVISION = 2
    RESUELTA = 3


class Incidencia:
    def __init__(self):
        self.id_incidencia = None
        self.id_detalle = None
        self.tipo = None
        self.dni_registrador = None
        self.descripcion = None
        self.fecha = None
        self.estado = None


# I repositorio sancion

class IRepositorioSancion(ABC):
    @abstractmethod
    def aplicar_sanciones_vencidas(self) -> int:
        """Comando automático e idempotente: una sanción por detalle vencido."""
        raise NotImplementedError

    @abstractmethod
    def levantar_sancion_vencimiento(self, id_prestamo: int, id_detalle: int, justificacion: str, dni_encargado: str) -> None:
        """Retira la sanción por tardanza con responsable y justificación."""
        raise NotImplementedError


# I repositorio politica prestamo

class IRepositorioPoliticaPrestamo(ABC):
    @abstractmethod
    def registrar_politica(self, politica) -> PoliticaPrestamo:
        """Escritura explícita. Devuelve PoliticaPrestamo y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def consultar_politica(self, id_politica) -> PoliticaPrestamo | None:
        raise NotImplementedError

    @abstractmethod
    def actualizar_politica(self, politica) -> PoliticaPrestamo:
        """Escritura explícita. Devuelve PoliticaPrestamo y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def eliminar_politica(self, id_politica) -> None:
        """Escritura explícita. Devuelve None y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def consultar_politicas(self) -> list[PoliticaPrestamo]:
        raise NotImplementedError

    @abstractmethod
    def consultar_politica_aplicable(self, tipo_persona, id_categoria) -> PoliticaPrestamo | None:
        raise NotImplementedError

    @abstractmethod
    def consultar_horario_atencion(self) -> HorarioAtencion:
        """Lectura del horario general de la institución, sin escrituras."""
        raise NotImplementedError

    @abstractmethod
    def actualizar_horario_atencion(self, horario: HorarioAtencion) -> HorarioAtencion:
        """Actualiza el horario para las próximas entregas."""
        raise NotImplementedError

    @abstractmethod
    def consultar_politica_vencimiento_reserva(self) -> PoliticaVencimientoReserva:
        raise NotImplementedError

    @abstractmethod
    def actualizar_politica_vencimiento_reserva(self, politica: PoliticaVencimientoReserva) -> PoliticaVencimientoReserva:
        raise NotImplementedError

    @abstractmethod
    def consultar_limites_articulos(self) -> list[LimiteArticulosPrestamo]:
        """Consulta los máximos generales por tipo de persona, sin escrituras."""
        raise NotImplementedError

    @abstractmethod
    def actualizar_limites_articulos(self, limites: list[LimiteArticulosPrestamo]) -> None:
        """Guarda en una transacción los máximos elegidos por el administrador."""
        raise NotImplementedError
