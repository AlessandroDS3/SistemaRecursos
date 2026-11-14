from dominio.compartido.validacion import NoEncontrado
from dominio.compartido.validacion import Conflicto, entero, texto
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_recursos.bien_material import (
    BienMaterial,
    ESTADOS_BIEN,
    IRepositorioBienMaterial,
    validar_cambio_estado,
)


class ServicioAplicacionBienMaterial:
    def __init__(self, repositorio: IRepositorioBienMaterial):
        self.repositorio = repositorio

    def consultar_bien_material(self, identificador):
        fila = self.repositorio.consultar_bien_material(entero(identificador))
        if fila is None:
            raise NoEncontrado('Bien inexistente.')
        return fila

    def consultar_bienes_materiales(self, filtros):
        estado = filtros.get('estado', '')
        if estado and estado not in ESTADOS_BIEN:
            raise ValueError('Estado de bien inválido.')
        return self.repositorio.consultar_bienes_materiales(
            dict(
                q=texto(filtros.get('q'), 'Búsqueda', 120),
                estado=estado,
                id_recurso=entero(filtros['id_recurso']) if filtros.get('id_recurso') else None,
            )
        )

    def guardar_bien_material(self, datos, actor, identificador=None):
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.consultar_cuenta_actor(entero(actor)), 'RECURSOS_GESTIONAR')
            actual = (
                operacion.consultar_bien_material(entero(identificador), bloquear=True)
                if identificador
                else None
            )
            if identificador and actual is None:
                raise NoEncontrado('Bien inexistente.')
            valores = {
                k: datos[k]
                for k in BienMaterial.__dataclass_fields__
                if k in datos and k not in ('id_bien', 'id_recurso')
            }
            valores['id_recurso'] = actual['id_recurso'] if actual else datos.get('id_recurso')
            valores.setdefault('codigo_inventario', None)
            bien = BienMaterial(**valores, id_bien=actual['id_bien'] if actual else None)
            return operacion.guardar_bien_material(bien)

    def cambiar_estado_bien_material(self, identificador, datos, actor):
        motivo = texto(datos.get('motivo'), 'Motivo', 255, True)
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(
                operacion.consultar_cuenta_actor(entero(actor)), 'RECURSOS_GESTIONAR'
            )
            bien = operacion.consultar_bien_material(entero(identificador), bloquear=True)
            if bien is None:
                raise NoEncontrado('Bien inexistente.')
            validar_cambio_estado(bien['estado'], datos.get('estado'), datos.get('estado_esperado'))
            if operacion.consultar_prestamo_pendiente(bien['id_bien']):
                raise Conflicto('El bien tiene una entrega pendiente.')
            operacion.cambiar_estado_bien_material(
                bien['id_bien'], bien['estado'], datos['estado'], motivo, cuenta['dni_persona']
            )

    def consultar_historial_bien_material(self, identificador):
        return self.repositorio.consultar_historial_estado('BIEN_MATERIAL', entero(identificador))

    def eliminar_bien_material(self, identificador, actor):
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.consultar_cuenta_actor(entero(actor)), 'RECURSOS_GESTIONAR')
            operacion.eliminar_bien_material(entero(identificador))
