from dataclasses import dataclass
from datetime import timedelta
from dominio.gestion_control.tipo_persona import TipoPersona
from dominio.gestion_recursos.validacion_recurso import entero


@dataclass(kw_only=True)
class PoliticaPrestamo:
    tipo_persona: TipoPersona
    id_categoria_ref: int
    plazo_maximo: int
    unidad_plazo: str
    permite_salida: bool = False
    id_politica: int | None = None

    def __post_init__(self):
        try:
            self.tipo_persona = TipoPersona(self.tipo_persona)
        except (ValueError, TypeError):
            raise ValueError("Selecciona un tipo de persona válido.") from None
        self.id_categoria_ref = entero(self.id_categoria_ref, "Categoría")
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
        return self.tipo_persona == tipo_persona and self.id_categoria_ref == id_categoria

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
