"""Reglas de vigencia de sesiones y de intentos de acceso; sin Flask ni base de datos."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from threading import Lock

INACTIVIDAD_MAXIMA = timedelta(minutes=30)
DURACION_MAXIMA = timedelta(hours=8)
INTERVALO_ACTIVIDAD = timedelta(minutes=1)


class AccesoBloqueado(Exception):
    """Demasiados intentos fallidos; el mensaje no revela si la cuenta existe."""

    def __init__(self, minutos: int):
        super().__init__(
            f'Demasiados intentos fallidos. Espera {minutos} '
            f'minuto{"s" if minutos != 1 else ""} e inténtalo otra vez.'
        )
        self.minutos = minutos


def huella_sesion(token: str) -> str:
    """El servidor solo guarda la huella del token; la cookie no sirve sin la tabla."""
    return sha256(token.encode()).hexdigest()


def sesion_vigente(fila: dict | None, id_usuario: int, ahora: datetime) -> bool:
    return bool(
        fila
        and fila['id_usuario'] == id_usuario
        and fila['fecha_cierre'] is None
        and ahora - fila['ultima_actividad'] <= INACTIVIDAD_MAXIMA
        and ahora - fila['fecha_inicio'] <= DURACION_MAXIMA
    )


@dataclass
class LimitadorIntentos:
    """Cuenta fallos por clave (usuario u origen) en memoria del proceso.

    Tras `maximo` fallos dentro de `ventana`, la clave queda bloqueada durante `bloqueo`.
    Se reinicia al reiniciar la aplicación; es la variante simple acordada para SEG-01.
    """

    maximo: int = 5
    ventana: timedelta = timedelta(minutes=15)
    bloqueo: timedelta = timedelta(minutes=15)
    reloj: object = lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    _fallos: dict = field(default_factory=dict, repr=False)
    _bloqueos: dict = field(default_factory=dict, repr=False)
    _cerrojo: Lock = field(default_factory=Lock, repr=False)

    def minutos_bloqueo(self, clave) -> int:
        """Minutos restantes de bloqueo de la clave, o 0 si puede intentar."""
        with self._cerrojo:
            hasta = self._bloqueos.get(clave)
            ahora = self.reloj()
            if hasta is None or hasta <= ahora:
                self._bloqueos.pop(clave, None)
                return 0
            return max(1, -(-int((hasta - ahora).total_seconds()) // 60))

    def registrar_fallo(self, clave) -> None:
        with self._cerrojo:
            ahora = self.reloj()
            recientes = [f for f in self._fallos.get(clave, []) if ahora - f < self.ventana]
            recientes.append(ahora)
            if len(recientes) >= self.maximo:
                self._bloqueos[clave] = ahora + self.bloqueo
                recientes = []
            self._fallos[clave] = recientes
            if len(self._fallos) > 10000:
                self._depurar(ahora)

    def limpiar(self, clave) -> None:
        with self._cerrojo:
            self._fallos.pop(clave, None)
            self._bloqueos.pop(clave, None)

    def _depurar(self, ahora):
        for clave in [c for c, f in self._fallos.items() if not f or ahora - f[-1] >= self.ventana]:
            del self._fallos[clave]
        for clave in [c for c, h in self._bloqueos.items() if h <= ahora]:
            del self._bloqueos[clave]
