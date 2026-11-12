from datetime import datetime, timezone

from dominio.gestion_control.horario_atencion import ZONA_INSTITUCION
from dominio.gestion_personas_usuarios.validacion_persona import validar_dni
from dominio.gestion_prestamos.ampliacion_prestamo import AmpliacionPrestamo
from dominio.gestion_prestamos.i_repositorio_ampliacion_prestamo import IRepositorioAmpliacionPrestamo
from dominio.gestion_recursos.validacion_recurso import texto
from servicios.validacion_identificadores import identificador


class ServicioAplicacionAmpliacionPrestamo:
    def __init__(self, repositorio: IRepositorioAmpliacionPrestamo):
        self.repositorio = repositorio

    def solicitar_ampliacion(self, id_prestamo, id_detalle, fecha_nueva, motivo, dni_responsable):
        try:
            fecha_local = datetime.fromisoformat(fecha_nueva)
            if fecha_local.tzinfo is not None or fecha_local.second or fecha_local.microsecond:
                raise ValueError
            fecha_utc = fecha_local.replace(tzinfo=ZONA_INSTITUCION).astimezone(timezone.utc).replace(tzinfo=None)
            if fecha_utc.year < 1000:
                raise ValueError
        except (ValueError, TypeError, OverflowError):
            raise ValueError('Indica una nueva fecha y hora válida de devolución en Lima.') from None
        ampliacion = AmpliacionPrestamo(
            id_detalle=identificador(id_detalle), fecha_limite_nueva=fecha_utc, motivo=motivo,
        )
        return self.repositorio.solicitar_ampliacion(
            identificador(id_prestamo), ampliacion, validar_dni(dni_responsable))

    def aprobar_ampliacion(self, id_prestamo, id_ampliacion, id_usuario, observacion=''):
        return self.repositorio.aprobar_ampliacion(
            identificador(id_prestamo), identificador(id_ampliacion), identificador(id_usuario),
            texto(observacion, 'Observación', 255))

    def rechazar_ampliacion(self, id_prestamo, id_ampliacion, id_usuario, observacion):
        return self.repositorio.rechazar_ampliacion(
            identificador(id_prestamo), identificador(id_ampliacion), identificador(id_usuario),
            texto(observacion, 'Motivo del rechazo', 255, True))

    def consultar_ampliaciones(self, id_prestamo):
        return self.repositorio.consultar_ampliaciones(identificador(id_prestamo))
