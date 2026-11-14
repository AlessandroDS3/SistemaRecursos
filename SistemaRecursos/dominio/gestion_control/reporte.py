from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Protocol
from dominio.compartido.validacion import LIMA, entero, texto
from dominio.gestion_personas_usuarios.persona import TIPOS_PERSONA

FILAS_POR_PAGINA = 50


@dataclass(kw_only=True)
class FiltroReporte:
    tipo: str = 'prestamos'
    desde: str = ''
    hasta: str = ''
    estado: str = ''
    modalidad: str = ''
    tipo_persona: str = ''
    q: str = ''
    pagina: int = 1

    def __post_init__(self):
        if self.tipo not in ('prestamos', 'devoluciones'):
            raise ValueError('Tipo de reporte inválido.')
        if self.estado not in ('', 'ACTIVO', 'VENCIDO', 'DEVUELTO', 'PARCIALMENTE_DEVUELTO'):
            raise ValueError('Estado de reporte inválido.')
        if self.modalidad not in ('', 'INDIVIDUAL', 'GRUPAL') or self.tipo_persona not in (
            '',
            *TIPOS_PERSONA,
        ):
            raise ValueError('Modalidad o tipo de persona inválidos.')
        self.q = texto(self.q, 'Búsqueda', 120)
        self.pagina = entero(self.pagina, 'Página', maximo=1000000)
        for campo in ('desde', 'hasta'):
            valor = getattr(self, campo)
            try:
                setattr(self, campo, date.fromisoformat(valor) if valor else None)
            except (ValueError, TypeError):
                raise ValueError('Las fechas deben usar el formato AAAA-MM-DD.') from None
        if self.desde and self.hasta and self.desde > self.hasta:
            raise ValueError('La fecha inicial no puede ser posterior a la final.')
        if self.hasta == date.max:
            raise ValueError('Fecha final fuera de rango.')

    @staticmethod
    def _utc(dia):
        return datetime.combine(dia, time(), LIMA).astimezone(timezone.utc).replace(tzinfo=None)

    @property
    def inicio(self):
        return self._utc(self.desde) if self.desde else None

    @property
    def fin(self):
        return self._utc(self.hasta + timedelta(days=1)) if self.hasta else None


def celda_csv(valor):
    texto_celda = '' if valor is None else str(valor)
    peligroso = texto_celda.startswith(('\t', '\r', '\n')) or texto_celda.lstrip().startswith(
        ('=', '+', '-', '@')
    )
    return "'" + texto_celda if peligroso else texto_celda


class IRepositorioReporte(Protocol):
    def consultar(self, filtro: FiltroReporte, paginar=True) -> tuple[list[dict], dict]: ...
