from dominio.compartido.validacion import NoEncontrado, entero
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_control.politica_prestamo import HorarioAtencion, PoliticaPrestamo
from dominio.gestion_prestamos.ampliacion_prestamo import AmpliacionPrestamo
from dominio.gestion_prestamos.contratos_prestamos import IRepositorioAmpliacionPrestamo


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
        return prestamo, nueva
