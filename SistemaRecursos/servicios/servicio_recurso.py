from dominio.compartido.validacion import NoEncontrado
from dominio.compartido.validacion import entero, texto
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_recursos.recurso import IRepositorioRecurso, Recurso
from dominio.gestion_recursos.bien_material import BienMaterial


class ServicioAplicacionRecurso:
    def __init__(self, repositorio: IRepositorioRecurso):
        self.repositorio = repositorio

    def listar(self, filtros):
        return self.repositorio.listar(
            dict(
                q=texto(filtros.get('q'), 'Búsqueda', 120),
                id_categoria=(
                    entero(filtros['id_categoria']) if filtros.get('id_categoria') else None
                ),
                solo_disponibles=filtros.get('solo_disponibles') == '1',
            )
        )

    def consultar(self, identificador):
        fila = self.repositorio.consultar(entero(identificador))
        if fila is None:
            raise NoEncontrado('Recurso inexistente.')
        return fila

    def guardar(self, datos, actor, identificador=None):
        recurso = Recurso(
            **{
                k: datos.get(k)
                for k in ('nombre', 'id_categoria', 'marca', 'modelo', 'descripcion')
            },
            id_recurso=entero(identificador) if identificador else None,
        )
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.cuenta_actor(entero(actor)), 'RECURSOS_GESTIONAR')
            if recurso.id_recurso is not None and operacion.consultar(recurso.id_recurso) is None:
                raise NoEncontrado('Recurso inexistente.')
            if not any(c['id_categoria'] == recurso.id_categoria for c in operacion.categorias()):
                raise ValueError('Categoría inexistente.')
            nuevo_id = operacion.guardar(recurso)
            if identificador is None and datos.get('codigo_inventario', '').strip():
                bien = BienMaterial(
                    id_recurso=nuevo_id,
                    **{
                        k: datos[k]
                        for k in (
                            'codigo_inventario',
                            'numero_serie',
                            'fecha_adquisicion',
                            'ubicacion',
                            'descripcion_bien',
                        )
                        if k in datos
                    },
                )
                operacion.guardar_bien(bien)
        return nuevo_id

    def eliminar(self, identificador, actor):
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.cuenta_actor(entero(actor)), 'RECURSOS_GESTIONAR')
            operacion.eliminar(entero(identificador))

    def categorias(self):
        return self.repositorio.categorias()

    def guardar_categoria(self, datos, actor, identificador=None):
        nombre = texto(datos.get('nombre'), 'Nombre de categoría', 80, True)
        descripcion = texto(datos.get('descripcion'), 'Descripción', 255)
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.cuenta_actor(entero(actor)), 'RECURSOS_GESTIONAR')
            return operacion.guardar_categoria(
                nombre, descripcion, entero(identificador) if identificador else None
            )

    def eliminar_categoria(self, identificador, actor):
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.cuenta_actor(entero(actor)), 'RECURSOS_GESTIONAR')
            operacion.eliminar_categoria(entero(identificador))
