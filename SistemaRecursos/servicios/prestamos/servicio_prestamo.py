from dominio.compartido.validacion import NoEncontrado
from dominio.compartido.validacion import Conflicto, dni, entero, ids, texto
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_personas_usuarios.persona import validar_elegibilidad
from dominio.gestion_prestamos.contratos_prestamos import IRepositorioPrestamo
from dominio.gestion_prestamos.prestamo import (
    SolicitudPrestamo,
    FILTROS_ESTADO_PRESTAMO,
    estado_prestamo,
)
from dominio.gestion_prestamos.devolucion import Devolucion
from servicios.control.operaciones_sancion import (
    registrar_danio_devolucion, registrar_falta, registrar_sancion_por_retraso,
    regularizar_devolucion,
)


class ServicioAplicacionPrestamo:
    def __init__(self, repositorio: IRepositorioPrestamo):
        self.repositorio = repositorio

    def autorizar_operacion_propia(self, datos, actor):
        operador = dni(datos.get('dni_operador'))
        accion = datos.get('accion')
        if accion not in ('ENTREGA', 'DEVOLUCION'):
            raise ValueError('Selecciona entrega o devolución.')
        prestamo_id = entero(datos.get('id_prestamo'), 'Préstamo') if accion == 'DEVOLUCION' else None
        motivo = texto(datos.get('motivo'), 'Motivo de autorización', 255, True)
        with self.repositorio.transaccion() as op:
            cuenta = exigir_permiso(op.consultar_cuenta_actor(entero(actor)), 'USUARIOS_GESTIONAR')
            if cuenta['rol'] != 'ADMINISTRADOR' or cuenta['dni_persona'] == operador:
                raise PermissionError('La autorización debe emitirla otro administrador.')
            if not op.consultar_operador_autorizable(operador):
                raise ValueError('El DNI debe corresponder a un encargado o administrador activo.')
            if prestamo_id is not None:
                prestamo = op.consultar_prestamo_para_actualizar(prestamo_id)
                if prestamo is None:
                    raise NoEncontrado('Préstamo inexistente.')
                if prestamo['dni_persona'] != operador and not op.es_participante(prestamo_id, operador):
                    raise ValueError('La persona autorizada debe participar en ese préstamo.')
            return op.guardar_autorizacion_propia(dict(
                dni_operador=operador, dni_administrador=cuenta['dni_persona'], accion=accion,
                id_prestamo_objetivo=prestamo_id, motivo=motivo,
            ))

    @staticmethod
    def validar_autorizacion_propia(op, documento, accion, codigo, prestamo=None):
        if not codigo:
            raise Conflicto('Para registrar tu propia operación, pide autorización a otro administrador.')
        identificador = entero(codigo, 'Número de autorización')
        autorizacion = op.consultar_autorizacion_propia(identificador, documento, accion, prestamo)
        if autorizacion is None:
            raise Conflicto('La autorización no corresponde a esta operación, ya se usó o venció.')
        return dict(autorizacion, codigo=identificador)

    @staticmethod
    def registrar_uso_autorizacion(op, autorizacion, prestamo, estado):
        op.consumir_autorizacion_propia(autorizacion['id_registro'], prestamo)
        op.registrar_historial_estado('PRESTAMO', prestamo, estado, estado, autorizacion['dni_operador'],
                                     f'Operación propia con autorización #{autorizacion["codigo"]} del DNI '
                                     f'{autorizacion["dni_administrador"]}. {autorizacion["motivo"]}'[:255])

    @staticmethod
    def participa_en_prestamo(op, prestamo, documento):
        return prestamo['dni_persona'] == documento or op.es_participante(prestamo['id_prestamo'], documento)

    @staticmethod
    def exigir_operador_ajeno(op, prestamo, documento):
        if ServicioAplicacionPrestamo.participa_en_prestamo(op, prestamo, documento):
            raise PermissionError('Otro responsable autorizado debe revisar este caso.')

    @staticmethod
    def autorizar_recepcion_propia(op, prestamo, documento, codigo):
        if ServicioAplicacionPrestamo.participa_en_prestamo(op, prestamo, documento):
            return ServicioAplicacionPrestamo.validar_autorizacion_propia(
                op, documento, 'DEVOLUCION', codigo, prestamo['id_prestamo']
            )
        return None

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
            return self.registrar_prestamo_en_operacion(operacion, solicitud, codigo=datos.get('autorizacion'))

    @staticmethod
    def registrar_prestamo_en_operacion(
        operacion: IRepositorioPrestamo,
        solicitud: SolicitudPrestamo,
        bien_reservado: int | None = None,
        reserva_origen: int | None = None,
        codigo=None,
    ) -> int:
        """Entrega directa o desde reserva; devuelve el identificador del préstamo.

        Recibe una operación dentro de una transacción ya abierta. Quien la llama
        confirma o revierte todas las escrituras, incluido el cierre de la reserva.
        Revalida elegibilidad, sanciones, cupo, inventario y política en ambos caminos.
        """
        contexto = operacion.consultar_contexto_entrega_prestamo(solicitud, reserva_origen)
        plan = solicitud.planificar(contexto, bien_reservado)
        autorizacion = None
        if solicitud.dni_encargado in solicitud.solicitantes:
            autorizacion = ServicioAplicacionPrestamo.validar_autorizacion_propia(
                operacion, solicitud.dni_encargado, 'ENTREGA', codigo,
            )
        prestamo = operacion.registrar_entrega_prestamo(solicitud, plan, contexto['ahora'])
        if autorizacion:
            ServicioAplicacionPrestamo.registrar_uso_autorizacion(operacion, autorizacion, prestamo, 'ACTIVO')
        return prestamo

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
            autorizacion = self.autorizar_recepcion_propia(operacion, prestamo, cuenta['dni_persona'],
                                                           datos.get('autorizacion'))
            por_id = {d['id_detalle']: d for d in prestamo['detalles']}
            for devolucion in devoluciones:
                if devolucion.id_detalle not in por_id:
                    raise NoEncontrado('El bien seleccionado no pertenece al préstamo.')
                detalle = por_id[devolucion.id_detalle]
                devolucion.validar(detalle)
                devolucion.validar_codigo_recibido(detalle, datos.get(f'codigo_recibido_{devolucion.id_detalle}'))
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
            if autorizacion:
                self.registrar_uso_autorizacion(operacion, autorizacion, prestamo['id_prestamo'], nuevo)

    def registrar_discrepancia_devolucion(self, identificador, detalle_id, motivo, actor):
        nota = texto(motivo, 'Discrepancia observada', 200, True)
        with self.repositorio.transaccion() as op:
            cuenta = exigir_permiso(op.consultar_cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR')
            prestamo = op.consultar_prestamo_para_actualizar(entero(identificador))
            if prestamo is None:
                raise NoEncontrado('Préstamo inexistente.')
            detalle_id = entero(detalle_id)
            detalle = next((fila for fila in prestamo['detalles'] if fila['id_detalle'] == detalle_id), None)
            if detalle is None:
                raise NoEncontrado('El bien no pertenece al préstamo.')
            if detalle['fecha_devolucion'] or detalle['fecha_regularizacion']:
                raise Conflicto('El bien ya se recibió o regularizó.')
            op.registrar_historial_estado('PRESTAMO', prestamo['id_prestamo'], prestamo['estado'],
                                         prestamo['estado'], cuenta['dni_persona'],
                                         f'Discrepancia en detalle #{detalle_id}: {nota}')

    def rectificar_devolucion(self, identificador, detalle_id, motivo, actor):
        nota = texto(motivo, 'Motivo de rectificación', 255, True)
        identificador, detalle_id = entero(identificador), entero(detalle_id)
        with self.repositorio.transaccion() as op:
            cuenta = exigir_permiso(op.consultar_cuenta_actor(entero(actor)), 'USUARIOS_GESTIONAR')
            if cuenta['rol'] != 'ADMINISTRADOR':
                raise PermissionError('Solo el administrador puede rectificar devoluciones.')
            prestamo = op.consultar_prestamo_para_actualizar(identificador)
            if prestamo is None:
                raise NoEncontrado('Préstamo inexistente.')
            detalle = next((fila for fila in prestamo['detalles'] if fila['id_detalle'] == detalle_id), None)
            if detalle is None:
                raise NoEncontrado('El bien no pertenece al préstamo.')
            if not detalle['fecha_devolucion']:
                raise Conflicto('Solo se rectifican devoluciones registradas.')
            self.exigir_operador_ajeno(op, prestamo, cuenta['dni_persona'])
            if op.sanciones.consultar_sancion_detalle(detalle_id):
                raise Conflicto('La devolución está vinculada a una sanción y requiere revisión del caso.')
            movimiento = op.consultar_ultimo_movimiento_bien(detalle['id_bien'])
            mismo_prestamo = f'Recepción del préstamo #{identificador}.'
            referencia_anterior = f'Devolución de préstamo #{identificador};'
            if (not movimiento or movimiento['estado_anterior'] not in ('PRESTADO', 'PERDIDO')
                    or movimiento['estado_nuevo'] != detalle['estado_bien']
                    or movimiento['fecha'] < detalle['fecha_devolucion']
                    or not (movimiento['observacion'] == mismo_prestamo or
                            (movimiento['observacion'] or '').startswith(referencia_anterior))):
                raise Conflicto('El bien tiene movimientos posteriores o falta el registro de recepción. Revisa el caso antes de rectificar.')
            op.rectificar_devolucion(detalle, movimiento, nota, cuenta['dni_persona'])
            detalle['fecha_devolucion'] = None
            estado = estado_prestamo(prestamo['detalles'], op.consultar_fecha_actual())
            op.actualizar_estado_prestamo(prestamo, estado, cuenta['dni_persona'],
                                         f'Rectificación de devolución del detalle #{detalle_id}. {nota}'[:255])

    def registrar_perdida_bien_material(self, identificador, detalle_id, motivo, actor, *, gravedad='GRAVE'):
        motivo = texto(motivo, 'Motivo de pérdida', 255, True)
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(
                operacion.consultar_cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR'
            )
            prestamo = operacion.consultar_prestamo_para_actualizar(entero(identificador))
            if prestamo is None:
                raise NoEncontrado('Préstamo inexistente.')
            self.exigir_operador_ajeno(operacion, prestamo, cuenta['dni_persona'])
            detalle = next(
                (d for d in prestamo['detalles'] if d['id_detalle'] == entero(detalle_id)), None
            )
            if detalle is None:
                raise NoEncontrado('El bien no pertenece al préstamo.')
            if (detalle['fecha_devolucion'] is not None or detalle['fecha_regularizacion'] is not None
                    or detalle['estado_bien'] != 'PRESTADO'):
                raise Conflicto('El bien debe estar prestado y pendiente para reportar su pérdida.')
            registrar_falta(
                operacion.sanciones, detalle, 'PERDIDA', gravedad, motivo,
                cuenta, operacion.consultar_fecha_actual(),
            )
            operacion.registrar_perdida_bien_material(
                prestamo, detalle, cuenta['dni_persona'], motivo
            )

    def actualizar_estados_prestamos_vencidos(self, actor):
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
