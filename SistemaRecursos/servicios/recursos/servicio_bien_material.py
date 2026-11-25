from dominio.compartido.validacion import NoEncontrado
from dominio.compartido.validacion import Conflicto, comprobar_version, entero, texto
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_recursos.bien_material import (
    BienMaterial,
    ESTADOS_MANUALES,
    validar_cambio_estado,
    validar_filtros_inventario,
    version_bien_material,
)
from dominio.gestion_recursos.contratos_recursos import IRepositorioBienMaterial
from dominio.gestion_recursos.mantenimiento import (
    AperturaMantenimiento,
    CierreMantenimiento,
    validar_apertura,
)


class ServicioAplicacionBienMaterial:
    def __init__(self, repositorio: IRepositorioBienMaterial):
        self.repositorio = repositorio

    def consultar_bien_material(self, identificador: int) -> dict:
        fila = self.repositorio.consultar_bien_material(entero(identificador))
        if fila is None:
            raise NoEncontrado('Bien inexistente.')
        return dict(fila, version=version_bien_material(fila))

    def consultar_bienes_materiales(self, filtros) -> list[dict]:
        return self.repositorio.consultar_bienes_materiales(validar_filtros_inventario(filtros))

    def consultar_detalle_bien_material(self, identificador: int) -> dict:
        bien = self.consultar_bien_material(identificador)
        pendiente = self.repositorio.consultar_prestamo_pendiente(bien['id_bien'], bloquear=False)
        relaciones = self.repositorio.consultar_relaciones_bien_material(
            bien['id_bien'], bloquear=False
        )
        abierto = self.repositorio.consultar_mantenimiento_abierto(bien['id_bien'])
        return dict(
            bien=bien,
            historial=self.consultar_historial_bien_material(bien['id_bien']),
            prestamo_pendiente=pendiente['id_prestamo'] if pendiente else None,
            danio_pendiente=self.repositorio.consultar_danio_pendiente(bien['id_bien']),
            mantenimiento_abierto=abierto,
            mantenimientos=self.repositorio.consultar_mantenimientos(bien['id_bien']),
            permite_mantenimiento=not abierto
            and not pendiente
            and bien['estado'] in ('DISPONIBLE', 'DANADO', 'MANTENIMIENTO'),
            permite_cambio_manual=bien['estado'] in ESTADOS_MANUALES
            and not pendiente
            and not abierto,
            permite_eliminar=bien['estado'] == 'DISPONIBLE' and not any(relaciones.values()),
        )

    def consultar_bien_disponible_para_prestamo(self, identificador: int) -> dict:
        bien = self.consultar_bien_material(identificador)
        if bien['estado'] != 'DISPONIBLE':
            raise Conflicto(
                'El bien ya no está disponible para préstamo. Selecciona otro ejemplar.'
            )
        return bien

    def registrar_bien_material(self, datos: dict, actor: int) -> int:
        return self._guardar_bien_material(datos, actor)

    def actualizar_bien_material(self, identificador: int, datos: dict, actor: int) -> int:
        return self._guardar_bien_material(datos, actor, entero(identificador))

    def _guardar_bien_material(
        self, datos: dict, actor: int, identificador: int | None = None
    ) -> int:
        actor = entero(actor)
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.consultar_cuenta_actor(actor), 'RECURSOS_GESTIONAR')
            actual = (
                operacion.consultar_bien_material(identificador, bloquear=True)
                if identificador is not None
                else None
            )
            if identificador is not None and actual is None:
                raise NoEncontrado('Bien inexistente.')
            if actual is not None:
                comprobar_version(datos.get('version'), version_bien_material(actual))
            valores = dict(actual or {})
            valores.update(datos)
            id_recurso = (
                actual['id_recurso'] if actual else entero(datos.get('id_recurso'), 'Recurso')
            )
            bien = BienMaterial.desde_datos(
                valores,
                id_recurso=id_recurso,
                id_bien=identificador,
            )
            if actual and bien.codigo_inventario != actual['codigo_inventario'] and (
                actual['estado'] in ('PRESTADO', 'RESERVADO')
                or operacion.consultar_prestamo_pendiente(identificador)
            ):
                raise Conflicto('El código de inventario se conserva mientras el bien tenga un préstamo o una reserva.')
            return operacion.guardar_bien_material(bien)

    def cambiar_estado_bien_material(self, identificador: int, datos: dict, actor: int) -> None:
        identificador, actor = entero(identificador), entero(actor)
        motivo = texto(datos.get('motivo'), 'Motivo', 255, True)
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(operacion.consultar_cuenta_actor(actor), 'RECURSOS_GESTIONAR')
            bien = operacion.consultar_bien_material(identificador, bloquear=True)
            if bien is None:
                raise NoEncontrado('Bien inexistente.')
            validar_cambio_estado(bien['estado'], datos.get('estado'), datos.get('estado_esperado'))
            if datos['estado'] == 'MANTENIMIENTO':
                raise ValueError('Para enviar el bien a mantenimiento usa Abrir mantenimiento.')
            if operacion.consultar_mantenimiento_abierto(bien['id_bien'], bloquear=True):
                raise Conflicto('Cierra el mantenimiento abierto para cambiar el estado del bien.')
            if operacion.consultar_prestamo_pendiente(bien['id_bien']):
                raise Conflicto('El bien tiene una entrega pendiente.')
            if datos['estado'] == 'DISPONIBLE' and operacion.consultar_danio_pendiente(
                bien['id_bien'], bloquear=True
            ):
                raise Conflicto('Acepta la reparación en la ficha de la sanción.')
            operacion.cambiar_estado_bien_material(
                bien['id_bien'], bien['estado'], datos['estado'], motivo, cuenta['dni_persona']
            )

    def abrir_mantenimiento(self, identificador: int, datos: dict, actor: int) -> int:
        identificador, actor = entero(identificador), entero(actor)
        apertura = AperturaMantenimiento(
            tipo=datos.get('tipo'),
            motivo=datos.get('motivo'),
            fecha_fin_estimada=datos.get('fecha_fin_estimada'),
        )
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(operacion.consultar_cuenta_actor(actor), 'RECURSOS_GESTIONAR')
            bien = operacion.consultar_bien_material(identificador, bloquear=True)
            if bien is None:
                raise NoEncontrado('Bien inexistente.')
            validar_apertura(
                bien['estado'],
                operacion.consultar_mantenimiento_abierto(identificador, bloquear=True),
                operacion.consultar_prestamo_pendiente(identificador),
            )
            id_mantenimiento = operacion.abrir_mantenimiento(
                identificador, apertura, bien['estado'], cuenta['dni_persona']
            )
            observacion = f'Mantenimiento #{id_mantenimiento} abierto: {apertura.motivo}'[:255]
            if bien['estado'] != 'MANTENIMIENTO':
                operacion.cambiar_estado_bien_material(
                    identificador, bien['estado'], 'MANTENIMIENTO', observacion,
                    cuenta['dni_persona'],
                )
            else:
                operacion.registrar_historial_estado(
                    'BIEN_MATERIAL', identificador, bien['estado'], bien['estado'],
                    cuenta['dni_persona'], observacion,
                )
            return id_mantenimiento

    def cerrar_mantenimiento(self, identificador: int, datos: dict, actor: int) -> None:
        identificador, actor = entero(identificador), entero(actor)
        cierre = CierreMantenimiento(
            resultado=datos.get('resultado'), observacion=datos.get('observacion')
        )
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(operacion.consultar_cuenta_actor(actor), 'RECURSOS_GESTIONAR')
            bien = operacion.consultar_bien_material(identificador, bloquear=True)
            if bien is None:
                raise NoEncontrado('Bien inexistente.')
            abierto = operacion.consultar_mantenimiento_abierto(identificador, bloquear=True)
            if abierto is None:
                raise Conflicto('El bien no tiene un mantenimiento abierto.')
            if cierre.resultado == 'DISPONIBLE' and operacion.consultar_danio_pendiente(
                identificador, bloquear=True
            ):
                raise Conflicto('Acepta la reparación en la ficha de la sanción antes de habilitarlo.')
            operacion.cerrar_mantenimiento(
                abierto['id_mantenimiento'], cierre, cuenta['dni_persona']
            )
            operacion.cambiar_estado_bien_material(
                identificador,
                bien['estado'],
                cierre.resultado,
                f"Mantenimiento #{abierto['id_mantenimiento']} cerrado: {cierre.observacion}"[:255],
                cuenta['dni_persona'],
            )

    def consultar_historial_bien_material(self, identificador: int) -> list[dict]:
        return self.repositorio.consultar_historial_estado('BIEN_MATERIAL', entero(identificador))

    def eliminar_bien_material(self, identificador: int, actor: int) -> None:
        identificador, actor = entero(identificador), entero(actor)
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.consultar_cuenta_actor(actor), 'RECURSOS_GESTIONAR')
            if operacion.consultar_bien_material(identificador, bloquear=True) is None:
                raise NoEncontrado('Bien inexistente.')
            relaciones = operacion.consultar_relaciones_bien_material(identificador)
            if relaciones['prestamos']:
                raise Conflicto('No puedes eliminar el bien porque tiene préstamos registrados.')
            if relaciones['reservas']:
                raise Conflicto('No puedes eliminar el bien porque tiene solicitudes o reservas.')
            if relaciones['historial']:
                raise Conflicto('No puedes eliminar el bien porque tiene historial de estados.')
            operacion.eliminar_bien_material(identificador)
