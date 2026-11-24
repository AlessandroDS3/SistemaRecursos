"""Casos de uso de sanciones; coordina dominio y repositorios en una transacción."""

from dominio.compartido.validacion import Conflicto, NoEncontrado, comprobar_version, entero, texto, version
from dominio.gestion_control.contratos_control import IRepositorioSancion
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_recursos.bien_material import BienMaterial
from dominio.gestion_prestamos.contratos_prestamos import IRepositorioPrestamo
from dominio.gestion_prestamos.devolucion import Devolucion
from dominio.gestion_prestamos.prestamo import estado_prestamo
from dominio.gestion_control.sancion import (
    ConfiguracionSanciones, ESTADOS_SANCION, alertas_revision,
    exigir_administrador, validar_levantamiento, validar_regularizacion,
    validar_reparacion, validar_verificacion,
)

from servicios.control.operaciones_sancion import (
    aceptar_regularizacion, cerrar_sancion, cumplir_sancion, registrar_falta,
    registrar_sancion_por_retraso,
)


class ServicioAplicacionSancion:
    def __init__(self, repositorio: IRepositorioSancion):
        self.repositorio = repositorio

    def consultar_configuracion_sanciones(self):
        datos = ConfiguracionSanciones.desde_datos(self.repositorio.consultar_configuracion() or {}).datos()
        return datos, version(datos)

    def guardar_configuracion_sanciones(self, datos, version_recibida, actor):
        campos = ConfiguracionSanciones.__dataclass_fields__
        if any(k not in datos for k in campos):
            raise ValueError('Completa los tres plazos de sanciones.')
        nuevos = ConfiguracionSanciones.desde_datos(datos).datos()
        with self.repositorio.transaccion() as op:
            cuenta = exigir_permiso(op.consultar_cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR')
            exigir_administrador(cuenta)
            actual = op.consultar_configuracion(bloquear=True)
            if actual is None:
                raise Conflicto('Configura primero el horario general en Políticas.')
            comprobar_version(version_recibida, version(ConfiguracionSanciones.desde_datos(actual).datos()))
            op.guardar_configuracion(nuevos)
            op.registrar_historial_estado(
                'CONFIGURACION_SANCIONES', 1, None, 'ACTUALIZADA', cuenta['dni_persona'],
                f'Leve: {nuevos["dias_leve"]} días; grave: {nuevos["dias_grave"]} días; '
                f'espera adicional: {nuevos["dias_espera_perdida"]} días.',
            )

    def procesar_sanciones_por_vencimiento(self):
        creadas = 0
        for fila in self.repositorio.consultar_detalles_vencidos():
            with self.repositorio.transaccion() as op:
                prestamo = op.prestamos.consultar_prestamo_para_actualizar(fila['id_prestamo'])
                if prestamo is None:
                    continue
                detalle = next(
                    (d for d in prestamo['detalles'] if d['id_detalle'] == fila['id_detalle']), None,
                )
                if detalle and not detalle['fecha_devolucion'] and not detalle['fecha_regularizacion']:
                    creadas += registrar_sancion_por_retraso(op, detalle, op.consultar_fecha_actual())
        for fila in self.repositorio.consultar_sanciones_a_revisar():
            with self.repositorio.transaccion() as op:
                sancion, _ = self._bloquear_caso(op, fila['id_sancion'])
                cumplir_sancion(op, sancion, op.consultar_fecha_actual())
        return creadas

    def consultar_sanciones(self, filtros=None):
        filtros = filtros or {}
        estado = filtros.get('estado', '')
        if estado not in ('', *ESTADOS_SANCION):
            raise ValueError('Estado de sanción inválido.')
        ahora = self.repositorio.consultar_fecha_actual()
        return [dict(s, **alertas_revision(s, ahora)) for s in self.repositorio.consultar_sanciones(
            dict(estado=estado, q=texto(filtros.get('q'), 'Búsqueda', 120))
        )]

    def consultar_sancion(self, identificador):
        sancion = self.repositorio.consultar_detalle_sancion(entero(identificador))
        if sancion is None:
            raise NoEncontrado('Sanción inexistente.')
        sancion.update(alertas_revision(sancion, self.repositorio.consultar_fecha_actual()))
        sancion['historial'] = self.repositorio.consultar_historial_estado('SANCION', sancion['id_sancion'])
        return sancion

    @staticmethod
    def _bloquear_caso(op, identificador):
        inicial = op.consultar_sancion(identificador)
        if inicial is None:
            raise NoEncontrado('Sanción inexistente.')
        prestamo = op.prestamos.consultar_prestamo_para_actualizar(inicial['id_prestamo'])
        return op.consultar_sancion(identificador, bloquear=True), prestamo

    def levantar_sancion(self, identificador, justificacion, actor):
        with self.repositorio.transaccion() as op:
            cuenta = exigir_permiso(op.consultar_cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR')
            sancion, _ = self._bloquear_caso(op, entero(identificador))
            ahora = op.consultar_fecha_actual()
            nota = validar_levantamiento(sancion, justificacion, ahora, cuenta)
            cerrar_sancion(op, sancion, 'LEVANTADA', nota, cuenta['dni_persona'], ahora)

    @staticmethod
    def _evaluar_detalle(op: IRepositorioSancion, prestamo, detalle, datos, cuenta):
        prestamos: IRepositorioPrestamo = op.prestamos
        causa = datos.get('causa')
        politica = None
        if causa in ('SALIDA_NO_AUTORIZADA', 'CUSTODIA'):
            politica = prestamos.consultar_politica_aplicada(detalle['id_politica'])
        sancion = registrar_falta(
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
            cuenta = exigir_permiso(op.consultar_cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR')
            sancion, prestamo = self._bloquear_caso(op, entero(identificador))
            detalle = next(d for d in prestamo['detalles'] if d['id_detalle'] == sancion['id_detalle'])
            self._evaluar_detalle(op, prestamo, detalle, datos, cuenta)

    def registrar_sancion_por_detalle_prestamo(self, prestamo_id, detalle_id, datos, actor):
        with self.repositorio.transaccion() as op:
            cuenta = exigir_permiso(op.consultar_cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR')
            prestamo = op.prestamos.consultar_prestamo_para_actualizar(entero(prestamo_id))
            if prestamo is None:
                raise NoEncontrado('Préstamo inexistente.')
            detalle_id = entero(detalle_id)
            detalle = next((d for d in prestamo['detalles'] if d['id_detalle'] == detalle_id), None)
            if detalle is None:
                raise NoEncontrado('El bien no pertenece al préstamo.')
            return self._evaluar_detalle(op, prestamo, detalle, datos, cuenta)

    def regularizar_sancion(self, identificador, datos, actor):
        with self.repositorio.transaccion() as op:
            cuenta = exigir_permiso(op.consultar_cuenta_actor(entero(actor)), 'PRESTAMOS_GESTIONAR')
            sancion, prestamo = self._bloquear_caso(op, entero(identificador))
            tipo = datos.get('tipo_regularizacion')
            nota = validar_regularizacion(sancion, tipo, datos.get('observacion'))
            detalle = next(d for d in prestamo['detalles'] if d['id_detalle'] == sancion['id_detalle'])
            ahora, nuevo = op.consultar_fecha_actual(), None
            if tipo == 'REPOSICION':
                if datos.get('acepta_equivalencia') != '1':
                    raise ValueError('Confirma que verificaste la equivalencia y el buen estado de la reposición.')
                bien = BienMaterial.desde_datos(datos, id_recurso=sancion['id_recurso'])
                nuevo = op.bienes.guardar_bien_material(bien)
                op.registrar_historial_estado('BIEN_MATERIAL', nuevo, None, 'DISPONIBLE', cuenta['dni_persona'],
                                             f'Reposición por sanción #{sancion["id_sancion"]}: {nota}'[:255])
                op.registrar_historial_estado('BIEN_MATERIAL', sancion['id_bien'], sancion['estado_bien'],
                                             sancion['estado_bien'], cuenta['dni_persona'],
                                             f'Repuesto por bien #{nuevo}. {nota}'[:255])
                if not detalle['fecha_devolucion']:
                    op.prestamos.cerrar_detalle_por_reposicion(detalle['id_detalle'], ahora)
                    detalle['fecha_regularizacion'] = ahora
            elif tipo == 'RECUPERACION':
                devolucion = Devolucion(id_detalle=detalle['id_detalle'], condicion='BUENO', observacion=nota)
                devolucion.validar(detalle)
                op.prestamos.registrar_devolucion(detalle, devolucion, ahora, cuenta['dni_persona'])
                detalle['fecha_devolucion'] = ahora
            elif tipo == 'REPARACION':
                bien = op.bienes.consultar_bien_material(sancion['id_bien'], bloquear=True)
                validar_reparacion(detalle, bien)
                # Las reparaciones registradas antes desde inventario ya liberaron el bien.
                if bien['estado'] != 'DISPONIBLE':
                    op.bienes.cambiar_estado_bien_material(
                        sancion['id_bien'], bien['estado'], 'DISPONIBLE', nota, cuenta['dni_persona']
                    )
            else:
                validar_verificacion(detalle)
            aceptar_regularizacion(op, sancion, tipo, nota, cuenta['dni_persona'], ahora, nuevo)
            op.prestamos.actualizar_estado_prestamo(
                prestamo, estado_prestamo(prestamo['detalles'], ahora), cuenta['dni_persona'],
                f'Regularización {tipo} del detalle #{detalle["id_detalle"]}.',
            )
