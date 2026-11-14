from datetime import datetime
from dominio.prestamos import AmpliacionPrestamo, IRepositorioPrestamo
from dominio.validaciones import entero as identificador


class ServicioAplicacionAmpliacionPrestamo:
    def __init__(self, repositorio: IRepositorioPrestamo):
        self.repositorio = repositorio

    def ampliar_plazo(self, id_prestamo, id_detalle, cantidad, unidad, fecha_actual, id_usuario, motivo=''):
        id_prestamo, id_detalle = identificador(id_prestamo), identificador(id_detalle)
        id_usuario = identificador(id_usuario)
        try:
            fecha_actual = datetime.fromisoformat(fecha_actual)
        except (ValueError, TypeError):
            raise ValueError('Recarga el préstamo para obtener su fecha de devolución actual.') from None
        ampliacion = AmpliacionPrestamo(cantidad=cantidad, unidad=unidad,
                                       fecha_limite_anterior=fecha_actual, motivo=motivo)
        with self.repositorio.transaccion() as operacion:
            cuenta = operacion.cargar_cuenta_ampliacion(id_usuario)
            if (cuenta is None or cuenta['estado_cuenta'] != 'ACTIVA'
                    or cuenta['estado_persona'] != 'ACTIVA'
                    or 'PRESTAMOS_GESTIONAR' not in cuenta['permisos']):
                raise PermissionError('La cuenta no tiene permiso para ampliar préstamos.')
            _, prestamo, detalles, ahora = operacion.cargar_recepcion(id_prestamo, cuenta['dni_persona'])
            detalle = next((d for d in detalles if d['id_detalle'] == id_detalle), None)
            if detalle is None:
                raise LookupError('El bien no pertenece a este préstamo.')
            politica, horario = operacion.cargar_politica_ampliacion(detalle['id_politica'])
            if politica is None:
                raise ValueError('No se encontró la política aplicada al bien.')
            nueva = ampliacion.calcular_fecha(detalle, ahora, politica, horario)
            operacion.guardar_fecha_limite(id_detalle, ampliacion.fecha_limite_anterior, nueva)
            observacion = (f'Ampliación del detalle #{id_detalle}: '
                           f'{ampliacion.fecha_limite_anterior.isoformat(sep=" ")} UTC → '
                           f'{nueva.isoformat(sep=" ")} UTC. {ampliacion.motivo}').strip()
            operacion.guardar_estado(prestamo, prestamo.estado.value, observacion, cuenta['dni_persona'])
        return nueva
