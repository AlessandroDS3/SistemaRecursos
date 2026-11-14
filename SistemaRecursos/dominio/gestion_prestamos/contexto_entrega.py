from dataclasses import dataclass
from datetime import datetime

from dominio.gestion_control.horario_atencion import HorarioAtencion
from dominio.gestion_control.politica_prestamo import LimiteArticulosPrestamo
from dominio.gestion_prestamos.validacion_prestamo import ConflictoPrestamoError, validar_persona


@dataclass
class ContextoEntrega:
    personas: dict
    tiene_vencidos: bool
    tiene_sanciones: bool
    limite: LimiteArticulosPrestamo
    pendientes: int
    bienes: list
    tiene_entregas_pendientes: bool
    politicas: dict
    horario: HorarioAtencion | None
    ahora: datetime

    def construir_prestamo(self, solicitud, id_bien_reservado=None):
        participantes = {solicitud.dni_persona, *(p.dni_persona for p in solicitud.participantes)}
        if set(self.personas) != participantes | {solicitud.dni_encargado}:
            raise ValueError('Una de las personas seleccionadas ya no existe.')
        if self.personas[solicitud.dni_encargado]['estado'] != 'ACTIVA':
            raise ValueError('El encargado está inactivo.')
        for dni in participantes:
            validar_persona(self.personas[dni])
        if self.tiene_vencidos:
            raise ConflictoPrestamoError('La persona tiene un préstamo vencido pendiente de devolución.')
        if self.tiene_sanciones:
            raise ConflictoPrestamoError('El solicitante o un participante tiene una sanción activa.')
        self.limite.validar_entrega(self.pendientes, len(solicitud.ids_bienes))
        if {b['id_bien'] for b in self.bienes} != set(solicitud.ids_bienes):
            raise ValueError('Uno de los bienes seleccionados ya no existe.')
        for bien in self.bienes:
            esperado = 'RESERVADO' if bien['id_bien'] == id_bien_reservado else 'DISPONIBLE'
            if bien['estado'] != esperado:
                raise ConflictoPrestamoError('Uno de los bienes dejó de estar disponible. No se registró la entrega.')
        if self.tiene_entregas_pendientes:
            raise ConflictoPrestamoError('Uno de los bienes tiene una entrega pendiente, aunque su inventario indique disponible. Revisa su préstamo antes de una nueva entrega.')
        if {b['id_categoria'] for b in self.bienes} != set(self.politicas):
            raise ValueError('Falta una política para el tipo de persona y una de las categorías seleccionadas.')
        if solicitud.salida_solicitada and any(not p.permite_salida for p in self.politicas.values()):
            raise ValueError('Una de las políticas no permite sacar el bien de la institución.')
        if self.horario is None:
            raise ValueError('Configura el horario general de atención en Políticas antes de registrar entregas.')
        self.horario.cierre_para_entrega(self.ahora)
        return solicitud.construir_prestamo(self.bienes, self.politicas, self.ahora, self.horario)
