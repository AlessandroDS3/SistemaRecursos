from dominio.compartido.validacion import NoEncontrado
from dominio.compartido.validacion import entero, texto
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_control.incidencia import TipoIncidencia, hay_retraso
from dominio.gestion_control.sancion import IRepositorioSancion, validar_levantamiento


class ServicioAplicacionSancion:
    def __init__(self, repositorio: IRepositorioSancion):
        self.repositorio = repositorio

    @staticmethod
    def registrar_sancion_por_retraso(operacion, detalle, ahora):
        if not hay_retraso(detalle, ahora):
            return False
        existente = operacion.consultar_incidencia_retraso(detalle['id_detalle'])
        if existente and existente['id_sancion'] is not None:
            return False
        incidencia = (
            existente['id_incidencia']
            if existente
            else operacion.registrar_incidencia(
                detalle['id_detalle'],
                TipoIncidencia.RETRASO.value,
                'Vencimiento del plazo de devolución.',
                detalle['fecha_limite_devolucion'],
            )
        )
        sancion = operacion.registrar_sancion(
            incidencia,
            'Devolución fuera de plazo',
            'Bloquea nuevos préstamos y reservas para el responsable y los integrantes.',
            detalle['fecha_limite_devolucion'],
        )
        operacion.registrar_historial_estado(
            'SANCION', sancion, None, 'ACTIVA', None, 'Aplicación por retraso.'
        )
        return True

    def aplicar_sanciones_por_vencimiento(self):
        creadas = 0
        for fila in self.repositorio.consultar_detalles_vencidos():
            with self.repositorio.transaccion() as operacion:
                detalle = operacion.consultar_detalle_prestamo(fila['id_detalle'])
                if detalle is not None and detalle['fecha_devolucion'] is None:
                    creadas += self.registrar_sancion_por_retraso(
                        operacion, detalle, operacion.consultar_fecha_actual()
                    )
        return creadas

    def consultar_sanciones(self, filtros=None):
        filtros = filtros or {}
        estado = filtros.get('estado', '')
        if estado not in ('', 'ACTIVA', 'LEVANTADA'):
            raise ValueError('Estado de sanción inválido.')
        return self.repositorio.consultar_sanciones(
            dict(estado=estado, q=texto(filtros.get('q'), 'Búsqueda', 120))
        )

    def levantar_sancion(self, identificador, justificacion, actor):
        identificador = entero(identificador)
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(
                operacion.consultar_cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR'
            )
            sancion = operacion.consultar_sancion(identificador, bloquear=True)
            if sancion is None:
                raise NoEncontrado('Sanción inexistente.')
            nota = validar_levantamiento(sancion, justificacion)
            operacion.levantar_sancion(
                identificador, operacion.consultar_fecha_actual(), cuenta['dni_persona'], nota
            )
            operacion.registrar_historial_estado(
                'SANCION', identificador, 'ACTIVA', 'LEVANTADA', cuenta['dni_persona'], nota
            )
