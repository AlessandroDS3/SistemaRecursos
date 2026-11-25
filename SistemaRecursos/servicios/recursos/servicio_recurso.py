from dominio.compartido.validacion import Conflicto, NoEncontrado, comprobar_version, entero, texto
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_recursos.contratos_recursos import IRepositorioRecurso
from dominio.gestion_recursos.recurso import (
    CAMPOS_RECURSO,
    Recurso,
    version_categoria,
    version_recurso,
)
from dominio.gestion_recursos.bien_material import BienMaterial, validar_filtros_inventario


class ServicioAplicacionRecurso:
    def __init__(self, repositorio: IRepositorioRecurso):
        self.repositorio = repositorio

    def consultar_recursos(self, filtros) -> list[dict]:
        return self.repositorio.consultar_recursos(validar_filtros_inventario(filtros))

    def consultar_administracion_recursos(self, filtros) -> dict:
        filtros = validar_filtros_inventario(filtros)
        recursos = self.repositorio.consultar_recursos(filtros, contar_bienes=False)
        bienes = self.repositorio.consultar_bienes_materiales(filtros)
        por_recurso: dict[int, list[dict]] = {}
        for bien in bienes:
            por_recurso.setdefault(bien['id_recurso'], []).append(bien)
        grupos = [
            dict(recurso=recurso, bienes=por_recurso.get(recurso['id_recurso'], []))
            for recurso in recursos
        ]
        visibles = [bien for grupo in grupos for bien in grupo['bienes']]
        return dict(
            grupos=grupos,
            categorias=self.consultar_categorias(),
            resumen=dict(
                recursos=len(grupos),
                bienes=len(visibles),
                disponibles=sum(bien['estado'] == 'DISPONIBLE' for bien in visibles),
            ),
        )

    def consultar_disponibilidad(self) -> int:
        return self.repositorio.consultar_disponibilidad()

    def consultar_recurso(self, identificador: int) -> dict:
        fila = self.repositorio.consultar_recurso(entero(identificador))
        if fila is None:
            raise NoEncontrado('Recurso inexistente.')
        return dict(fila, version=version_recurso(fila))

    def registrar_recurso(self, datos: dict, actor: int) -> int:
        return self._guardar_recurso(datos, actor)

    def actualizar_recurso(self, identificador: int, datos: dict, actor: int) -> int:
        return self._guardar_recurso(datos, actor, entero(identificador))

    def _guardar_recurso(self, datos: dict, actor: int, identificador: int | None = None) -> int:
        actor = entero(actor)
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.consultar_cuenta_actor(actor), 'RECURSOS_GESTIONAR')
            actual = None
            if identificador is not None:
                actual = operacion.consultar_recurso(identificador, bloquear=True)
                if actual is None:
                    raise NoEncontrado('Recurso inexistente.')
                comprobar_version(datos.get('version'), version_recurso(actual))
            valores = dict(actual or {})
            valores.update(datos)
            campos_recurso: dict = {campo: valores.get(campo) for campo in CAMPOS_RECURSO}
            recurso = Recurso(**campos_recurso, id_recurso=identificador)
            if operacion.consultar_categoria(recurso.id_categoria) is None:
                raise ValueError('Categoría inexistente.')
            if actual and recurso.id_categoria != actual['id_categoria'] and (
                operacion.existe_prestamo_pendiente_del_recurso(identificador)
            ):
                raise Conflicto('El recurso conserva su categoría mientras tenga bienes pendientes de devolución o regularización.')
            id_recurso_guardado = operacion.guardar_recurso(recurso)
            if identificador is None and texto(
                datos.get('codigo_inventario'), 'Código de inventario', 40
            ):
                bien = BienMaterial.desde_datos(datos, id_recurso=id_recurso_guardado)
                operacion.guardar_bien_material(bien)
        return id_recurso_guardado

    def eliminar_recurso(self, identificador: int, actor: int) -> None:
        identificador, actor = entero(identificador), entero(actor)
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.consultar_cuenta_actor(actor), 'RECURSOS_GESTIONAR')
            if operacion.consultar_recurso(identificador, bloquear=True) is None:
                raise NoEncontrado('Recurso inexistente.')
            relaciones = operacion.consultar_relaciones_recurso(identificador)
            if relaciones['bienes']:
                raise Conflicto('No puedes eliminar el recurso porque tiene bienes registrados.')
            if relaciones['reservas']:
                raise Conflicto(
                    'No puedes eliminar el recurso porque tiene solicitudes o reservas.'
                )
            operacion.eliminar_recurso(identificador)

    def consultar_categorias(self) -> list[dict]:
        return [
            dict(fila, version=version_categoria(fila))
            for fila in self.repositorio.consultar_categorias()
        ]

    def consultar_categoria(self, identificador: int) -> dict:
        fila = self.repositorio.consultar_categoria(entero(identificador))
        if fila is None:
            raise NoEncontrado('Categoría inexistente.')
        return dict(fila, version=version_categoria(fila))

    def guardar_categoria(self, datos: dict, actor: int, identificador: int | None = None) -> int:
        actor = entero(actor)
        identificador = entero(identificador) if identificador is not None else None
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.consultar_cuenta_actor(actor), 'RECURSOS_GESTIONAR')
            actual = None
            if identificador is not None:
                actual = operacion.consultar_categoria(identificador, bloquear=True)
                if actual is None:
                    raise NoEncontrado('Categoría inexistente.')
                comprobar_version(datos.get('version'), version_categoria(actual))
            valores = dict(actual or {})
            valores.update(datos)
            nombre = texto(valores.get('nombre'), 'Nombre de categoría', 80, True)
            descripcion = texto(valores.get('descripcion'), 'Descripción', 255)
            return operacion.guardar_categoria(nombre, descripcion, identificador)

    def eliminar_categoria(self, identificador: int, actor: int) -> None:
        identificador, actor = entero(identificador), entero(actor)
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.consultar_cuenta_actor(actor), 'RECURSOS_GESTIONAR')
            if operacion.consultar_categoria(identificador, bloquear=True) is None:
                raise NoEncontrado('Categoría inexistente.')
            relaciones = operacion.consultar_relaciones_categoria(identificador)
            if relaciones['recursos']:
                raise Conflicto(
                    'No puedes eliminar la categoría porque tiene recursos registrados.'
                )
            if relaciones['politicas']:
                raise Conflicto(
                    'No puedes eliminar la categoría porque tiene políticas de préstamo.'
                )
            operacion.eliminar_categoria(identificador)
