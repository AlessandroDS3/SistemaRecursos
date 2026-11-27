
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from dominio.compartido.validacion import LIMA, validar_dni, validar_entero, validar_texto
from servicios.reportes.catalogo_reportes import OPCIONES_FILTROS, REPORTES


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
        self._validar_tipo_de_reporte()
        self._descartar_filtros_ajenos_al_reporte()
        self._validar_estado()
        self._validar_opciones()
        self._normalizar_textos_e_identificadores()
        self._normalizar_fechas()
        self._validar_rango_de_fechas()

    def _validar_tipo_de_reporte(self):
        if not isinstance(self.tipo, str) or self.tipo not in REPORTES:
            raise ValueError('Tipo de reporte inválido.')

    def _descartar_filtros_ajenos_al_reporte(self):
        for campo in self.__dataclass_fields__:
            if campo != 'tipo' and campo not in self.definicion.filtros:
                setattr(self, campo, '')

    def _validar_estado(self):
        if self.estado not in ('', *self.definicion.estados):
            raise ValueError('Estado de reporte inválido.')

    def _validar_opciones(self):
        for campo, opciones in OPCIONES_FILTROS.items():
            if getattr(self, campo) not in ('', *opciones):
                raise ValueError(f'Filtro {campo.replace("_", " ")} inválido.')

    def _normalizar_textos_e_identificadores(self):
        self.q = validar_texto(self.q, 'Búsqueda', 120)
        self.ubicacion = validar_texto(self.ubicacion, 'Ubicación', 120)
        self.codigo_inventario = validar_texto(self.codigo_inventario, 'Código de inventario', 40)
        if self.dni_persona:
            self.dni_persona = validar_dni(self.dni_persona)
        if self.id_categoria:
            self.id_categoria = validar_entero(self.id_categoria, 'Categoría')

    def _normalizar_fechas(self):
        for campo in ('desde', 'hasta'):
            valor = getattr(self, campo)
            try:
                if isinstance(valor, str):
                    valor = date.fromisoformat(valor) if valor else None
                setattr(self, campo, valor)
            except (ValueError, TypeError):
                raise ValueError('Las fechas deben usar el formato AAAA-MM-DD.') from None

    def _validar_rango_de_fechas(self):
        if isinstance(self.desde, date) and isinstance(self.hasta, date):
            if self.desde > self.hasta:
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
    def _convertir_medianoche_de_lima_a_utc(dia):
        return datetime.combine(dia, time(), LIMA).astimezone(timezone.utc).replace(tzinfo=None)

    @property
    def inicio_del_rango_utc(self):
        return self._convertir_medianoche_de_lima_a_utc(self.desde) if self.desde else None

    @property
    def fin_exclusivo_del_rango_utc(self):
        return self._convertir_medianoche_de_lima_a_utc(self.hasta + timedelta(days=1)) if isinstance(self.hasta, date) else None
