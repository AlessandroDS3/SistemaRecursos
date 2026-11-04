"""Entrada de una entrega; las políticas y fechas definitivas se resuelven bajo bloqueo."""
from dataclasses import dataclass, field
from dominio.gestion_personas_usuarios.validacion_persona import validar_dni
from dominio.gestion_prestamos.validacion_prestamo import lista_ids
from dominio.gestion_prestamos.tipo_prestamo import TipoPrestamo
from dominio.gestion_prestamos.participante_prestamo import ParticipantePrestamo
from dominio.gestion_prestamos.fabrica_prestamo import FabricaPrestamo
from dominio.gestion_recursos.validacion_recurso import texto


@dataclass(kw_only=True)
class SolicitudPrestamo:
    dni_persona: str
    dni_encargado: str
    ids_bienes: list
    tipo_prestamo: TipoPrestamo = TipoPrestamo.INDIVIDUAL
    observaciones: str = ""
    participantes: list = field(default_factory=list)
    salida_solicitada: bool = False

    def __post_init__(self):
        self.dni_persona = validar_dni(self.dni_persona)
        self.dni_encargado = validar_dni(self.dni_encargado)
        self.ids_bienes = lista_ids(self.ids_bienes, "Bienes")
        if not self.ids_bienes:
            raise ValueError("Selecciona al menos un bien disponible.")
        self.tipo_prestamo = TipoPrestamo(self.tipo_prestamo)
        self.observaciones = texto(self.observaciones, "Observaciones", 255)
        self.participantes = [p if isinstance(p, ParticipantePrestamo) else ParticipantePrestamo(**p)
                              for p in self.participantes]

    def construir_prestamo(self, bienes, politicas, ahora, horario=None):
        return FabricaPrestamo.construir({
            "dni_persona": self.dni_persona, "dni_encargado": self.dni_encargado,
            "tipo_prestamo": self.tipo_prestamo, "observaciones": self.observaciones,
            "participantes": self.participantes, "salida_solicitada": self.salida_solicitada,
            "detalles": [{"id_bien_ref": bien["id_bien"],
                          "id_politica_ref": politicas[bien["id_categoria_ref"]].id_politica,
                          "fecha_limite_devolucion": politicas[bien["id_categoria_ref"]].fecha_limite(ahora, horario),
                          "estado_entrega": bien["estado"]} for bien in bienes],
        })
