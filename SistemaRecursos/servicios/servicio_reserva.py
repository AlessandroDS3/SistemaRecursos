from __future__ import annotations
from dominio.resultados_consulta import ReservaDetalle, ResultadoReservas
from dominio.gestion_prestamos.i_repositorio_reserva import IRepositorioReserva
from dominio.gestion_personas_usuarios.validacion_persona import validar_dni
from datetime import datetime, timezone, timedelta
from dominio.gestion_prestamos.reserva import Reserva, AccionReserva, TipoSolicitud
from dominio.gestion_prestamos.reserva import EstadoReserva
from servicios.validacion_identificadores import identificador
from dominio.gestion_recursos.validacion_recurso import texto


HORA_LIMA = timezone(timedelta(hours=-5))


class ServicioAplicacionReserva:
    def __init__(self, repositorio_reservas: IRepositorioReserva):
        self.repositorio: IRepositorioReserva = repositorio_reservas

    def registrar_reserva(self, datos, persona_actual) -> int:
        ahora = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
        persona = validar_dni(persona_actual)
        try:
            tipo = TipoSolicitud(datos.get("tipo_gestion", TipoSolicitud.PRESTAMO))
        except (ValueError, TypeError):
            raise ValueError("Selecciona solicitud de préstamo o reserva.") from None
        fecha = self._fecha_requerida(tipo, datos.get("fecha_requerida", ""), ahora)
        if datos.get("acepta_condiciones") != "1":
            raise ValueError("Confirma que revisaste el plazo y el permiso de salida del préstamo.")
        reserva = Reserva(
            dni_persona=persona, id_recurso_ref=datos.get("id_recurso_ref"),
            tipo_gestion=tipo, fecha_requerida=fecha,
            observaciones=datos.get("observaciones", ""),
            salida_solicitada=datos.get("salida_solicitada") == "1",
        )
        return self.repositorio.registrar_reserva(reserva, validar_dni(persona_actual))

    def expirar_solicitudes_vencidas(self) -> int:
        return self.repositorio.expirar_solicitudes_vencidas()

    def consultar_reserva(self, id_reserva, persona_actual, gestionar=False) -> ReservaDetalle:
        reserva = self.repositorio.consultar_reserva(identificador(id_reserva))
        if not reserva:
            raise LookupError("No se encontró la solicitud o reserva.")
        if not gestionar and reserva["dni_persona"] != validar_dni(persona_actual):
            raise PermissionError("Solo puedes consultar tus propias solicitudes y reservas.")
        return reserva

    def consultar_reservas(self, filtros, persona_actual, gestionar=False) -> ResultadoReservas:
        tipo = filtros.get("tipo", "")
        estado = filtros.get("estado", "")
        if tipo and tipo not in {tipo.value for tipo in TipoSolicitud}:
            raise ValueError("Selecciona un tipo de solicitud válido.")
        if estado and estado not in {e.value for e in EstadoReserva}:
            raise ValueError("Selecciona un estado válido.")
        return self.repositorio.consultar_reservas(
            {"tipo": tipo, "estado": estado, "q": texto(filtros.get("q", ""), "Búsqueda", 120)},
            None if gestionar else validar_dni(persona_actual),
        )

    def preparar_reserva(self, id_reserva, datos, persona_actual, gestionar=False) -> int | None:
        return self._resolver_reserva(
            id_reserva, datos, persona_actual, gestionar, AccionReserva.PREPARAR, self.repositorio.preparar_reserva
        )

    def entregar_reserva(self, id_reserva, datos, persona_actual, gestionar=False) -> int | None:
        return self._resolver_reserva(
            id_reserva, datos, persona_actual, gestionar, AccionReserva.ENTREGAR, self.repositorio.entregar_reserva
        )

    def cancelar_reserva(self, id_reserva, datos, persona_actual, gestionar=False) -> int | None:
        return self._resolver_reserva(
            id_reserva, datos, persona_actual, gestionar, AccionReserva.CANCELAR, self.repositorio.cancelar_reserva
        )

    def rechazar_reserva(self, id_reserva, datos, persona_actual, gestionar=False) -> int | None:
        return self._resolver_reserva(
            id_reserva, datos, persona_actual, gestionar, AccionReserva.RECHAZAR, self.repositorio.rechazar_reserva
        )

    def expirar_reserva(self, id_reserva, datos, persona_actual, gestionar=False) -> int | None:
        return self._resolver_reserva(
            id_reserva, datos, persona_actual, gestionar, AccionReserva.EXPIRAR, self.repositorio.expirar_reserva
        )

    def _resolver_reserva(self, id_reserva, datos, persona_actual, gestionar, accion, operacion):
        accion.validar_permiso(gestionar)
        motivo = texto(datos.get("motivo", ""), "Motivo", 255, accion.requiere_motivo)
        return operacion(
            identificador(id_reserva), validar_dni(persona_actual),
            gestionar, motivo, datos.get("acepta_condiciones") == "1",
        )

    @staticmethod
    def _fecha_requerida(tipo, valor, ahora):
        if tipo == TipoSolicitud.PRESTAMO:
            return ahora
        try:
            fecha_local = datetime.fromisoformat(valor)
            if fecha_local.tzinfo is not None:
                raise ValueError
            fecha_utc = fecha_local.replace(tzinfo=HORA_LIMA).astimezone(
                timezone.utc
            ).replace(tzinfo=None)
        except (TypeError, ValueError):
            raise ValueError("Indica una fecha y hora válida de retiro en Lima.") from None
        if fecha_utc <= ahora:
            raise ValueError("La fecha de retiro de una reserva debe ser futura.")
        return fecha_utc
