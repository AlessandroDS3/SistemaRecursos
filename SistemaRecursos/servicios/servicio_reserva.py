from dominio.compartido.validacion import NoEncontrado
from dominio.compartido.validacion import Conflicto, dni, entero, texto
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_control.politica_prestamo import ConfiguracionReservas
from dominio.gestion_prestamos.prestamo import SolicitudPrestamo
from dominio.gestion_prestamos.reserva import (
    IRepositorioReserva,
    ESTADOS_RESERVA,
    nueva_reserva,
    validar_accion,
    validar_solicitud,
)
from servicios.servicio_prestamo import ServicioAplicacionPrestamo


class ServicioAplicacionReserva:
    def __init__(self, repositorio: IRepositorioReserva):
        self.repositorio = repositorio

    def consultar_recursos_para_reserva(self, documento):
        return self.repositorio.consultar_recursos_para_reserva(dni(documento))

    def consultar_reservas(self, documento=None, filtros=None):
        filtros = filtros or {}
        estado, tipo = filtros.get('estado', ''), filtros.get('tipo_gestion', '')
        if estado not in ('', *ESTADOS_RESERVA) or tipo not in ('', 'PRESTAMO', 'RESERVA'):
            raise ValueError('Estado o tipo de reserva inválidos.')
        return self.repositorio.consultar_reservas(
            documento,
            dict(estado=estado, tipo_gestion=tipo, q=texto(filtros.get('q'), 'Búsqueda', 120)),
        )

    def consultar_reserva(self, identificador, documento, gestionar=False):
        reserva = self.repositorio.consultar_reserva(entero(identificador))
        if reserva is None:
            raise NoEncontrado('Reserva inexistente.')
        if not gestionar and reserva['dni_persona'] != documento:
            raise PermissionError('Solo puedes consultar tus reservas.')
        reserva['historial'] = self.repositorio.consultar_historial_estado(
            'RESERVA', reserva['id_reserva']
        )
        return reserva

    def registrar_reserva(self, datos, actor):
        with self.repositorio.transaccion() as op:
            cuenta = exigir_permiso(
                op.consultar_cuenta_actor(entero(actor)), 'RESERVAS_PROPIAS_GESTIONAR'
            )
            reserva = nueva_reserva(datos, cuenta['dni_persona'], op.consultar_fecha_actual())
            contexto = op.consultar_contexto_reserva(reserva['dni_persona'], reserva['id_recurso'])
            validar_solicitud(reserva, contexto, comprobar_duplicada=True)
            configuracion = self._consultar_configuracion_reservas(op)
            reserva['fecha_limite_vencimiento'] = configuracion.vencimiento(
                reserva['fecha_requerida'], 'espera'
            )
            identificador = op.registrar_reserva(reserva)
            op.registrar_historial_estado(
                'RESERVA',
                identificador,
                None,
                'EN_ESPERA',
                cuenta['dni_persona'],
                'Solicitud registrada.',
            )
            return identificador

    @staticmethod
    def _consultar_configuracion_reservas(op):
        fila = op.consultar_configuracion_general()
        if fila is None:
            raise ValueError('Configura los plazos de reserva en Políticas.')
        return ConfiguracionReservas(
            **{k: fila[k] for k in ConfiguracionReservas.__dataclass_fields__}
        )

    def preparar_reserva(self, identificador, datos, actor):
        return self._resolver_reserva(identificador, 'preparar', datos, actor)

    def entregar_reserva(self, identificador, datos, actor):
        return self._resolver_reserva(identificador, 'entregar', datos, actor)

    def cancelar_reserva(self, identificador, datos, actor):
        return self._resolver_reserva(identificador, 'cancelar', datos, actor)

    def rechazar_reserva(self, identificador, datos, actor):
        return self._resolver_reserva(identificador, 'rechazar', datos, actor)

    def expirar_reserva(self, identificador, datos, actor):
        return self._resolver_reserva(identificador, 'expirar', datos, actor)

    def _resolver_reserva(self, identificador, accion, datos, actor):
        if accion not in ('preparar', 'entregar', 'cancelar', 'rechazar', 'expirar'):
            raise ValueError('Acción de reserva inválida.')
        with self.repositorio.transaccion() as op:
            cuenta = op.consultar_cuenta_actor(entero(actor))
            gestionar = bool(cuenta and 'PRESTAMOS_GESTIONAR' in cuenta['permisos'])
            exigir_permiso(
                cuenta, 'PRESTAMOS_GESTIONAR' if gestionar else 'RESERVAS_PROPIAS_GESTIONAR'
            )
            reserva = op.consultar_reserva(entero(identificador))
            if reserva is None:
                raise NoEncontrado('Reserva inexistente.')
            # Un recurso serializa la selección de la cola y de sus ejemplares.
            op.bloquear_recurso(reserva['id_recurso'])
            reserva = op.consultar_reserva(entero(identificador), bloquear=True)
            ahora = op.consultar_fecha_actual()
            validar_accion(reserva, accion, cuenta['dni_persona'], gestionar, ahora)
            cambios, nota = {}, ''
            if accion == 'preparar':
                validar_solicitud(
                    reserva,
                    op.consultar_contexto_reserva(reserva['dni_persona'], reserva['id_recurso']),
                )
                primera = op.consultar_primera_reserva_en_espera(reserva['id_recurso'], ahora)
                if primera is None or primera['id_reserva'] != reserva['id_reserva']:
                    raise Conflicto('Atiende primero la reserva anterior de este recurso.')
                bien = op.consultar_bien_disponible(reserva['id_recurso'])
                if bien is None:
                    raise Conflicto('No hay un bien disponible para preparar la reserva.')
                op.cambiar_estado_bien_reservado(
                    bien['id_bien'],
                    'RESERVADO',
                    'DISPONIBLE',
                    cuenta['dni_persona'],
                    reserva['id_reserva'],
                )
                cambios = dict(
                    estado='LISTA_PARA_RETIRO',
                    id_bien=bien['id_bien'],
                    fecha_preparacion=ahora,
                    fecha_limite_vencimiento=self._consultar_configuracion_reservas(op).vencimiento(
                        ahora, 'retiro'
                    ),
                )
                nota = 'Bien preparado para retiro.'
            elif accion == 'entregar':
                if datos.get('acepta_condiciones') != '1':
                    raise ValueError(
                        'Confirma que comunicaste el plazo y las condiciones de entrega.'
                    )
                if not reserva['id_bien'] or reserva['recurso_bien'] != reserva['id_recurso']:
                    raise Conflicto('El bien asignado no corresponde al recurso reservado.')
                solicitud = SolicitudPrestamo(
                    dni_persona=reserva['dni_persona'],
                    dni_encargado=cuenta['dni_persona'],
                    bienes=[reserva['id_bien']],
                    observaciones=reserva['observaciones'],
                    salida_solicitada=bool(reserva['salida_solicitada']),
                )
                prestamo = ServicioAplicacionPrestamo.registrar_prestamo_en_operacion(
                    op.prestamos, solicitud, reserva['id_bien']
                )
                cambios, nota = (
                    dict(estado='ATENDIDA', id_prestamo_ref=prestamo),
                    f'Préstamo #{prestamo} entregado.',
                )
            else:
                nota = texto(datos.get('motivo'), 'Motivo', 255, accion in ('rechazar', 'expirar'))
                cambios = dict(
                    estado={
                        'cancelar': 'CANCELADA',
                        'rechazar': 'RECHAZADA',
                        'expirar': 'EXPIRADA',
                    }[accion]
                )
                self._liberar_bien_reservado(op, reserva, cuenta['dni_persona'])
                cambios['id_bien'] = None
            op.actualizar_reserva(reserva['id_reserva'], cambios)
            op.registrar_historial_estado(
                'RESERVA',
                reserva['id_reserva'],
                reserva['estado'],
                cambios['estado'],
                cuenta['dni_persona'],
                nota,
            )
            return cambios.get('id_prestamo_ref')

    @staticmethod
    def _liberar_bien_reservado(op, reserva, actor):
        if reserva['id_bien'] is not None:
            op.cambiar_estado_bien_reservado(
                reserva['id_bien'], 'DISPONIBLE', 'RESERVADO', actor, reserva['id_reserva']
            )

    def expirar_reservas_vencidas(self):
        cantidad = 0
        for fila in self.repositorio.consultar_reservas_vencidas():
            with self.repositorio.transaccion() as op:
                reserva = op.consultar_reserva(fila['id_reserva'], bloquear=True)
                if reserva is None or reserva['estado'] not in ('EN_ESPERA', 'LISTA_PARA_RETIRO'):
                    continue
                if (
                    reserva['fecha_limite_vencimiento'] is None
                    or reserva['fecha_limite_vencimiento'] > op.consultar_fecha_actual()
                ):
                    continue
                self._liberar_bien_reservado(op, reserva, None)
                op.actualizar_reserva(reserva['id_reserva'], dict(estado='EXPIRADA', id_bien=None))
                op.registrar_historial_estado(
                    'RESERVA',
                    reserva['id_reserva'],
                    reserva['estado'],
                    'EXPIRADA',
                    None,
                    'Plazo vencido.',
                )
                cantidad += 1
        return cantidad
