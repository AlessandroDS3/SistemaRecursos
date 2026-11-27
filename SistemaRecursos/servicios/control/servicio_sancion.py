"""Casos de uso de sanciones; coordina dominio y repositorios en una transacción."""

from datetime import datetime
from typing import Mapping

from dominio.compartido.validacion import (
    Conflicto,
    NoEncontrado,
    exigir_version_vigente,
    validar_entero,
    validar_texto,
    calcular_version_de_registro,
)
from dominio.gestion_control.contratos_control import IRepositorioSancion
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_recursos.bien_material import BienMaterial, CondicionBien
from dominio.gestion_recursos.mantenimiento import AperturaMantenimiento
from dominio.gestion_prestamos.contratos_prestamos import IRepositorioPrestamo
from dominio.gestion_prestamos.devolucion import Devolucion
from dominio.gestion_prestamos.prestamo import calcular_estado_prestamo
from dominio.gestion_control.sancion import (
    ConfiguracionSanciones, ESTADOS_SANCION, EstadoSancion, calcular_alertas_de_sancion,
    exigir_administrador, validar_levantamiento_de_sancion, validar_regularizacion_sancion,
    validar_aceptacion_de_reparacion, validar_devolucion_para_verificacion,
)

from servicios.control.operaciones_sancion import (
    registrar_regularizacion_sancion, registrar_cierre_sancion, marcar_sancion_cumplida_si_corresponde, aplicar_o_reevaluar_sancion,
    registrar_sancion_por_retraso,
)
from servicios.prestamos.servicio_prestamo import ServicioAplicacionPrestamo


