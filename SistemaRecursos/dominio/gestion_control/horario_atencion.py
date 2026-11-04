"""Horario diario de la institución; las fechas de persistencia se expresan en UTC."""
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

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
