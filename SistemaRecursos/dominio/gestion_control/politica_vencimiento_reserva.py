from dataclasses import dataclass
from datetime import datetime, timedelta


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
        limite = 87600 if unidad == "HORAS" else 3650
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
