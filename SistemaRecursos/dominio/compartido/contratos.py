from contextlib import AbstractContextManager
from datetime import datetime
from typing import Protocol, TypedDict


class FilaHistorialEstado(TypedDict):
    fecha: datetime
    estado_anterior: str | None
    estado_nuevo: str
    responsable: str | None
    observacion: str | None


class IRepositorioTransaccional(Protocol):
    """Una operación independiente que conserva bloqueos hasta confirmar o revertir."""

    def transaccion(self) -> AbstractContextManager: ...
    def consultar_cuenta_actor(self, identificador: int) -> dict | None: ...
    def consultar_fecha_actual(self) -> datetime: ...
    def registrar_historial_estado(
        self,
        entidad: str,
        identificador: int,
        anterior: str | None,
        nuevo: str,
        actor: str | None,
        observacion: str,
        *,
        datos: dict[str, object] | None = None,
    ): ...
    def consultar_historial_estado(self, entidad: str, identificador: int) -> list[FilaHistorialEstado]: ...
