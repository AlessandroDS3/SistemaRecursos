from dominio.compartido.validacion import NoEncontrado
from dominio.compartido.validacion import Conflicto, dni, entero, ids, texto
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_personas_usuarios.persona import validar_elegibilidad
from dominio.gestion_prestamos.prestamo import (
    IRepositorioPrestamo,
    SolicitudPrestamo,
    FILTROS_ESTADO_PRESTAMO,
    estado_prestamo,
)
from dominio.gestion_prestamos.devolucion import Devolucion
from servicios.operaciones_sancion import (
    registrar_danio_devolucion, registrar_falta, registrar_sancion_por_retraso,
    regularizar_devolucion,
)


class ServicioAplicacionPrestamo:
    def __init__(self, repositorio: IRepositorioPrestamo):
        self.repositorio = repositorio

    def consultar_condiciones_prestamo(self, documento):
        resultado = self.repositorio.consultar_condiciones_prestamo(dni(documento))
        validar_elegibilidad(resultado['persona'])
        persona = resultado.pop('persona')
        return dict(resultado, solicitante=f'{persona["nombres"]} {persona["apellidos"]}')

    def consultar_prestamos(self, filtros, documento=None):
        estado = filtros.get('estado', '')
        if estado and estado not in FILTROS_ESTADO_PRESTAMO:
            raise ValueError('Estado de préstamo inválido.')
        return self.repositorio.consultar_prestamos(
            dict(q=texto(filtros.get('q'), 'Búsqueda', 120), estado=estado), documento
        )

    def consultar_resumen_prestamos(self, documento=None):
        return self.repositorio.consultar_resumen_prestamos(
            dni(documento) if documento is not None else None
        )

    def consultar_prestamo(self, identificador, documento, gestionar=False):
        prestamo = self.repositorio.consultar_prestamo(entero(identificador))
        if prestamo is None:
            raise NoEncontrado('Préstamo inexistente.')
        afectados = {
            prestamo['dni_persona'],
            *(p['dni_persona'] for p in prestamo['participantes']),
        }
        if not gestionar and dni(documento) not in afectados:
            raise PermissionError('Solo puedes consultar los préstamos en los que participas.')
        prestamo['historial'] = self.repositorio.consultar_historial_estado(
            'PRESTAMO', prestamo['id_prestamo']
        )
        return prestamo

    def registrar_prestamo(self, datos, actor):
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(
                operacion.consultar_cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR'
            )
            if datos.get('acepta_condiciones') != '1':
                raise ValueError('Confirma que comunicaste el plazo y las condiciones de entrega.')
            solicitud = SolicitudPrestamo(
                dni_persona=datos.get('dni_persona'),
                dni_encargado=cuenta['dni_persona'],
                bienes=datos.get('bienes', []),
                participantes=datos.get('participantes', []),
                tipo_prestamo=datos.get('tipo_prestamo', 'INDIVIDUAL'),
                salida_solicitada=datos.get('salida_solicitada') == '1',
                observaciones=datos.get('observaciones', ''),
            )
            return self.registrar_prestamo_en_operacion(operacion, solicitud)

    @staticmethod
    def registrar_prestamo_en_operacion(
        operacion: IRepositorioPrestamo,
        solicitud: SolicitudPrestamo,
        bien_reservado: int | None = None,
    ) -> int:
        """Entrega directa o desde reserva; devuelve el identificador del préstamo.

        Recibe una operación dentro de una transacción ya abierta. Quien la llama
        confirma o revierte todas las escrituras, incluido el cierre de la reserva.
        Revalida elegibilidad, sanciones, cupo, inventario y política en ambos caminos.
        """
        contexto = operacion.consultar_contexto_entrega_prestamo(solicitud)
        plan = solicitud.planificar(contexto, bien_reservado)
        return operacion.registrar_entrega_prestamo(solicitud, plan, contexto['ahora'])

    def registrar_devolucion(self, identificador, datos, actor):
        detalles = ids(datos.get('detalles', []))
        devoluciones = [
            Devolucion(
                id_detalle=d,
                condicion=datos.get(f'condicion_{d}'),
                observacion=datos.get(f'observacion_{d}', ''),
            )
            for d in detalles
        ]
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(
                operacion.consultar_cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR'
            )
            prestamo = operacion.consultar_prestamo_para_actualizar(entero(identificador))
            if prestamo is None:
                raise NoEncontrado('Préstamo inexistente.')
            por_id = {d['id_detalle']: d for d in prestamo['detalles']}
            for devolucion in devoluciones:
                if devolucion.id_detalle not in por_id:
                    raise NoEncontrado('El bien seleccionado no pertenece al préstamo.')
                devolucion.validar(por_id[devolucion.id_detalle])
            ahora = operacion.consultar_fecha_actual()
            for devolucion in devoluciones:
                detalle = por_id[devolucion.id_detalle]
                registrar_sancion_por_retraso(
                    operacion.sanciones, detalle, ahora
                )
                operacion.registrar_devolucion(detalle, devolucion, ahora, cuenta['dni_persona'])
                detalle['fecha_devolucion'] = ahora
                detalle['condicion_devolucion'] = devolucion.condicion
                if devolucion.condicion == 'DANADO' and detalle['condicion_entrega'] == 'BUENO':
                    registrar_danio_devolucion(
                        operacion.sanciones, detalle, devolucion.observacion, cuenta, ahora,
                    )
                else:
                    regularizar_devolucion(
                        operacion.sanciones, detalle, devolucion.condicion, cuenta['dni_persona'], ahora,
                    )
            nuevo = estado_prestamo(prestamo['detalles'], ahora)
            operacion.actualizar_estado_prestamo(
                prestamo, nuevo, cuenta['dni_persona'], f'Recepción de {len(detalles)} bien(es).'
            )

    def registrar_perdida_bien_material(self, identificador, detalle_id, motivo, actor):
        motivo = texto(motivo, 'Motivo de pérdida', 255, True)
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(
                operacion.consultar_cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR'
            )
            prestamo = operacion.consultar_prestamo_para_actualizar(entero(identificador))
            if prestamo is None:
                raise NoEncontrado('Préstamo inexistente.')
            detalle = next(
                (d for d in prestamo['detalles'] if d['id_detalle'] == entero(detalle_id)), None
            )
            if detalle is None:
                raise NoEncontrado('El bien no pertenece al préstamo.')
            if (detalle['fecha_devolucion'] is not None or detalle['fecha_regularizacion'] is not None
                    or detalle['estado_bien'] != 'PRESTADO'):
                raise Conflicto('El bien debe estar prestado y pendiente para reportar su pérdida.')
            registrar_falta(
                operacion.sanciones, detalle, 'PERDIDA', 'GRAVE', motivo,
                cuenta, operacion.consultar_fecha_actual(),
            )
            operacion.registrar_perdida_bien_material(
                prestamo, detalle, cuenta['dni_persona'], motivo
            )

    def registrar_vencimientos_prestamos(self, actor):
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(
                operacion.consultar_cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR'
            )
            for fila in operacion.consultar_prestamos({'estado': 'VENCIDO'}):
                prestamo = operacion.consultar_prestamo_para_actualizar(fila['id_prestamo'])
                nuevo = estado_prestamo(prestamo['detalles'], operacion.consultar_fecha_actual())
                if nuevo != prestamo['estado']:
                    operacion.actualizar_estado_prestamo(
                        prestamo, nuevo, cuenta['dni_persona'], 'Vencimiento registrado.'
                    )
