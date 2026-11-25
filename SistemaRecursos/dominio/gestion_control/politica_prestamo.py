from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

from dominio.compartido.validacion import LIMA, entero
from dominio.gestion_personas_usuarios.persona import TIPOS_PERSONA

NOMBRES_DIAS = ('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo')
DIAS_LABORABLES = 0b0011111  # Un bit por día, empezando por el lunes.


def dias_habilitados(mascara):
    return tuple(dia for dia in range(len(NOMBRES_DIAS)) if mascara & (1 << dia))


def hora(valor):
    if isinstance(valor, timedelta):
        segundos = int(valor.total_seconds())
        if segundos != valor.total_seconds() or segundos % 60 or not 0 <= segundos < 86400:
            raise ValueError('Horario inválido.')
        valor = time(segundos // 3600, segundos % 3600 // 60)
    if isinstance(valor, str):
        try:
            valor = time.fromisoformat(valor)
        except ValueError:
            raise ValueError('Introduce una hora válida.') from None
    if not isinstance(valor, time) or valor.second or valor.microsecond or valor.tzinfo:
        raise ValueError('El horario debe indicar horas y minutos.')
    return valor


@dataclass(kw_only=True)
class HorarioAtencion:
    hora_apertura: time = time(8)
    hora_cierre: time = time(16)
    dias_atencion: int = DIAS_LABORABLES

    def __post_init__(self):
        self.hora_apertura, self.hora_cierre = hora(self.hora_apertura), hora(self.hora_cierre)
        if self.hora_apertura >= self.hora_cierre:
            raise ValueError('La apertura debe ser anterior al cierre.')
        self.dias_atencion = entero(self.dias_atencion, 'Días de atención', maximo=127)

    @classmethod
    def desde_datos(cls, datos):
        return cls(**{campo: datos[campo] for campo in cls.__dataclass_fields__ if campo in datos})

    def cierre(self, fecha):
        local = fecha.replace(tzinfo=timezone.utc).astimezone(LIMA)
        if local.weekday() not in dias_habilitados(self.dias_atencion):
            dias = ', '.join(NOMBRES_DIAS[dia].lower() for dia in dias_habilitados(self.dias_atencion))
            raise ValueError(f'No hay atención ese día. Días de atención: {dias}.')
        if not self.hora_apertura <= local.time() < self.hora_cierre:
            raise ValueError(
                f'La atención es de {self.hora_apertura:%H:%M} a {self.hora_cierre:%H:%M}.'
            )
        return (
            datetime.combine(local.date(), self.hora_cierre, LIMA)
            .astimezone(timezone.utc)
            .replace(tzinfo=None)
        )


@dataclass(kw_only=True)
class PoliticaPrestamo:
    tipo_persona: str
    id_categoria: int
    plazo_maximo: int
    unidad_plazo: str
    permite_salida: bool = False
    id_politica: int | None = None

    def __post_init__(self):
        if self.tipo_persona not in TIPOS_PERSONA or self.unidad_plazo not in ('HORAS', 'DIAS'):
            raise ValueError('Tipo de persona o unidad de plazo inválidos.')
        self.id_categoria = entero(self.id_categoria, 'Categoría')
        self.plazo_maximo = entero(
            self.plazo_maximo,
            'Plazo máximo',
            maximo=87600 if self.unidad_plazo == 'HORAS' else 3650,
        )
        if self.permite_salida not in (True, False, 0, 1, '0', '1', ''):
            raise ValueError('Permiso de salida inválido.')
        self.permite_salida = self.permite_salida in (True, 1, '1')

    @classmethod
    def desde_datos(cls, datos):
        valores = {k: datos[k] for k in cls.__dataclass_fields__ if k in datos}
        for campo in ('tipo_persona', 'id_categoria', 'plazo_maximo', 'unidad_plazo'):
            valores.setdefault(campo, None)
        return cls(**valores)

    @property
    def duracion(self):
        return timedelta(**{'hours' if self.unidad_plazo == 'HORAS' else 'days': self.plazo_maximo})

    def vencimiento(self, entrega, horario):
        fin = entrega + self.duracion
        return min(fin, horario.cierre(entrega)) if self.unidad_plazo == 'HORAS' else fin


@dataclass(kw_only=True)
class ConfiguracionReservas:
    plazo_espera: int = 2
    unidad_espera: str = 'DIAS'
    plazo_retiro: int = 24
    unidad_retiro: str = 'HORAS'

    def __post_init__(self):
        for campo in ('espera', 'retiro'):
            unidad = getattr(self, 'unidad_' + campo)
            if unidad not in ('HORAS', 'DIAS'):
                raise ValueError('Unidad de plazo de reserva inválida.')
            setattr(
                self,
                'plazo_' + campo,
                entero(
                    getattr(self, 'plazo_' + campo),
                    'Plazo de reserva',
                    maximo=720 if unidad == 'HORAS' else 30,
                ),
            )

    def vencimiento(self, desde, etapa):
        unidad, cantidad = getattr(self, 'unidad_' + etapa), getattr(self, 'plazo_' + etapa)
        try:
            return desde + timedelta(**{'hours' if unidad == 'HORAS' else 'days': cantidad})
        except OverflowError:
            raise ValueError('La fecha de vencimiento de la reserva está fuera de rango.') from None
