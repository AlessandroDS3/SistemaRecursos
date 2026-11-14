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

    def consultar(self, identificador):
        fila = self.repositorio.consultar(entero(identificador))
        if fila is None:
            raise NoEncontrado('Bien inexistente.')
        return fila

    def listar(self, filtros):
        estado = filtros.get('estado', '')
        if estado and estado not in ESTADOS_BIEN:
            raise ValueError('Estado de bien inválido.')
        return self.repositorio.listar(
            dict(
                q=texto(filtros.get('q'), 'Búsqueda', 120),
                estado=estado,
                id_recurso=entero(filtros['id_recurso']) if filtros.get('id_recurso') else None,
            )
        )

    def guardar(self, datos, actor, identificador=None):
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.cuenta_actor(entero(actor)), 'RECURSOS_GESTIONAR')
            actual = (
                operacion.consultar(entero(identificador), bloquear=True) if identificador else None
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
            return operacion.guardar(bien)

    def cambiar_estado(self, identificador, datos, actor):
        motivo = texto(datos.get('motivo'), 'Motivo', 255, True)
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(operacion.cuenta_actor(entero(actor)), 'RECURSOS_GESTIONAR')
            bien = operacion.consultar(entero(identificador), bloquear=True)
            if bien is None:
                raise NoEncontrado('Bien inexistente.')
            validar_cambio_estado(bien['estado'], datos.get('estado'), datos.get('estado_esperado'))
            if operacion.prestamo_pendiente(bien['id_bien']):
                raise Conflicto('El bien tiene una entrega pendiente.')
            operacion.cambiar_estado(
                bien['id_bien'], bien['estado'], datos['estado'], motivo, cuenta['dni_persona']
            )

    def historial(self, identificador):
        return self.repositorio.consultar_historial('BIEN_MATERIAL', entero(identificador))

    def eliminar(self, identificador, actor):
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.cuenta_actor(entero(actor)), 'RECURSOS_GESTIONAR')
            operacion.eliminar(entero(identificador))
