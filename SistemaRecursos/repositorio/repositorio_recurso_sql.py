from dataclasses import asdict
from repositorio.base_sql import RepositorioSQL
from repositorio.repositorio_bien_material_sql import RepositorioBienMaterialSQL


class RepositorioRecursoSQL(RepositorioSQL):
    def consultar_recursos(self, filtros: dict) -> list[dict]:
        sql = '''SELECT r.*,c.nombre AS categoria,
            (SELECT COUNT(*) FROM bien_material b WHERE b.id_recurso=r.id_recurso) AS total,
            (SELECT COUNT(*) FROM bien_material b WHERE b.id_recurso=r.id_recurso AND b.estado='DISPONIBLE') AS disponibles
            FROM recurso r JOIN categoria_recurso c ON c.id_categoria=r.id_categoria WHERE 1=1'''
        parametros = []
        condiciones_bien = ['b.id_recurso=r.id_recurso']
        parametros_bien = []
        if filtros.get('estado'):
            condiciones_bien.append('b.estado=%s')
            parametros_bien.append(filtros['estado'])
        if filtros.get('solo_disponibles'):
            condiciones_bien.append("b.estado='DISPONIBLE'")
        subconsulta_bien = 'SELECT 1 FROM bien_material b WHERE ' + ' AND '.join(condiciones_bien)
        if filtros.get('q'):
            sql += (
                ' AND (r.nombre LIKE %s OR r.marca LIKE %s OR r.modelo LIKE %s OR EXISTS('
                + subconsulta_bien
                + ' AND b.codigo_inventario LIKE %s))'
            )
            busqueda = f"%{filtros['q']}%"
            parametros.extend([busqueda] * 3 + parametros_bien + [busqueda])
        if filtros.get('id_categoria'):
            sql += ' AND r.id_categoria=%s'
            parametros.append(filtros['id_categoria'])
        if filtros.get('id_recurso'):
            sql += ' AND r.id_recurso=%s'
            parametros.append(filtros['id_recurso'])
        if len(condiciones_bien) > 1:
            sql += ' AND EXISTS(' + subconsulta_bien + ')'
            parametros.extend(parametros_bien)
        return self.consultar_sql(sql + ' ORDER BY r.nombre,r.id_recurso', parametros)

    def consultar_recurso(self, identificador: int, bloquear: bool = False) -> dict | None:
        return self.consultar_sql(
            'SELECT * FROM recurso WHERE id_recurso=%s' + (' FOR UPDATE' if bloquear else ''),
            (identificador,),
            una=True,
        )

    def guardar_recurso(self, recurso) -> int:
        datos = asdict(recurso)
        identificador = datos.pop('id_recurso')
        if identificador is None:
            recurso.id_recurso = self.insertar('recurso', datos)
        else:
            self.ejecutar(
                'UPDATE recurso SET ' + ','.join(c + '=%s' for c in datos) + ' WHERE id_recurso=%s',
                (*datos.values(), identificador),
            )
        return recurso.id_recurso

    def guardar_bien_material(self, bien) -> int:
        return RepositorioBienMaterialSQL(self.conexion, self._cursor).guardar_bien_material(bien)

    def consultar_bienes_materiales(self, filtros: dict) -> list[dict]:
        return RepositorioBienMaterialSQL(self.conexion, self._cursor).consultar_bienes_materiales(
            filtros
        )

    def consultar_relaciones_recurso(self, identificador: int) -> dict:
        consultas = {
            'bienes': 'SELECT id_bien FROM bien_material WHERE id_recurso=%s LIMIT 1 FOR UPDATE',
            'reservas': 'SELECT id_reserva FROM reserva WHERE id_recurso=%s LIMIT 1 FOR UPDATE',
        }
        return {
            relacion: self.consultar_sql(sql, (identificador,), una=True) is not None
            for relacion, sql in consultas.items()
        }

    def eliminar_recurso(self, identificador: int) -> None:
        self.ejecutar('DELETE FROM recurso WHERE id_recurso=%s', (identificador,))

    def consultar_categorias(self) -> list[dict]:
        return self.consultar_sql('SELECT * FROM categoria_recurso ORDER BY nombre')

    def consultar_categoria(self, identificador: int, bloquear: bool = False) -> dict | None:
        return self.consultar_sql(
            'SELECT * FROM categoria_recurso WHERE id_categoria=%s'
            + (' FOR UPDATE' if bloquear else ''),
            (identificador,),
            una=True,
        )

    def consultar_relaciones_categoria(self, identificador: int) -> dict:
        consultas = {
            'recursos': 'SELECT id_recurso FROM recurso WHERE id_categoria=%s LIMIT 1 FOR UPDATE',
            'politicas': 'SELECT id_politica FROM politica_prestamo WHERE id_categoria=%s LIMIT 1 FOR UPDATE',
        }
        return {
            relacion: self.consultar_sql(sql, (identificador,), una=True) is not None
            for relacion, sql in consultas.items()
        }

    def guardar_categoria(
        self, nombre: str, descripcion: str, identificador: int | None = None
    ) -> int:
        if identificador is None:
            return self.insertar(
                'categoria_recurso', dict(nombre=nombre, descripcion=descripcion or None)
            )
        self.ejecutar(
            'UPDATE categoria_recurso SET nombre=%s,descripcion=%s WHERE id_categoria=%s',
            (nombre, descripcion or None, identificador),
        )
        return identificador

    def eliminar_categoria(self, identificador: int) -> None:
        self.ejecutar('DELETE FROM categoria_recurso WHERE id_categoria=%s', (identificador,))