class ServicioAplicacionSancion:
    def __init__(self, repositorio: IRepositorioSancion):
        self.repositorio = repositorio

    def consultar_configuracion_sanciones(self):
        datos = ConfiguracionSanciones.desde_datos(self.repositorio.consultar_configuracion_sanciones() or {}).como_diccionario()
        return datos, calcular_version_de_registro(datos)

    def guardar_configuracion_sanciones(self, datos, version_recibida, actor):
        campos = ConfiguracionSanciones.__dataclass_fields__
        if any(k not in datos for k in campos):
            raise ValueError('Completa los tres plazos de sanciones.')
        nuevos = ConfiguracionSanciones.desde_datos(datos).como_diccionario()
        with self.repositorio.transaccion() as op:
            cuenta = exigir_permiso(op.consultar_cuenta_actor(validar_entero(actor)), 'PRESTAMOS_GESTIONAR')
            exigir_administrador(cuenta)
            actual = op.consultar_configuracion_sanciones(bloquear=True)
            if actual is None:
                raise Conflicto('Configura primero el horario general en Políticas.')
            exigir_version_vigente(version_recibida, calcular_version_de_registro(ConfiguracionSanciones.desde_datos(actual).como_diccionario()))
            op.guardar_configuracion_sanciones(nuevos)
            op.registrar_historial_estado(
                'CONFIGURACION_SANCIONES', 1, None, 'ACTUALIZADA', cuenta['dni_persona'],
                f'Leve: {nuevos["dias_leve"]} días; grave: {nuevos["dias_grave"]} días; '
                f'espera adicional: {nuevos["dias_espera_perdida"]} días.',
            )

    def procesar_sanciones_por_vencimiento(self):
        creadas = 0
        for fila in self.repositorio.consultar_detalles_de_prestamo_vencidos():
            with self.repositorio.transaccion() as op:
                prestamo = op.prestamos.consultar_prestamo_para_actualizar(fila['id_prestamo'])
                if prestamo is None:
                    continue
                detalle = next(
                    (d for d in prestamo['detalles'] if d['id_detalle'] == fila['id_detalle']), None,
                )
                if detalle and not detalle['fecha_devolucion'] and not detalle['fecha_regularizacion']:
                    creadas += registrar_sancion_por_retraso(op, detalle, op.consultar_fecha_actual())
        for fila in self.repositorio.consultar_sanciones_activas_para_revision():
            with self.repositorio.transaccion() as op:
                sancion, _ = self._bloquear_sancion_y_prestamo(op, fila['id_sancion'])
                marcar_sancion_cumplida_si_corresponde(op, sancion, op.consultar_fecha_actual())
        return creadas

    def consultar_sanciones(self, filtros=None):
        filtros = filtros or {}
        estado = filtros.get('estado', '')
        if estado not in ('', *ESTADOS_SANCION):
            raise ValueError('Estado de sanción inválido.')
        ahora = self.repositorio.consultar_fecha_actual()
        return [dict(s, **calcular_alertas_de_sancion(s, ahora)) for s in self.repositorio.consultar_sanciones(
            dict(estado=estado, q=validar_texto(filtros.get('q'), 'Búsqueda', 120))
        )]

    def consultar_sancion(self, identificador):
        sancion = self.repositorio.consultar_detalle_sancion(validar_entero(identificador))
        if sancion is None:
            raise NoEncontrado('Sanción inexistente.')
        sancion.update(calcular_alertas_de_sancion(sancion, self.repositorio.consultar_fecha_actual()))
        sancion['historial'] = self.repositorio.consultar_historial_estado('SANCION', sancion['id_sancion'])
        return sancion

    @staticmethod
    def _bloquear_sancion_y_prestamo(op, identificador):
        inicial = op.consultar_sancion(identificador)
        if inicial is None:
            raise NoEncontrado('Sanción inexistente.')
        prestamo = op.prestamos.consultar_prestamo_para_actualizar(inicial['id_prestamo'])
        return op.consultar_sancion(identificador, bloquear=True), prestamo

    def levantar_sancion(self, identificador, justificacion, actor):
        with self.repositorio.transaccion() as op:
            cuenta = exigir_permiso(op.consultar_cuenta_actor(validar_entero(actor)), 'PRESTAMOS_GESTIONAR')
            sancion, prestamo = self._bloquear_sancion_y_prestamo(op, validar_entero(identificador))
            ServicioAplicacionPrestamo.exigir_operador_que_no_participe_en_el_prestamo(op.prestamos, prestamo, cuenta['dni_persona'])
            ahora = op.consultar_fecha_actual()
            nota = validar_levantamiento_de_sancion(sancion, justificacion, ahora, cuenta)
            registrar_cierre_sancion(op, sancion, EstadoSancion.LEVANTADA, nota, cuenta['dni_persona'], ahora)

    def anular_sancion(self, identificador, motivo, actor):
        motivo = validar_texto(motivo, 'Motivo de anulación', 255, True)
        with self.repositorio.transaccion() as op:
            cuenta = exigir_permiso(op.consultar_cuenta_actor(validar_entero(actor)), 'PRESTAMOS_GESTIONAR')
            exigir_administrador(cuenta)
            sancion, prestamo = self._bloquear_sancion_y_prestamo(op, validar_entero(identificador))
            ServicioAplicacionPrestamo.exigir_operador_que_no_participe_en_el_prestamo(op.prestamos, prestamo, cuenta['dni_persona'])
            if sancion['estado'] == EstadoSancion.ANULADA:
                raise Conflicto('La sanción ya fue anulada.')
            registrar_cierre_sancion(op, sancion, EstadoSancion.ANULADA, motivo, cuenta['dni_persona'], op.consultar_fecha_actual())

    def registrar_recuperacion_del_bien_original(self, identificador, motivo, actor):
        apertura = AperturaMantenimiento(tipo='CORRECTIVO', motivo=motivo)
        with self.repositorio.transaccion() as op:
            cuenta = exigir_permiso(op.consultar_cuenta_actor(validar_entero(actor)), 'PRESTAMOS_GESTIONAR')
            exigir_administrador(cuenta)
            sancion, prestamo = self._bloquear_sancion_y_prestamo(op, validar_entero(identificador))
            ServicioAplicacionPrestamo.exigir_operador_que_no_participe_en_el_prestamo(op.prestamos, prestamo, cuenta['dni_persona'])
            if (sancion['tipo'] != 'PERDIDA' or not sancion['id_bien_reposicion']
                    or sancion['estado_bien'] != 'PERDIDO' or sancion['fecha_recuperacion_original']):
                raise Conflicto('Solo se registra aquí la recuperación de un bien perdido que ya fue repuesto.')
            bien = sancion['id_bien']
            if op.bienes.consultar_prestamo_pendiente(bien) or op.bienes.consultar_mantenimiento_abierto(bien):
                raise Conflicto('Resuelve primero los pendientes abiertos del bien original.')
            dni_actor = cuenta['dni_persona']
            op.bienes.abrir_mantenimiento(bien, apertura, 'PERDIDO', dni_actor)
            op.bienes.cambiar_estado_bien_material(bien, 'PERDIDO', 'MANTENIMIENTO', apertura.motivo, dni_actor)
            op.actualizar_sancion(sancion['id_sancion'], dict(fecha_recuperacion_original=op.consultar_fecha_actual()))
            op.registrar_historial_estado('SANCION', sancion['id_sancion'], sancion['estado'], sancion['estado'],
                                         dni_actor, f'Original recuperado. {apertura.motivo}'[:255])

    @staticmethod
    def _evaluar_falta_del_bien_prestado(op: IRepositorioSancion, prestamo, detalle, datos, cuenta):
        prestamos: IRepositorioPrestamo = op.prestamos
        ServicioAplicacionPrestamo.exigir_operador_que_no_participe_en_el_prestamo(prestamos, prestamo, cuenta['dni_persona'])
        causa = datos.get('causa')
        politica = None
        if causa in ('SALIDA_NO_AUTORIZADA', 'CUSTODIA'):
            politica = prestamos.consultar_politica_aplicada(detalle['id_politica'])
        sancion = aplicar_o_reevaluar_sancion(
            op, detalle, causa, datos.get('gravedad'), datos.get('motivo'),
            cuenta, op.consultar_fecha_actual(), politica=politica,
        )
        if causa == 'PERDIDA' and detalle['estado_bien'] == 'PRESTADO':
            prestamos.registrar_perdida_bien_material(
                prestamo, detalle, cuenta['dni_persona'], datos['motivo'],
            )
        return sancion['id_sancion']

    def evaluar_sancion(self, identificador, datos, actor):
        with self.repositorio.transaccion() as op:
            cuenta = exigir_permiso(op.consultar_cuenta_actor(validar_entero(actor)), 'PRESTAMOS_GESTIONAR')
            sancion, prestamo = self._bloquear_sancion_y_prestamo(op, validar_entero(identificador))
            detalle = next(d for d in prestamo['detalles'] if d['id_detalle'] == sancion['id_detalle'])
            self._evaluar_falta_del_bien_prestado(op, prestamo, detalle, datos, cuenta)

    def aplicar_sancion_a_bien_prestado(self, prestamo_id, detalle_id, datos, actor):
        with self.repositorio.transaccion() as op:
            cuenta = exigir_permiso(op.consultar_cuenta_actor(validar_entero(actor)), 'PRESTAMOS_GESTIONAR')
            prestamo = op.prestamos.consultar_prestamo_para_actualizar(validar_entero(prestamo_id))
            if prestamo is None:
                raise NoEncontrado('Préstamo inexistente.')
            detalle_id = validar_entero(detalle_id)
            detalle = next((d for d in prestamo['detalles'] if d['id_detalle'] == detalle_id), None)
            if detalle is None:
                raise NoEncontrado('El bien no pertenece al préstamo.')
            return self._evaluar_falta_del_bien_prestado(op, prestamo, detalle, datos, cuenta)

    def regularizar_sancion(self, identificador: int, datos: Mapping[str, str], actor: int) -> None:
        with self.repositorio.transaccion() as op:
            cuenta = exigir_permiso(op.consultar_cuenta_actor(validar_entero(actor)), 'PRESTAMOS_GESTIONAR')
            sancion, prestamo = self._bloquear_sancion_y_prestamo(op, validar_entero(identificador))
            documento = cuenta['dni_persona']
            tipo = datos.get('tipo_regularizacion')
            es_recepcion = tipo in ('RECUPERACION', 'REPOSICION')
            if not es_recepcion:
                ServicioAplicacionPrestamo.exigir_operador_que_no_participe_en_el_prestamo(op.prestamos, prestamo, documento)
            nota = validar_regularizacion_sancion(sancion, tipo, datos.get('observacion'))
            detalle = next(d for d in prestamo['detalles'] if d['id_detalle'] == sancion['id_detalle'])
            ahora = op.consultar_fecha_actual()
            autorizacion = (
                ServicioAplicacionPrestamo.validar_autorizacion_si_es_recepcion_propia(
                    op.prestamos, prestamo, documento, datos.get('autorizacion'),
                ) if es_recepcion else None
            )
            reposicion = None
            if tipo == 'REPOSICION':
                reposicion = self._regularizar_por_reposicion(op, sancion, detalle, datos, documento, nota, ahora)
            elif tipo == 'RECUPERACION':
                self._regularizar_por_recuperacion(op.prestamos, detalle, datos.get('codigo_recibido'), documento, nota, ahora)
            elif tipo == 'REPARACION':
                self._regularizar_por_reparacion(op, sancion['id_bien'], detalle, documento, nota)
            else:
                validar_devolucion_para_verificacion(detalle)
            registrar_regularizacion_sancion(op, sancion, tipo, nota, documento, ahora, reposicion)
            estado = calcular_estado_prestamo(prestamo['detalles'], ahora)
            op.prestamos.actualizar_estado_prestamo(
                prestamo, estado, documento,
                f'Regularización {tipo} del detalle #{detalle["id_detalle"]}.',
            )
            if autorizacion:
                ServicioAplicacionPrestamo.registrar_uso_autorizacion(op.prestamos, autorizacion,
                                                                   prestamo['id_prestamo'], estado)

    @staticmethod
    def _regularizar_por_reposicion(
        op: IRepositorioSancion, sancion: dict, detalle: dict, datos: Mapping[str, str],
        documento: str, nota: str, ahora: datetime,
    ) -> int:
        if datos.get('acepta_equivalencia') != '1':
            raise ValueError('Confirma que verificaste la equivalencia y el buen estado de la reposición.')
        bien = BienMaterial.desde_datos(datos, id_recurso=sancion['id_recurso'])
        nuevo = op.bienes.guardar_bien_material(bien)
        op.registrar_historial_estado(
            'BIEN_MATERIAL', nuevo, None, 'DISPONIBLE', documento,
            f'Reposición por sanción #{sancion["id_sancion"]}: {nota}'[:255],
        )
        op.registrar_historial_estado(
            'BIEN_MATERIAL', sancion['id_bien'], sancion['estado_bien'], sancion['estado_bien'],
            documento, f'Repuesto por bien #{nuevo}. {nota}'[:255],
        )
        if not detalle['fecha_devolucion']:
            op.prestamos.cerrar_detalle_por_reposicion(detalle['id_detalle'], ahora)
            detalle['fecha_regularizacion'] = ahora
        return nuevo

    @staticmethod
    def _regularizar_por_recuperacion(
        prestamos: IRepositorioPrestamo, detalle: dict, codigo: str | None,
        documento: str, nota: str, ahora: datetime,
    ) -> None:
        devolucion = Devolucion(id_detalle=detalle['id_detalle'], condicion=CondicionBien.BUENO, observacion=nota)
        devolucion.validar_bien_pendiente_de_devolucion(detalle)
        devolucion.validar_codigo_recibido(detalle, codigo)
        prestamos.registrar_devolucion(detalle, devolucion, ahora, documento)
        detalle['fecha_devolucion'] = ahora

    @staticmethod
    def _regularizar_por_reparacion(
        op: IRepositorioSancion, id_bien: int, detalle: dict, documento: str, nota: str,
    ) -> None:
        bienes = op.bienes
        bien = bienes.consultar_bien_material(id_bien, bloquear=True)
        validar_aceptacion_de_reparacion(detalle, bien)
        # El inventario puede haber liberado el bien al registrar su reparación.
        if bien['estado'] != 'DISPONIBLE':
            bienes.cambiar_estado_bien_material(id_bien, bien['estado'], 'DISPONIBLE', nota, documento)
