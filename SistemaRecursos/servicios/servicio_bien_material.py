from dominio.compartido.validacion import NoEncontrado
from dominio.compartido.validacion import Conflicto, comprobar_version, entero, texto
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_recursos.bien_material import (
    BienMaterial,
    IRepositorioBienMaterial,
    validar_cambio_estado,
    validar_filtros_inventario,
    version_bien_material,
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

    def guardar_bien_material(
        self, datos: dict, actor: int, identificador: int | None = None
    ) -> int:
        identificador = entero(identificador) if identificador is not None else None
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
            if operacion.consultar_prestamo_pendiente(bien['id_bien']):
                raise Conflicto('El bien tiene una entrega pendiente.')
            operacion.cambiar_estado_bien_material(
                bien['id_bien'], bien['estado'], datos['estado'], motivo, cuenta['dni_persona']
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
