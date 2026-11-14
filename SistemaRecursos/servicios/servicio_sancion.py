from dominio.compartido.validacion import NoEncontrado
from dominio.compartido.validacion import entero
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_control.incidencia import TipoIncidencia, hay_retraso
from dominio.gestion_control.sancion import IRepositorioSancion, validar_levantamiento


class ServicioAplicacionSancion:
    def __init__(self, repositorio: IRepositorioSancion):
        self.repositorio = repositorio

    @staticmethod
    def registrar_retraso(operacion, detalle, ahora):
        if not hay_retraso(detalle, ahora):
            return False
        existente = operacion.buscar_retraso(detalle['id_detalle'])
        if existente and existente['id_sancion'] is not None:
            return False
        incidencia = (
            existente['id_incidencia']
            if existente
            else operacion.guardar_incidencia(
                detalle['id_detalle'],
                TipoIncidencia.RETRASO.value,
                'Vencimiento del plazo de devolución.',
                detalle['fecha_limite_devolucion'],
            )
        )
        sancion = operacion.guardar_sancion(
            incidencia,
            'Devolución fuera de plazo',
            'Bloquea nuevos préstamos y reservas para el responsable y los integrantes.',
            detalle['fecha_limite_devolucion'],
        )
        operacion.historial('SANCION', sancion, None, 'ACTIVA', None, 'Aplicación por retraso.')
        return True

    def procesar_vencimientos(self):
        creadas = 0
        for fila in self.repositorio.candidatos():
            with self.repositorio.transaccion() as operacion:
                detalle = operacion.cargar_detalle(fila['id_detalle'])
                if detalle is not None and detalle['fecha_devolucion'] is None:
                    creadas += self.registrar_retraso(operacion, detalle, operacion.ahora())
        return creadas

    def listar(self):
        return self.repositorio.listar()

    def levantar(self, identificador, justificacion, actor):
        identificador = entero(identificador)
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(operacion.cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR')
            sancion = operacion.consultar(identificador, bloquear=True)
            if sancion is None:
                raise NoEncontrado('Sanción inexistente.')
            nota = validar_levantamiento(sancion, justificacion)
            operacion.levantar(identificador, operacion.ahora(), cuenta['dni_persona'], nota)
            operacion.historial(
                'SANCION', identificador, 'ACTIVA', 'LEVANTADA', cuenta['dni_persona'], nota
            )
