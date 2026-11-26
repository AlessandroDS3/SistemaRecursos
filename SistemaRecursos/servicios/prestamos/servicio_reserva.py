from dataclasses import replace
from datetime import datetime
from typing import Mapping

from dominio.compartido.validacion import Conflicto, NoEncontrado, validar_dni, validar_entero, validar_texto
from dominio.gestion_control.politica_prestamo import ConfiguracionReservas, HorarioAtencion
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_prestamos.contratos_prestamos import IRepositorioReserva
from dominio.gestion_prestamos.prestamo import SolicitudPrestamo, TipoPrestamo, validar_cupo_articulos
from dominio.gestion_prestamos.reserva import (
    AccionReserva, DetalleReserva, ESTADOS_RESERVA, FILTRO_PENDIENTES,
    LISTA_PARA_RETIRO, Reserva, ReservaEnCola, validar_integrante_de_reserva,
    validar_recursos_de_reserva, validar_solicitante_y_recurso_para_reserva,
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
        reserva = Reserva.desde_detalle(fila)
        if not gestionar and documento not in (reserva.dni_persona, *reserva.participantes):
            raise PermissionError('Solo puedes consultar tus reservas.')
        return dict(
            fila,
            participantes=list(reserva.participantes),
            bienes=[fila, *self.repositorio.consultar_lineas_de_reserva(reserva.identificador)],
            historial=self.repositorio.consultar_historial_estado('RESERVA', reserva.identificador),
            ventana_atencion=reserva.ventana_atencion(self.repositorio.consultar_fecha_actual()),
        )

    def registrar_reserva(self, datos: Mapping, actor: int) -> int:
        recursos = validar_recursos_de_reserva(datos)
        with self.repositorio.transaccion() as op:
            cuenta = exigir_permiso(op.consultar_cuenta_actor(validar_entero(actor)), 'RESERVAS_PROPIAS_GESTIONAR')
            principal = Reserva.desde_formulario(
                dict(datos, id_recurso=recursos[0]), cuenta['dni_persona'], op.consultar_fecha_actual(),
            )
            lineas = [principal, *(replace(principal, id_recurso=r, participantes=()) for r in recursos[1:])]
            self._bloquear_recursos_y_personas(op, lineas)
            self._validar_cupo_y_recursos_de_reserva(op, lineas, nueva=True)
            configuracion = self._obtener_horario_y_plazos_de_reserva(op)
            HorarioAtencion.desde_datos(configuracion).obtener_cierre_si_hay_atencion(principal.fecha_requerida)
            limite = self._leer_plazos_de_reserva(configuracion).calcular_vencimiento_de_reserva(
                principal.fecha_requerida, 'espera',
            )
            identificador = op.guardar_nueva_reserva(principal.con_plazo_de_espera(limite))
            for linea in lineas[1:]:
                op.guardar_nueva_reserva(replace(linea.con_plazo_de_espera(limite), id_reserva_principal=identificador))
            op.registrar_historial_estado('RESERVA', identificador, None, principal.estado,
                                         principal.dni_persona, 'Solicitud registrada.')
            return identificador

    @staticmethod
    def _bloquear_recursos_y_personas(op: IRepositorioReserva, lineas: list[Reserva], operador: str | None = None):
        principal = lineas[0]
        personas = {principal.dni_persona, *principal.participantes}
        if operador:
            personas.add(operador)
        for recurso in sorted({linea.id_recurso for linea in lineas}):
            op.bloquear_recurso(recurso)
        for documento in sorted(personas):
            op.bloquear_persona(documento)

    @staticmethod
    def _validar_cupo_y_recursos_de_reserva(op: IRepositorioReserva, lineas: list[Reserva], nueva=False):
        principal = lineas[0]
        por_recurso = {linea.id_recurso: linea for linea in lineas if linea.id_recurso != principal.id_recurso}
        contexto = op.consultar_datos_para_validar_reserva(principal.dni_persona, principal.id_recurso)
        personas = [validar_solicitante_y_recurso_para_reserva(principal, contexto, comprobar_duplicada=nueva)]
        for linea in por_recurso.values():
            contexto = op.consultar_datos_para_validar_reserva(principal.dni_persona, linea.id_recurso)
            validar_solicitante_y_recurso_para_reserva(linea, contexto, comprobar_duplicada=nueva)
        for documento in principal.participantes:
            contexto = op.consultar_datos_para_validar_reserva(documento, principal.id_recurso)
            personas.append(validar_integrante_de_reserva(contexto))
        for persona in personas:
            validar_cupo_articulos(
                persona, op.prestamos.consultar_cupo_persona(persona, principal.id_reserva), len(lineas),
            )

    @classmethod
    def _consultar_reserva_para_actualizar(cls, op: IRepositorioReserva, identificador: int,
                                         operador: str | None = None) -> list[DetalleReserva]:
        principal = op.consultar_reserva(identificador)
        if principal is None:
            raise NoEncontrado(MENSAJE_RESERVA_INEXISTENTE)
        lineas = [principal, *op.consultar_lineas_de_reserva(identificador)]
        cls._bloquear_recursos_y_personas(op, [Reserva.desde_detalle(fila) for fila in lineas], operador)
        principal = op.consultar_reserva(identificador, bloquear=True)
        if principal is None:
            raise NoEncontrado(MENSAJE_RESERVA_INEXISTENTE)
        return [principal, *op.consultar_lineas_de_reserva(identificador, bloquear=True)]

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

    def _asignar_bienes_para_retiro(
        self, op: IRepositorioReserva, lineas: list[Reserva], actor: str, ahora: datetime
    ) -> list[Reserva]:
        principal = lineas[0]
        self._validar_cupo_y_recursos_de_reserva(op, lineas)
        for recurso in sorted({linea.id_recurso for linea in lineas}):
            if op.consultar_primera_reserva_en_espera(recurso, ahora) != principal.identificador:
                raise Conflicto('Atiende primero la reserva anterior de este recurso.')
        plazos = self._leer_plazos_de_reserva(self._obtener_horario_y_plazos_de_reserva(op))
        inicio_retiro = max(ahora, principal.fecha_requerida)
        limite = plazos.calcular_vencimiento_de_reserva(inicio_retiro, 'retiro')
        preparadas = []
        for linea in lineas:
            bien = op.consultar_bien_disponible(linea.id_recurso)
            if bien is None:
                raise Conflicto('Faltan bienes disponibles para preparar la reserva completa.')
            preparadas.append(linea.asignar_bien_para_retiro(bien, ahora, limite))
            op.cambiar_estado_bien_reservado(bien, 'RESERVADO', 'DISPONIBLE', actor, principal.identificador)
        return preparadas

    @staticmethod
    def _registrar_prestamo_de_reserva(
        op: IRepositorioReserva, lineas: list[Reserva], filas: list[DetalleReserva],
        actor: str, datos: Mapping[str, str], ahora: datetime,
    ) -> list[Reserva]:
        if datos.get('acepta_condiciones') != '1':
            raise ValueError('Confirma que comunicaste el plazo y las condiciones de entrega.')
        principal = lineas[0]
        bienes = []
        for linea, fila in zip(lineas, filas):
            if linea.id_bien is None or fila.get('recurso_bien') != linea.id_recurso:
                raise Conflicto('Uno de los bienes asignados no corresponde al recurso reservado.')
            bienes.append(linea.id_bien)
        solicitud = SolicitudPrestamo(
            dni_persona=principal.dni_persona, dni_encargado=actor, bienes=bienes,
            tipo_prestamo=TipoPrestamo.GRUPAL if principal.participantes else TipoPrestamo.INDIVIDUAL,
            participantes=list(principal.participantes),
            observaciones=principal.observaciones, salida_solicitada=principal.salida_solicitada,
        )
        prestamo = ServicioAplicacionPrestamo.registrar_entrega_prestamo_en_transaccion(
            op.prestamos, solicitud, frozenset(bienes), principal.identificador, codigo=datos.get('autorizacion'),
        )
        return [linea.marcar_atendida_con_prestamo(prestamo, ahora) for linea in lineas]

    def _procesar_accion_reserva(
        self, identificador: int, accion: AccionReserva, datos: Mapping[str, str], actor: int
    ) -> int | None:
        identificador = validar_entero(identificador)
        with self.repositorio.transaccion() as op:
            cuenta = op.consultar_cuenta_actor(validar_entero(actor))
            gestionar = bool(cuenta and 'PRESTAMOS_GESTIONAR' in cuenta['permisos'])
            cuenta = exigir_permiso(cuenta, 'PRESTAMOS_GESTIONAR' if gestionar else 'RESERVAS_PROPIAS_GESTIONAR')
            documento = cuenta['dni_persona']
            filas = self._consultar_reserva_para_actualizar(op, identificador, documento)
            lineas = [Reserva.desde_detalle(fila) for fila in filas]
            reserva = lineas[0]
            if not gestionar:
                if accion != 'cancelar':
                    raise PermissionError('La acción requiere gestionar préstamos.')
                if reserva.dni_persona != documento:
                    raise PermissionError('Solo puedes cancelar tus reservas.')
            ahora = op.consultar_fecha_actual()
            for linea in lineas:
                linea.validar_accion_reserva(accion, ahora)
            if accion == 'preparar':
                actualizadas = self._asignar_bienes_para_retiro(op, lineas, documento, ahora)
                nota = 'Reserva preparada para retiro.'
            elif accion == 'entregar':
                actualizadas = self._registrar_prestamo_de_reserva(op, lineas, filas, documento, datos, ahora)
                nota = f'Préstamo #{actualizadas[0].id_prestamo_ref} entregado.'
            else:
                actualizadas = [linea.cerrar_sin_entrega(accion, ahora) for linea in lineas]
                no_retirado = accion == 'expirar' and reserva.estado == LISTA_PARA_RETIRO
                nota = validar_texto(datos.get('motivo'), 'Motivo', 220 if no_retirado else 255, accion != 'cancelar')
                if no_retirado:
                    nota = f'{MENSAJE_NO_RETIRADO} {nota}'
                self._liberar_bienes_reservados(op, lineas, documento)
            self._guardar_estado_e_historial_reserva(op, reserva, actualizadas, documento, nota)
            return actualizadas[0].id_prestamo_ref if accion == 'entregar' else None

    @staticmethod
    def _guardar_estado_e_historial_reserva(
        op: IRepositorioReserva, anterior: Reserva, actuales: list[Reserva], actor: str | None, nota: str
    ) -> None:
        for linea in actuales:
            op.actualizar_reserva(linea)
        op.registrar_historial_estado('RESERVA', anterior.identificador, anterior.estado, actuales[0].estado, actor, nota)

    @staticmethod
    def _liberar_bienes_reservados(op: IRepositorioReserva, lineas: list[Reserva], actor: str | None) -> None:
        for linea in lineas:
            if linea.id_bien is not None:
                op.cambiar_estado_bien_reservado(
                    linea.id_bien, 'DISPONIBLE', 'RESERVADO', actor, lineas[0].identificador,
                )

    def expirar_reservas_vencidas(self) -> int:
        cantidad = 0
        for identificador in self.repositorio.consultar_reservas_vencidas():
            with self.repositorio.transaccion() as op:
                try:
                    filas = self._consultar_reserva_para_actualizar(op, identificador)
                except NoEncontrado:
                    continue
                lineas = [Reserva.desde_detalle(fila) for fila in filas]
                reserva = lineas[0]
                ahora = op.consultar_fecha_actual()
                if not reserva.puede_expirar(ahora):
                    continue
                expiradas = [linea.cerrar_sin_entrega('expirar', ahora) for linea in lineas]
                self._liberar_bienes_reservados(op, lineas, None)
                nota = MENSAJE_NO_RETIRADO if reserva.estado == LISTA_PARA_RETIRO else 'Plazo vencido.'
                self._guardar_estado_e_historial_reserva(op, reserva, expiradas, None, nota)
                cantidad += 1
        return cantidad
