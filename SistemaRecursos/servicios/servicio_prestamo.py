from dominio.compartido.validacion import NoEncontrado
from dominio.compartido.validacion import Conflicto, dni, entero, ids, texto
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_personas_usuarios.persona import validar_elegibilidad
from dominio.gestion_prestamos.prestamo import (
    IRepositorioPrestamo,
    SolicitudPrestamo,
    estado_prestamo,
)
from dominio.gestion_prestamos.devolucion import Devolucion
from servicios.servicio_sancion import ServicioAplicacionSancion


class ServicioAplicacionPrestamo:
    def __init__(self, repositorio: IRepositorioPrestamo):
        self.repositorio = repositorio

    def condiciones(self, documento):
        resultado = self.repositorio.condiciones(dni(documento))
        validar_elegibilidad(resultado['persona'])
        persona = resultado.pop('persona')
        return dict(resultado, solicitante=f'{persona["nombres"]} {persona["apellidos"]}')

    def listar(self, filtros, documento=None):
        estado = filtros.get('estado', '')
        if estado and estado not in (
            'ACTIVO',
            'DEVUELTO',
            'VENCIDO',
            'PARCIALMENTE_DEVUELTO',
            'PENDIENTES',
            'PERDIDOS',
        ):
            raise ValueError('Estado de préstamo inválido.')
        return self.repositorio.listar(
            dict(q=texto(filtros.get('q'), 'Búsqueda', 120), estado=estado), documento
        )

    def consultar(self, identificador, documento, gestionar=False):
        prestamo = self.repositorio.consultar(entero(identificador))
        if prestamo is None:
            raise NoEncontrado('Préstamo inexistente.')
        afectados = {
            prestamo['dni_persona'],
            *(p['dni_persona'] for p in prestamo['participantes']),
        }
        if not gestionar and dni(documento) not in afectados:
            raise PermissionError('Solo puedes consultar los préstamos en los que participas.')
        prestamo['historial'] = self.repositorio.consultar_historial(
            'PRESTAMO', prestamo['id_prestamo']
        )
        return prestamo

    def registrar(self, datos, actor):
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(operacion.cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR')
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
            return self.entregar_en_operacion(operacion, solicitud)

    @staticmethod
    def entregar_en_operacion(operacion, solicitud, bien_reservado=None):
        contexto = operacion.cargar_entrega(solicitud)
        plan = solicitud.planificar(contexto, bien_reservado)
        return operacion.guardar_entrega(solicitud, plan, contexto['ahora'])

    def devolver(self, identificador, datos, actor):
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
            cuenta = exigir_permiso(operacion.cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR')
            prestamo = operacion.consultar(entero(identificador), bloquear=True)
            if prestamo is None:
                raise NoEncontrado('Préstamo inexistente.')
            por_id = {d['id_detalle']: d for d in prestamo['detalles']}
            for devolucion in devoluciones:
                if devolucion.id_detalle not in por_id:
                    raise NoEncontrado('El bien seleccionado no pertenece al préstamo.')
                devolucion.validar(por_id[devolucion.id_detalle])
            ahora = operacion.ahora()
            for devolucion in devoluciones:
                detalle = por_id[devolucion.id_detalle]
                ServicioAplicacionSancion.registrar_retraso(operacion.sanciones, detalle, ahora)
                operacion.guardar_devolucion(detalle, devolucion, ahora, cuenta['dni_persona'])
                detalle['fecha_devolucion'] = ahora
            nuevo = estado_prestamo(prestamo['detalles'], ahora)
            operacion.guardar_estado(
                prestamo, nuevo, cuenta['dni_persona'], f'Recepción de {len(detalles)} bien(es).'
            )

    def reportar_perdida(self, identificador, detalle_id, motivo, actor):
        motivo = texto(motivo, 'Motivo de pérdida', 255, True)
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(operacion.cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR')
            prestamo = operacion.consultar(entero(identificador), bloquear=True)
            if prestamo is None:
                raise NoEncontrado('Préstamo inexistente.')
            detalle = next(
                (d for d in prestamo['detalles'] if d['id_detalle'] == entero(detalle_id)), None
            )
            if detalle is None:
                raise NoEncontrado('El bien no pertenece al préstamo.')
            if detalle['fecha_devolucion'] is not None or detalle['estado_bien'] != 'PRESTADO':
                raise Conflicto('El bien debe estar prestado y pendiente para reportar su pérdida.')
            operacion.guardar_perdida(prestamo, detalle, cuenta['dni_persona'], motivo)

    def actualizar_vencimientos(self, actor):
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(operacion.cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR')
            for fila in operacion.listar({'estado': 'VENCIDO'}):
                prestamo = operacion.consultar(fila['id_prestamo'], bloquear=True)
                nuevo = estado_prestamo(prestamo['detalles'], operacion.ahora())
                if nuevo != prestamo['estado']:
                    operacion.guardar_estado(
                        prestamo, nuevo, cuenta['dni_persona'], 'Vencimiento registrado.'
                    )
