from dominio.compartido.validacion import Conflicto, NoEncontrado, entero, texto
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_personas_usuarios.persona import validar_elegibilidad
from dominio.gestion_control.politica_prestamo import HorarioAtencion, PoliticaPrestamo
from dominio.gestion_prestamos.ampliacion_prestamo import AmpliacionPrestamo
from dominio.gestion_prestamos.contratos_prestamos import IRepositorioAmpliacionPrestamo
from dominio.gestion_prestamos.solicitud_ampliacion import (
    SolicitudAmpliacion,
    exigir_pendiente,
    exigir_responsable,
)


class ServicioAplicacionAmpliacionPrestamo:
    def __init__(self, repositorio: IRepositorioAmpliacionPrestamo):
        self.repositorio = repositorio

    def ampliar_prestamo(self, prestamo_id, detalle_id, datos, actor):
        prestamo_id, detalle_id = entero(prestamo_id), entero(detalle_id)
        ampliacion = AmpliacionPrestamo(
            cantidad=datos.get('cantidad'),
            unidad=datos.get('unidad'),
            fecha_anterior=datos.get('fecha_actual'),
            motivo=datos.get('motivo', ''),
        )
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(
                operacion.consultar_cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR'
            )
            prestamo, nueva = self._calcular_ampliacion(
                operacion, prestamo_id, detalle_id, ampliacion
            )
            operacion.actualizar_plazo_prestamo(detalle_id, ampliacion.fecha_anterior, nueva)
            operacion.registrar_historial_estado(
                'PRESTAMO',
                prestamo_id,
                prestamo['estado'],
                prestamo['estado'],
                cuenta['dni_persona'],
                f'Detalle #{detalle_id}: {ampliacion.fecha_anterior} UTC → {nueva} UTC. {ampliacion.motivo}',
            )
        return nueva

    def consultar_ampliacion_prestamo(self, prestamo_id, detalle_id, datos, actor):
        ampliacion = AmpliacionPrestamo(
            cantidad=datos.get('cantidad'),
            unidad=datos.get('unidad'),
            fecha_anterior=datos.get('fecha_actual'),
            motivo=datos.get('motivo', ''),
        )
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.consultar_cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR')
            _, nueva = self._calcular_ampliacion(
                operacion, entero(prestamo_id), entero(detalle_id), ampliacion
            )
        return nueva

    # Solicitudes del usuario (AMP-01)

    def solicitar_ampliacion(self, prestamo_id, detalle_id, datos, actor):
        prestamo_id, detalle_id = entero(prestamo_id), entero(detalle_id)
        solicitud = SolicitudAmpliacion(
            cantidad=datos.get('cantidad'), unidad=datos.get('unidad'), motivo=datos.get('motivo')
        )
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(
                operacion.consultar_cuenta_actor(entero(actor)), 'PRESTAMOS_PROPIOS_CONSULTAR'
            )
            contexto = operacion.consultar_contexto_ampliacion_prestamo(prestamo_id, detalle_id)
            if contexto['prestamo'] is None or contexto['detalle'] is None:
                raise NoEncontrado('Préstamo inexistente.')
            exigir_responsable(contexto['prestamo'], cuenta['dni_persona'])
            fecha_anterior = contexto['detalle']['fecha_limite_devolucion']
            # Se revisa ahora contra la política para no registrar pedidos imposibles.
            prestamo, nueva = self._calcular_ampliacion(
                operacion,
                prestamo_id,
                detalle_id,
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
                'PRESTAMO', prestamo_id, prestamo['estado'], prestamo['estado'],
                cuenta['dni_persona'],
                f'Solicitud de ampliación #{identificador} para el detalle #{detalle_id}: '
                f'{solicitud.motivo}'[:255],
            )
        return identificador

    def aprobar_solicitud_ampliacion(self, identificador, datos, actor):
        identificador = entero(identificador)
        observacion = texto(datos.get('observacion'), 'Observación', 255)
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(
                operacion.consultar_cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR'
            )
            solicitud = exigir_pendiente(
                operacion.consultar_solicitud_ampliacion(identificador)
            )
            ampliacion = AmpliacionPrestamo(
                cantidad=solicitud['cantidad'],
                unidad=solicitud['unidad'],
                fecha_anterior=solicitud['fecha_limite_anterior'],
                motivo=f'Solicitud #{identificador}',
            )
            try:
                prestamo, nueva = self._calcular_ampliacion(
                    operacion, solicitud['id_prestamo'], solicitud['id_detalle'], ampliacion
                )
            except Conflicto as error:
                raise Conflicto(f'{error} Rechaza la solicitud con un motivo.') from None
            exigir_pendiente(operacion.consultar_solicitud_ampliacion(identificador, bloquear=True))
            operacion.actualizar_plazo_prestamo(
                solicitud['id_detalle'], ampliacion.fecha_anterior, nueva
            )
            operacion.resolver_solicitud_ampliacion(
                identificador, 'APROBADA', cuenta['dni_persona'], nueva, observacion or None
            )
            operacion.registrar_historial_estado(
                'PRESTAMO', solicitud['id_prestamo'], prestamo['estado'], prestamo['estado'],
                cuenta['dni_persona'],
                f"Solicitud #{identificador} aprobada. Detalle #{solicitud['id_detalle']}: "
                f'{ampliacion.fecha_anterior} UTC → {nueva} UTC',
            )
        return nueva

    def rechazar_solicitud_ampliacion(self, identificador, datos, actor):
        identificador = entero(identificador)
        observacion = texto(datos.get('observacion'), 'Motivo del rechazo', 255, True)
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(
                operacion.consultar_cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR'
            )
            solicitud = exigir_pendiente(
                operacion.consultar_solicitud_ampliacion(identificador, bloquear=True)
            )
            operacion.resolver_solicitud_ampliacion(
                identificador, 'RECHAZADA', cuenta['dni_persona'], None, observacion
            )
            operacion.registrar_historial_estado(
                'PRESTAMO', solicitud['id_prestamo'], None, 'SOLICITUD_RECHAZADA',
                cuenta['dni_persona'], f'Solicitud #{identificador} rechazada: {observacion}'[:255],
            )

    def consultar_solicitudes_ampliacion(self, estado='PENDIENTE'):
        return self.repositorio.consultar_solicitudes_ampliacion(estado=estado or None)

    def consultar_solicitudes_prestamo(self, prestamo_id):
        return self.repositorio.consultar_solicitudes_ampliacion(prestamo=entero(prestamo_id))

    @staticmethod
    def _calcular_ampliacion(operacion, prestamo_id, detalle_id, ampliacion):
        contexto = operacion.consultar_contexto_ampliacion_prestamo(prestamo_id, detalle_id)
        prestamo, detalle = contexto['prestamo'], contexto['detalle']
        if prestamo is None:
            raise NoEncontrado('Préstamo inexistente.')
        if detalle is None:
            raise NoEncontrado('El detalle no pertenece a este préstamo.')
        fila, horario = contexto['politica'], contexto['horario']
        if fila is None:
            raise ValueError('No se encontró la política aplicada al bien.')
        nueva = ampliacion.calcular(
            detalle,
            operacion.consultar_fecha_actual(),
            PoliticaPrestamo.desde_datos(fila),
            HorarioAtencion(**horario) if horario else None,
        )
        restricciones = operacion.consultar_restricciones_ampliacion(prestamo, detalle['id_recurso'])
        for persona in restricciones['personas']:
            validar_elegibilidad(persona)
        if restricciones['sancion']:
            raise Conflicto('El responsable o un integrante tiene una sanción activa.')
        if restricciones['reservas_sin_bien']:
            raise Conflicto('Hay reservas vigentes de este recurso sin otro ejemplar disponible.')
        return prestamo, nueva
