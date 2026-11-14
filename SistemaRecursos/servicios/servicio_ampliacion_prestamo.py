from dominio.compartido.validacion import entero
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_control.politica_prestamo import HorarioAtencion, PoliticaPrestamo
from dominio.gestion_prestamos.ampliacion_prestamo import (
    AmpliacionPrestamo,
    IRepositorioAmpliacionPrestamo,
)


class ServicioAplicacionAmpliacionPrestamo:
    def __init__(self, repositorio: IRepositorioAmpliacionPrestamo):
        self.repositorio = repositorio

    def ampliar(self, prestamo_id, detalle_id, datos, actor):
        prestamo_id, detalle_id = entero(prestamo_id), entero(detalle_id)
        ampliacion = AmpliacionPrestamo(
            cantidad=datos.get('cantidad'),
            unidad=datos.get('unidad'),
            fecha_anterior=datos.get('fecha_actual'),
            motivo=datos.get('motivo', ''),
        )
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(operacion.cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR')
            prestamo, detalle, fila, horario = operacion.cargar(prestamo_id, detalle_id)
            if fila is None:
                raise ValueError('No se encontró la política aplicada al bien.')
            nueva = ampliacion.calcular(
                detalle,
                operacion.ahora(),
                PoliticaPrestamo.desde_datos(fila),
                HorarioAtencion(**horario) if horario else None,
            )
            operacion.guardar(detalle_id, ampliacion.fecha_anterior, nueva)
            operacion.historial(
                'PRESTAMO',
                prestamo_id,
                prestamo['estado'],
                prestamo['estado'],
                cuenta['dni_persona'],
                f'Detalle #{detalle_id}: {ampliacion.fecha_anterior} UTC → {nueva} UTC. {ampliacion.motivo}',
            )
        return nueva
