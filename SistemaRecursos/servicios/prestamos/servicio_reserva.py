from datetime import datetime
from typing import Mapping

from dominio.compartido.validacion import Conflicto, NoEncontrado, validar_dni, validar_entero, validar_texto
from dominio.gestion_control.politica_prestamo import ConfiguracionReservas, HorarioAtencion
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_prestamos.contratos_prestamos import IRepositorioReserva
from dominio.gestion_prestamos.prestamo import SolicitudPrestamo, validar_cupo_articulos
from dominio.gestion_prestamos.reserva import (
    AccionReserva, DetalleReserva, ESTADOS_RESERVA, FILTRO_PENDIENTES,
    LISTA_PARA_RETIRO, Reserva, ReservaEnCola, validar_solicitante_y_recurso_para_reserva, ventana_atencion_reserva,
)
from servicios.prestamos.servicio_prestamo import ServicioAplicacionPrestamo

MENSAJE_RESERVA_INEXISTENTE = 'Reserva inexistente.'
MENSAJE_NO_RETIRADO = 'No retiró el bien preparado.'


class ServicioAplicacionReserva:
    def __init__(self, repositorio: IRepositorioReserva) -> None:
        self.repositorio = repositorio

    def consultar_recursos_para_reserva(self, documento: str) -> list[dict]:
        return self.repositorio.consultar_recursos_para_reserva(validar_dni(documento))

    def contar_reservas_pendientes(self, documento: str | None = None) -> int:
        return self.repositorio.contar_reservas_pendientes(documento)

    def consultar_reservas(
        self, documento: str | None = None, filtros: Mapping[str, str] | None = None
    ) -> list[ReservaEnCola]:
        filtros = filtros or {}
        estado, tipo = filtros.get('estado', ''), filtros.get('tipo_gestion', '')
        if estado not in ('', FILTRO_PENDIENTES, *ESTADOS_RESERVA) or tipo not in ('', 'PRESTAMO', 'RESERVA'):
            raise ValueError('Estado o tipo de reserva inválidos.')
        return self.repositorio.consultar_reservas(
            documento, dict(estado=estado, tipo_gestion=tipo, q=validar_texto(filtros.get('q'), 'Búsqueda', 120)),
        )

    def consultar_reserva(self, identificador: int, documento: str, gestionar: bool = False) -> DetalleReserva:
        fila = self.repositorio.consultar_reserva(validar_entero(identificador))
        if fila is None:
            raise NoEncontrado(MENSAJE_RESERVA_INEXISTENTE)
        if not gestionar and fila['dni_persona'] != documento:
            raise PermissionError('Solo puedes consultar tus reservas.')
        fila['historial'] = self.repositorio.consultar_historial_estado('RESERVA', fila['id_reserva'])
        fila['ventana_atencion'] = ventana_atencion_reserva(
            fila['fecha_requerida'], fila['fecha_limite_vencimiento'], self.repositorio.consultar_fecha_actual(),
        )
        return fila

    def registrar_reserva(self, datos: Mapping[str, str], actor: int) -> int:
        with self.repositorio.transaccion() as op:
            cuenta = exigir_permiso(op.consultar_cuenta_actor(validar_entero(actor)), 'RESERVAS_PROPIAS_GESTIONAR')
            reserva = Reserva.desde_formulario(datos, cuenta['dni_persona'], op.consultar_fecha_actual())
            contexto = op.consultar_datos_para_validar_reserva(reserva.dni_persona, reserva.id_recurso)
            persona = validar_solicitante_y_recurso_para_reserva(reserva, contexto, comprobar_duplicada=True)
            validar_cupo_articulos(persona, op.prestamos.consultar_cupo_persona(persona))
            configuracion = self._obtener_horario_y_plazos_de_reserva(op)
            HorarioAtencion.desde_datos(configuracion).obtener_cierre_si_hay_atencion(reserva.fecha_requerida)
            limite = self._leer_plazos_de_reserva(configuracion).calcular_vencimiento_de_reserva(reserva.fecha_requerida, 'espera')
            identificador = op.guardar_nueva_reserva(reserva.con_plazo_de_espera(limite))
            op.registrar_historial_estado('RESERVA', identificador, None, reserva.estado,
                                         cuenta['dni_persona'], 'Solicitud registrada.')
            return identificador

    @staticmethod
    def _obtener_horario_y_plazos_de_reserva(op: IRepositorioReserva) -> dict:
        fila = op.consultar_horario_y_plazos_de_reserva()
        if fila is None:
            raise ValueError('Configura los plazos de reserva en Políticas.')
        return fila

    @staticmethod
    def _leer_plazos_de_reserva(fila: dict) -> ConfiguracionReservas:
        return ConfiguracionReservas(**{k: fila[k] for k in ConfiguracionReservas.__dataclass_fields__})

    def preparar_reserva(self, identificador: int, datos: Mapping[str, str], actor: int) -> int | None:
        return self._procesar_accion_reserva(identificador, 'preparar', datos, actor)

    def entregar_reserva(self, identificador: int, datos: Mapping[str, str], actor: int) -> int | None:
        return self._procesar_accion_reserva(identificador, 'entregar', datos, actor)

    def cancelar_reserva(self, identificador: int, datos: Mapping[str, str], actor: int) -> int | None:
        return self._procesar_accion_reserva(identificador, 'cancelar', datos, actor)

    def rechazar_reserva(self, identificador: int, datos: Mapping[str, str], actor: int) -> int | None:
        return self._procesar_accion_reserva(identificador, 'rechazar', datos, actor)

    def expirar_reserva(self, identificador: int, datos: Mapping[str, str], actor: int) -> int | None:
        return self._procesar_accion_reserva(identificador, 'expirar', datos, actor)

    def _asignar_bien_para_retiro(
        self, op: IRepositorioReserva, reserva: Reserva, actor: str, ahora: datetime
    ) -> Reserva:
        contexto = op.consultar_datos_para_validar_reserva(reserva.dni_persona, reserva.id_recurso)
        persona = validar_solicitante_y_recurso_para_reserva(reserva, contexto)
        validar_cupo_articulos(persona, op.prestamos.consultar_cupo_persona(persona, reserva.identificador))
        if op.consultar_primera_reserva_en_espera(reserva.id_recurso, ahora) != reserva.identificador:
            raise Conflicto('Atiende primero la reserva anterior de este recurso.')
        bien = op.consultar_bien_disponible(reserva.id_recurso)
        if bien is None:
            raise Conflicto('No hay un bien disponible para preparar la reserva.')
        plazos = self._leer_plazos_de_reserva(self._obtener_horario_y_plazos_de_reserva(op))
        inicio_retiro = max(ahora, reserva.fecha_requerida)
        limite = plazos.calcular_vencimiento_de_reserva(inicio_retiro, 'retiro')
        preparada = reserva.asignar_bien_para_retiro(bien, ahora, limite)
        op.cambiar_estado_bien_reservado(bien, 'RESERVADO', 'DISPONIBLE', actor, reserva.identificador)
        return preparada

    @staticmethod
    def _registrar_prestamo_de_reserva(
        op: IRepositorioReserva, reserva: Reserva, recurso_bien: int | None,
        actor: str, datos: Mapping[str, str], ahora: datetime,
    ) -> Reserva:
        if datos.get('acepta_condiciones') != '1':
            raise ValueError('Confirma que comunicaste el plazo y las condiciones de entrega.')
        bien = reserva.id_bien
        if bien is None or recurso_bien != reserva.id_recurso:
            raise Conflicto('El bien asignado no corresponde al recurso reservado.')
        solicitud = SolicitudPrestamo(
            dni_persona=reserva.dni_persona, dni_encargado=actor, bienes=[bien],
            observaciones=reserva.observaciones, salida_solicitada=reserva.salida_solicitada,
        )
        prestamo = ServicioAplicacionPrestamo.registrar_entrega_prestamo_en_transaccion(
            op.prestamos, solicitud, bien, reserva.identificador, codigo=datos.get('autorizacion'),
        )
        return reserva.marcar_atendida_con_prestamo(prestamo, ahora)

    def _procesar_accion_reserva(
        self, identificador: int, accion: AccionReserva, datos: Mapping[str, str], actor: int
    ) -> int | None:
        identificador = validar_entero(identificador)
        with self.repositorio.transaccion() as op:
            cuenta = op.consultar_cuenta_actor(validar_entero(actor))
            gestionar = bool(cuenta and 'PRESTAMOS_GESTIONAR' in cuenta['permisos'])
            cuenta = exigir_permiso(cuenta, 'PRESTAMOS_GESTIONAR' if gestionar else 'RESERVAS_PROPIAS_GESTIONAR')
            documento = cuenta['dni_persona']
            fila = op.consultar_reserva(identificador)
            if fila is None:
                raise NoEncontrado(MENSAJE_RESERVA_INEXISTENTE)
            # El recurso serializa la cola y la selección de ejemplar.
            op.bloquear_recurso(fila['id_recurso'])
            op.bloquear_persona(fila['dni_persona'])
            fila = op.consultar_reserva(identificador, bloquear=True)
            if fila is None:
                raise NoEncontrado(MENSAJE_RESERVA_INEXISTENTE)
            reserva = Reserva.desde_detalle(fila)
            if not gestionar:
                if accion != 'cancelar':
                    raise PermissionError('La acción requiere gestionar préstamos.')
                if reserva.dni_persona != documento:
                    raise PermissionError('Solo puedes cancelar tus reservas.')
            ahora = op.consultar_fecha_actual()
            reserva.validar_accion_reserva(accion, ahora)
            if accion == 'preparar':
                actualizada = self._asignar_bien_para_retiro(op, reserva, documento, ahora)
                nota = 'Bien preparado para retiro.'
            elif accion == 'entregar':
                actualizada = self._registrar_prestamo_de_reserva(op, reserva, fila.get('recurso_bien'), documento, datos, ahora)
                nota = f'Préstamo #{actualizada.id_prestamo_ref} entregado.'
            else:
                actualizada = reserva.cerrar_sin_entrega(accion, ahora)
                no_retirado = accion == 'expirar' and reserva.estado == LISTA_PARA_RETIRO
                nota = validar_texto(datos.get('motivo'), 'Motivo', 220 if no_retirado else 255, accion != 'cancelar')
                if no_retirado:
                    nota = f'{MENSAJE_NO_RETIRADO} {nota}'
                self._liberar_bien_reservado(op, reserva, documento)
            self._guardar_estado_e_historial_reserva(op, reserva, actualizada, documento, nota)
            return actualizada.id_prestamo_ref if accion == 'entregar' else None

    @staticmethod
    def _guardar_estado_e_historial_reserva(
        op: IRepositorioReserva, anterior: Reserva, actual: Reserva, actor: str | None, nota: str
    ) -> None:
        op.actualizar_reserva(actual)
        op.registrar_historial_estado('RESERVA', actual.identificador, anterior.estado, actual.estado, actor, nota)

    @staticmethod
    def _liberar_bien_reservado(op: IRepositorioReserva, reserva: Reserva, actor: str | None) -> None:
        if reserva.id_bien is not None:
            op.cambiar_estado_bien_reservado(
                reserva.id_bien, 'DISPONIBLE', 'RESERVADO', actor, reserva.identificador,
            )

    def expirar_reservas_vencidas(self) -> int:
        cantidad = 0
        for identificador in self.repositorio.consultar_reservas_vencidas():
            with self.repositorio.transaccion() as op:
                fila = op.consultar_reserva(identificador, bloquear=True)
                if fila is None:
                    continue
                reserva = Reserva.desde_detalle(fila)
                ahora = op.consultar_fecha_actual()
                if not reserva.puede_expirar(ahora):
                    continue
                expirada = reserva.cerrar_sin_entrega('expirar', ahora)
                self._liberar_bien_reservado(op, reserva, None)
                nota = MENSAJE_NO_RETIRADO if reserva.estado == LISTA_PARA_RETIRO else 'Plazo vencido.'
                self._guardar_estado_e_historial_reserva(op, reserva, expirada, None, nota)
                cantidad += 1
        return cantidad
