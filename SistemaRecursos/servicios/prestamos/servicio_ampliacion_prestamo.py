from datetime import datetime
from typing import Mapping

from dominio.compartido.validacion import Conflicto, NoEncontrado, validar_entero, validar_texto
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_personas_usuarios.persona import validar_elegibilidad_del_solicitante
from dominio.gestion_prestamos.ampliacion_prestamo import (
    EVENTO_AMPLIACION_PLAZO, AmpliacionPrestamo, DatosParaValidarAmpliacion, PrestamoParaAmpliar,
)
from dominio.gestion_prestamos.contratos_prestamos import IRepositorioAmpliacionPrestamo
from dominio.gestion_prestamos.solicitud_ampliacion import (
    EstadoSolicitudAmpliacion,
    SolicitudAmpliacion,
    exigir_solicitud_ampliacion_pendiente,
    exigir_titular_del_prestamo_para_ampliacion,
)


class ServicioAplicacionAmpliacionPrestamo:
    def __init__(self, repositorio: IRepositorioAmpliacionPrestamo):
        self.repositorio = repositorio

    def ampliar_prestamo(self, prestamo_id: int, detalle_id: int, datos: Mapping[str, str], actor: int) -> datetime:
        prestamo_id, detalle_id = validar_entero(prestamo_id), validar_entero(detalle_id)
        ampliacion = AmpliacionPrestamo(
            cantidad=datos.get('cantidad'),
            unidad=datos.get('unidad'),
            fecha_anterior=datos.get('fecha_actual'),
            motivo=datos.get('motivo', ''),
        )
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(
                operacion.consultar_cuenta_actor(validar_entero(actor)), 'PRESTAMOS_GESTIONAR'
            )
            prestamo, nueva = self._validar_y_calcular_nuevo_plazo(
                operacion, operacion.consultar_datos_para_validar_ampliacion(prestamo_id, detalle_id), ampliacion,
            )
            operacion.actualizar_plazo_prestamo(detalle_id, ampliacion.fecha_anterior, nueva)
            self._registrar_historial_ampliacion(operacion, prestamo, detalle_id, ampliacion, nueva, cuenta['dni_persona'])
        return nueva

    def previsualizar_ampliacion_prestamo(self, prestamo_id: int, detalle_id: int,
                                     datos: Mapping[str, str], actor: int) -> datetime:
        ampliacion = AmpliacionPrestamo(
            cantidad=datos.get('cantidad'),
            unidad=datos.get('unidad'),
            fecha_anterior=datos.get('fecha_actual'),
            motivo=datos.get('motivo', ''),
        )
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.consultar_cuenta_actor(validar_entero(actor)), 'PRESTAMOS_GESTIONAR')
            _, nueva = self._validar_y_calcular_nuevo_plazo(
                operacion, operacion.consultar_datos_para_validar_ampliacion(validar_entero(prestamo_id), validar_entero(detalle_id)),
                ampliacion,
            )
        return nueva

    # Solicitudes del usuario (AMP-01)

    def solicitar_ampliacion(self, prestamo_id: int, detalle_id: int, datos: Mapping[str, str], actor: int) -> int:
        prestamo_id, detalle_id = validar_entero(prestamo_id), validar_entero(detalle_id)
        solicitud = SolicitudAmpliacion(
            cantidad=datos.get('cantidad'), unidad=datos.get('unidad'), motivo=datos.get('motivo')
        )
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(
                operacion.consultar_cuenta_actor(validar_entero(actor)), 'PRESTAMOS_PROPIOS_CONSULTAR'
            )
            contexto = operacion.consultar_datos_para_validar_ampliacion(prestamo_id, detalle_id)
            if contexto.prestamo is None or contexto.detalle is None:
                raise NoEncontrado('Préstamo inexistente.')
            exigir_titular_del_prestamo_para_ampliacion(contexto.prestamo.dni_persona, cuenta['dni_persona'])
            fecha_anterior = contexto.detalle.fecha_limite_devolucion
            # Se revisa ahora contra la política para no registrar pedidos imposibles.
            prestamo, _ = self._validar_y_calcular_nuevo_plazo(
                operacion,
                contexto,
                AmpliacionPrestamo(
                    cantidad=solicitud.cantidad,
                    unidad=solicitud.unidad,
                    fecha_anterior=fecha_anterior,
                    motivo='',
                ),
            )
            identificador = operacion.registrar_solicitud_ampliacion(
                prestamo_id, detalle_id, cuenta['dni_persona'], solicitud, fecha_anterior
            )
            operacion.registrar_historial_estado(
                'PRESTAMO', prestamo_id, prestamo.estado, prestamo.estado,
                cuenta['dni_persona'],
                f'Solicitud de ampliación #{identificador} para el detalle #{detalle_id}: '
                f'{solicitud.motivo}'[:255],
            )
        return identificador

    def aprobar_solicitud_ampliacion(self, identificador: int, datos: Mapping[str, str], actor: int) -> datetime:
        identificador = validar_entero(identificador)
        observacion = validar_texto(datos.get('observacion'), 'Observación', 255)
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(
                operacion.consultar_cuenta_actor(validar_entero(actor)), 'PRESTAMOS_GESTIONAR'
            )
            solicitud = exigir_solicitud_ampliacion_pendiente(
                operacion.consultar_solicitud_ampliacion(identificador)
            )
            ampliacion = AmpliacionPrestamo(
                cantidad=solicitud['cantidad'],
                unidad=solicitud['unidad'],
                fecha_anterior=solicitud['fecha_limite_anterior'],
                motivo=f'Solicitud #{identificador}',
            )
            try:
                contexto = operacion.consultar_datos_para_validar_ampliacion(solicitud['id_prestamo'], solicitud['id_detalle'])
                prestamo, nueva = self._validar_y_calcular_nuevo_plazo(
                    operacion, contexto, ampliacion,
                )
            except Conflicto as error:
                raise Conflicto(f'{error} Rechaza la solicitud con un motivo.') from None
            exigir_solicitud_ampliacion_pendiente(operacion.consultar_solicitud_ampliacion(identificador, bloquear=True))
            operacion.actualizar_plazo_prestamo(
                solicitud['id_detalle'], ampliacion.fecha_anterior, nueva
            )
            operacion.resolver_solicitud_ampliacion(
                identificador, EstadoSolicitudAmpliacion.APROBADA, cuenta['dni_persona'], nueva, observacion or None
            )
            self._registrar_historial_ampliacion(
                operacion, prestamo, solicitud['id_detalle'], ampliacion, nueva, cuenta['dni_persona'],
                id_solicitud=identificador,
            )
        return nueva

    @staticmethod
    def _registrar_historial_ampliacion(
        operacion: IRepositorioAmpliacionPrestamo, prestamo: PrestamoParaAmpliar,
        detalle_id: int, ampliacion: AmpliacionPrestamo, nueva_fecha: datetime, documento: str,
        *, id_solicitud: int | None = None,
    ) -> None:
        anterior = ampliacion.fecha_anterior
        observacion = f'Detalle #{detalle_id}: {anterior} UTC → {nueva_fecha} UTC'
        datos: dict[str, object] = dict(evento=EVENTO_AMPLIACION_PLAZO, id_detalle=detalle_id,
                                       fecha_limite_anterior=anterior.isoformat(), fecha_limite_nueva=nueva_fecha.isoformat())
        if id_solicitud is not None:
            observacion = f'Solicitud #{id_solicitud} aprobada. {observacion}'
            datos['id_solicitud'] = id_solicitud
        else:
            observacion = f'{observacion}. {ampliacion.motivo}'
        operacion.registrar_historial_estado(
            'PRESTAMO', prestamo.id_prestamo, prestamo.estado, prestamo.estado, documento, observacion, datos=datos,
        )

    def rechazar_solicitud_ampliacion(self, identificador: int, datos: Mapping[str, str], actor: int) -> None:
        identificador = validar_entero(identificador)
        observacion = validar_texto(datos.get('observacion'), 'Motivo del rechazo', 255, True)
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(
                operacion.consultar_cuenta_actor(validar_entero(actor)), 'PRESTAMOS_GESTIONAR'
            )
            solicitud = exigir_solicitud_ampliacion_pendiente(
                operacion.consultar_solicitud_ampliacion(identificador, bloquear=True)
            )
            operacion.resolver_solicitud_ampliacion(
                identificador, EstadoSolicitudAmpliacion.RECHAZADA, cuenta['dni_persona'], None, observacion
            )
            operacion.registrar_historial_estado(
                'PRESTAMO', solicitud['id_prestamo'], None, 'SOLICITUD_RECHAZADA',
                cuenta['dni_persona'], f'Solicitud #{identificador} rechazada: {observacion}'[:255],
            )

    def consultar_solicitudes_ampliacion(self, estado='PENDIENTE'):
        return self.repositorio.consultar_solicitudes_ampliacion(estado=estado or None)

    def consultar_solicitudes_de_ampliacion_del_prestamo(self, prestamo_id):
        return self.repositorio.consultar_solicitudes_ampliacion(prestamo=validar_entero(prestamo_id))

    @staticmethod
    def _validar_y_calcular_nuevo_plazo(operacion: IRepositorioAmpliacionPrestamo, contexto: DatosParaValidarAmpliacion,
                            ampliacion: AmpliacionPrestamo) -> tuple[PrestamoParaAmpliar, datetime]:
        prestamo, detalle = contexto.prestamo, contexto.detalle
        if prestamo is None:
            raise NoEncontrado('Préstamo inexistente.')
        if detalle is None:
            raise NoEncontrado('El detalle no pertenece a este préstamo.')
        if contexto.politica is None:
            raise ValueError('No se encontró la política aplicada al bien.')
        nueva = ampliacion.calcular_nuevo_plazo_de_devolucion(
            detalle,
            operacion.consultar_fecha_actual(),
            contexto.politica,
            contexto.horario,
        )
        restricciones = operacion.consultar_restricciones_ampliacion(prestamo, detalle.id_recurso)
        for persona in restricciones.personas:
            validar_elegibilidad_del_solicitante(persona)
        if restricciones.sancion:
            raise Conflicto('El responsable o un integrante tiene una sanción activa.')
        if restricciones.reservas_sin_bien:
            raise Conflicto('Hay reservas vigentes de este recurso sin otro ejemplar disponible.')
        return prestamo, nueva
