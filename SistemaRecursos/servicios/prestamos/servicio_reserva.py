from datetime import datetime
from typing import Mapping

from dominio.compartido.validacion import Conflicto, NoEncontrado, dni, entero, texto
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_control.politica_prestamo import ConfiguracionReservas
from dominio.gestion_prestamos.contratos_prestamos import IRepositorioReserva
from dominio.gestion_prestamos.prestamo import SolicitudPrestamo
from dominio.gestion_prestamos.reserva import (
    ATENDIDA,
    CambiosReserva,
    DetalleReserva,
    EN_ESPERA,
    ESTADOS_CIERRE,
    ESTADOS_PENDIENTES,
    ESTADOS_POR_ACCION,
    ESTADOS_RESERVA,
    EXPIRADA,
    FILTRO_PENDIENTES,
    LISTA_PARA_RETIRO,
    Reserva,
    nueva_reserva,
    validar_accion,
    validar_solicitud,
    ventana_atencion_reserva,
)
from servicios.prestamos.servicio_prestamo import ServicioAplicacionPrestamo

MENSAJE_RESERVA_INEXISTENTE = 'Reserva inexistente.'


class ServicioAplicacionReserva:
    def __init__(self, repositorio: IRepositorioReserva) -> None:
        self.repositorio = repositorio

    def consultar_recursos_para_reserva(self, documento: str) -> list[dict]:
        return self.repositorio.consultar_recursos_para_reserva(dni(documento))

    def contar_reservas_pendientes(self, documento: str | None = None) -> int:
        return self.repositorio.contar_reservas_pendientes(documento)

    def consultar_reservas(
        self, documento: str | None = None, filtros: Mapping[str, str] | None = None
    ) -> list[Reserva]:
        filtros = filtros or {}
        estado, tipo = filtros.get('estado', ''), filtros.get('tipo_gestion', '')
        if estado not in ('', FILTRO_PENDIENTES, *ESTADOS_RESERVA) or tipo not in ('', 'PRESTAMO', 'RESERVA'):
            raise ValueError('Estado o tipo de reserva inválidos.')
        return self.repositorio.consultar_reservas(
            documento,
            {
                'estado': estado,
                'tipo_gestion': tipo,
                'q': texto(filtros.get('q'), 'Búsqueda', 120),
            },
        )

    def consultar_reserva(
        self, identificador: int, documento: str, gestionar: bool = False
    ) -> DetalleReserva:
        reserva = self.repositorio.consultar_reserva(entero(identificador))
        if reserva is None:
            raise NoEncontrado(MENSAJE_RESERVA_INEXISTENTE)
        if not gestionar and reserva['dni_persona'] != documento:
            raise PermissionError('Solo puedes consultar tus reservas.')
        reserva['historial'] = self.repositorio.consultar_historial_estado(
            'RESERVA', reserva['id_reserva']
        )
        reserva['ventana_atencion'] = ventana_atencion_reserva(
            reserva, self.repositorio.consultar_fecha_actual()
        )
        return reserva

    def registrar_reserva(self, datos: Mapping[str, str], actor: int) -> int:
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
                EN_ESPERA,
                cuenta['dni_persona'],
                'Solicitud registrada.',
            )
            return identificador

    @staticmethod
    def _consultar_configuracion_reservas(op: IRepositorioReserva) -> ConfiguracionReservas:
        fila = op.consultar_configuracion_general()
        if fila is None:
            raise ValueError('Configura los plazos de reserva en Políticas.')
        return ConfiguracionReservas(
            **{k: fila[k] for k in ConfiguracionReservas.__dataclass_fields__}
        )

    def preparar_reserva(
        self, identificador: int, datos: Mapping[str, str], actor: int
    ) -> int | None:
        return self._resolver_reserva(identificador, 'preparar', datos, actor)

    def entregar_reserva(
        self, identificador: int, datos: Mapping[str, str], actor: int
    ) -> int | None:
        return self._resolver_reserva(identificador, 'entregar', datos, actor)

    def cancelar_reserva(
        self, identificador: int, datos: Mapping[str, str], actor: int
    ) -> int | None:
        return self._resolver_reserva(identificador, 'cancelar', datos, actor)

    def rechazar_reserva(
        self, identificador: int, datos: Mapping[str, str], actor: int
    ) -> int | None:
        return self._resolver_reserva(identificador, 'rechazar', datos, actor)

    def expirar_reserva(
        self, identificador: int, datos: Mapping[str, str], actor: int
    ) -> int | None:
        return self._resolver_reserva(identificador, 'expirar', datos, actor)

    def _preparar_reserva(
        self, op: IRepositorioReserva, reserva: DetalleReserva, cuenta: dict, ahora: datetime
    ) -> tuple[CambiosReserva, str]:
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
        cambios: CambiosReserva = {
            'estado': LISTA_PARA_RETIRO,
            'id_bien': bien['id_bien'],
            'fecha_preparacion': ahora,
            'fecha_limite_vencimiento': self._consultar_configuracion_reservas(op).vencimiento(
                ahora, 'retiro'
            ),
        }
        return cambios, 'Bien preparado para retiro.'

    @staticmethod
    def _entregar_reserva(
        op: IRepositorioReserva, reserva: DetalleReserva, cuenta: dict, datos: Mapping[str, str]
    ) -> tuple[CambiosReserva, str]:
        if datos.get('acepta_condiciones') != '1':
            raise ValueError('Confirma que comunicaste el plazo y las condiciones de entrega.')
        bien = reserva['id_bien']
        if not bien or reserva['recurso_bien'] != reserva['id_recurso']:
            raise Conflicto('El bien asignado no corresponde al recurso reservado.')
        solicitud = SolicitudPrestamo(
            dni_persona=reserva['dni_persona'],
            dni_encargado=cuenta['dni_persona'],
            bienes=[bien],
            observaciones=reserva['observaciones'],
            salida_solicitada=bool(reserva['salida_solicitada']),
        )
        prestamo = ServicioAplicacionPrestamo.registrar_prestamo_en_operacion(
            op.prestamos, solicitud, bien
        )
        return (
            {'estado': ATENDIDA, 'id_prestamo_ref': prestamo},
            f'Préstamo #{prestamo} entregado.',
        )

    def _cerrar_reserva(
        self,
        op: IRepositorioReserva,
        reserva: DetalleReserva,
        cuenta: dict,
        accion: str,
        datos: Mapping[str, str],
    ) -> tuple[CambiosReserva, str]:
        nota = texto(datos.get('motivo'), 'Motivo', 255, accion in ('rechazar', 'expirar'))
        self._liberar_bien_reservado(op, reserva, cuenta['dni_persona'])
        # Liberar el inventario no borra qué bien se preparó para esta reserva.
        return {'estado': ESTADOS_CIERRE[accion]}, nota

    def _resolver_reserva(
        self, identificador: int, accion: str, datos: Mapping[str, str], actor: int
    ) -> int | None:
        if accion not in ESTADOS_POR_ACCION:
            raise ValueError('Acción de reserva inválida.')
        with self.repositorio.transaccion() as op:
            cuenta = op.consultar_cuenta_actor(entero(actor))
            gestionar = bool(cuenta and 'PRESTAMOS_GESTIONAR' in cuenta['permisos'])
            cuenta = exigir_permiso(
                cuenta, 'PRESTAMOS_GESTIONAR' if gestionar else 'RESERVAS_PROPIAS_GESTIONAR'
            )
            reserva = op.consultar_reserva(entero(identificador))
            if reserva is None:
                raise NoEncontrado(MENSAJE_RESERVA_INEXISTENTE)
            # Un recurso serializa la selección de la cola y de sus ejemplares.
            op.bloquear_recurso(reserva['id_recurso'])
            reserva = op.consultar_reserva(entero(identificador), bloquear=True)
            if reserva is None:
                raise NoEncontrado(MENSAJE_RESERVA_INEXISTENTE)
            ahora = op.consultar_fecha_actual()
            validar_accion(reserva, accion, cuenta['dni_persona'], gestionar, ahora)
            if accion == 'preparar':
                cambios, nota = self._preparar_reserva(op, reserva, cuenta, ahora)
            elif accion == 'entregar':
                cambios, nota = self._entregar_reserva(op, reserva, cuenta, datos)
            else:
                cambios, nota = self._cerrar_reserva(op, reserva, cuenta, accion, datos)
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
    def _liberar_bien_reservado(
        op: IRepositorioReserva, reserva: DetalleReserva, actor: str | None
    ) -> None:
        if reserva['id_bien'] is not None:
            op.cambiar_estado_bien_reservado(
                reserva['id_bien'], 'DISPONIBLE', 'RESERVADO', actor, reserva['id_reserva']
            )

    def expirar_reservas_vencidas(self) -> int:
        cantidad = 0
        for fila in self.repositorio.consultar_reservas_vencidas():
            with self.repositorio.transaccion() as op:
                reserva = op.consultar_reserva(fila['id_reserva'], bloquear=True)
                if reserva is None or reserva['estado'] not in ESTADOS_PENDIENTES:
                    continue
                if (
                    reserva['fecha_limite_vencimiento'] is None
                    or reserva['fecha_limite_vencimiento'] > op.consultar_fecha_actual()
                ):
                    continue
                self._liberar_bien_reservado(op, reserva, None)
                op.actualizar_reserva(reserva['id_reserva'], {'estado': EXPIRADA})
                op.registrar_historial_estado(
                    'RESERVA',
                    reserva['id_reserva'],
                    reserva['estado'],
                    EXPIRADA,
                    None,
                    'Plazo vencido.',
                )
                cantidad += 1
        return cantidad
