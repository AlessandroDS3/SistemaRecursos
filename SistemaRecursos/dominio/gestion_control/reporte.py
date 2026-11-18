from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Protocol
from dominio.compartido.validacion import LIMA, dni, entero, texto
from dominio.gestion_control.catalogo_reportes import OPCIONES_FILTROS, REPORTES


@dataclass(kw_only=True)
class FiltroReporte:
    tipo: str = 'prestamos'
    desde: str | date | None = ''
    hasta: str | date | None = ''
    estado: str = ''
    modalidad: str = ''
    tipo_persona: str = ''
    q: str = ''
    id_categoria: str | int = ''
    ubicacion: str = ''
    cumplimiento: str = ''
    tipo_gestion: str = ''
    codigo_inventario: str = ''
    dni_persona: str = ''

    @classmethod
    def desde_datos(cls, datos):
        return cls(**{k: datos[k] for k in cls.__dataclass_fields__ if k in datos})

    def __post_init__(self):
        if not isinstance(self.tipo, str) or self.tipo not in REPORTES:
            raise ValueError('Tipo de reporte inválido.')
        # Los filtros de otro reporte no alteran esta consulta ni sus enlaces de exportación.
        for campo in self.__dataclass_fields__:
            if campo != 'tipo' and campo not in self.definicion.filtros:
                setattr(self, campo, '')
        if self.estado not in ('', *self.definicion.estados):
            raise ValueError('Estado de reporte inválido.')
        for campo, opciones in OPCIONES_FILTROS.items():
            if getattr(self, campo) not in ('', *opciones):
                raise ValueError(f'Filtro {campo.replace("_", " ")} inválido.')
        self.q = texto(self.q, 'Búsqueda', 120)
        self.ubicacion = texto(self.ubicacion, 'Ubicación', 120)
        self.codigo_inventario = texto(self.codigo_inventario, 'Código de inventario', 40)
        if self.dni_persona:
            self.dni_persona = dni(self.dni_persona)
        if self.id_categoria:
            self.id_categoria = entero(self.id_categoria, 'Categoría')
        for campo in ('desde', 'hasta'):
            valor = getattr(self, campo)
            try:
                setattr(self, campo, date.fromisoformat(valor) if valor else None)
            except (ValueError, TypeError):
                raise ValueError('Las fechas deben usar el formato AAAA-MM-DD.') from None
        if (
            isinstance(self.desde, date)
            and isinstance(self.hasta, date)
            and self.desde > self.hasta
        ):
            raise ValueError('La fecha inicial no puede ser posterior a la final.')
        if self.hasta == date.max:
            raise ValueError('Fecha final fuera de rango.')

    @property
    def definicion(self):
        return REPORTES[self.tipo]

    @property
    def parametros(self):
        parametros = {'tipo': self.tipo}
        for campo in self.definicion.filtros:
            valor = getattr(self, campo)
            if valor not in ('', None):
                parametros[campo] = valor.isoformat() if isinstance(valor, date) else valor
        return parametros

    @staticmethod
    def _utc(dia):
        return datetime.combine(dia, time(), LIMA).astimezone(timezone.utc).replace(tzinfo=None)

    @property
    def inicio(self):
        return self._utc(self.desde) if self.desde else None

    @property
    def fin(self):
        return self._utc(self.hasta + timedelta(days=1)) if isinstance(self.hasta, date) else None


def celda_csv(valor):
    texto_celda = '' if valor is None else str(valor)
    peligroso = texto_celda.startswith(('\t', '\r', '\n')) or texto_celda.lstrip().startswith(
        ('=', '+', '-', '@')
    )
    return "'" + texto_celda if peligroso else texto_celda


class IRepositorioReporte(Protocol):
    def consultar_filas_reporte(self, filtro: FiltroReporte) -> list[dict]: ...
    def consultar_historial(self, filtro: FiltroReporte, solo_prestamos: bool = False) -> dict: ...
