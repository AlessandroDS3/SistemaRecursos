from dominio.gestion_prestamos.prestamo import Prestamo
from dominio.gestion_prestamos.detalle_prestamo import DetallePrestamo
from dominio.gestion_prestamos.participante_prestamo import ParticipantePrestamo


class FabricaPrestamo:
    @classmethod
    def construir(cls, datos):
        prestamo = Prestamo(
            dni_persona=datos.get("dni_persona"),
            dni_encargado=datos.get("dni_encargado"),
            tipo_prestamo=datos.get("tipo_prestamo", "INDIVIDUAL"),
            observaciones=datos.get("observaciones", ""),
            salida_solicitada=datos.get("salida_solicitada", False),
        )
        for datos_detalle in datos.get("detalles", []):
            if isinstance(datos_detalle, DetallePrestamo):
                detalle = datos_detalle
            else:
                detalle = DetallePrestamo(**datos_detalle)
            prestamo.agregar_detalle(detalle)

        for datos_participante in datos.get("participantes", []):
            if isinstance(datos_participante, ParticipantePrestamo):
                participante = datos_participante
            else:
                participante = ParticipantePrestamo(**datos_participante)
            prestamo.participantes.append(participante)

        prestamo.validar()
        return prestamo
