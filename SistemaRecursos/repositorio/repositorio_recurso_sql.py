from dataclasses import asdict
from repositorio.base_sql import RepositorioSQL
from repositorio.repositorio_bien_material_sql import RepositorioBienMaterialSQL


class RepositorioRecursoSQL(RepositorioSQL):
    def consultar_recursos(self, filtros):
        sql = '''SELECT r.*,c.nombre AS categoria,
            (SELECT COUNT(*) FROM bien_material b WHERE b.id_recurso=r.id_recurso) AS total,
            (SELECT COUNT(*) FROM bien_material b WHERE b.id_recurso=r.id_recurso AND b.estado='DISPONIBLE') AS disponibles
            FROM recurso r JOIN categoria_recurso c ON c.id_categoria=r.id_categoria WHERE 1=1'''
        parametros = []
        if filtros.get('q'):
            sql += ' AND (r.nombre LIKE %s OR r.marca LIKE %s OR r.modelo LIKE %s)'
            parametros += [f"%{filtros['q']}%"] * 3
        if filtros.get('id_categoria'):
            sql += ' AND r.id_categoria=%s'
            parametros.append(filtros['id_categoria'])
        if filtros.get('solo_disponibles'):
            sql += " AND EXISTS(SELECT 1 FROM bien_material b WHERE b.id_recurso=r.id_recurso AND b.estado='DISPONIBLE')"
        return self.consultar_sql(sql + ' ORDER BY r.nombre,r.id_recurso', parametros)

    def consultar_recurso(self, identificador):
        return self.consultar_sql(
            'SELECT * FROM recurso WHERE id_recurso=%s', (identificador,), una=True
        )

    def guardar_recurso(self, recurso):
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

    def guardar_bien_material(self, bien):
        return RepositorioBienMaterialSQL(self.conexion, self._cursor).guardar_bien_material(bien)

    def eliminar_recurso(self, identificador):
        self.ejecutar('DELETE FROM recurso WHERE id_recurso=%s', (identificador,))

    def consultar_categorias(self):
        return self.consultar_sql('SELECT * FROM categoria_recurso ORDER BY nombre')

    def guardar_categoria(self, nombre, descripcion, identificador=None):
        if identificador is None:
            return self.insertar(
                'categoria_recurso', dict(nombre=nombre, descripcion=descripcion or None)
            )
        self.ejecutar(
            'UPDATE categoria_recurso SET nombre=%s,descripcion=%s WHERE id_categoria=%s',
            (nombre, descripcion or None, identificador),
        )
        return identificador

    def eliminar_categoria(self, identificador):
        self.ejecutar('DELETE FROM categoria_recurso WHERE id_categoria=%s', (identificador,))
