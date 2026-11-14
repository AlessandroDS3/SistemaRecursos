from dataclasses import asdict
from repositorio.base_sql import RepositorioSQL


class RepositorioBienMaterialSQL(RepositorioSQL):
    def consultar_bien_material(self, identificador, bloquear=False):
        return self.consultar_sql(
            '''SELECT b.*,r.nombre AS recurso,c.nombre AS categoria
            FROM bien_material b JOIN recurso r ON r.id_recurso=b.id_recurso
            JOIN categoria_recurso c ON c.id_categoria=r.id_categoria WHERE b.id_bien=%s'''
            + (' FOR UPDATE' if bloquear else ''),
            (identificador,),
            una=True,
        )

    def consultar_bienes_materiales(self, filtros):
        condiciones, parametros = [], []
        for campo in ('id_recurso', 'estado'):
            if filtros.get(campo):
                condiciones.append('b.' + campo + '=%s')
                parametros.append(filtros[campo])
        if filtros.get('q'):
            condiciones.append('(b.codigo_inventario LIKE %s OR r.nombre LIKE %s)')
            parametros.extend([f"%{filtros['q']}%"] * 2)
        sql = '''SELECT b.*,r.nombre AS recurso FROM bien_material b
            JOIN recurso r ON r.id_recurso=b.id_recurso'''
        if condiciones:
            sql += ' WHERE ' + ' AND '.join(condiciones)
        return self.consultar_sql(sql + ' ORDER BY r.nombre,b.codigo_inventario', parametros)

    def guardar_bien_material(self, bien):
        datos = asdict(bien)
        identificador = datos.pop('id_bien')
        if identificador is None:
            bien.id_bien = self.insertar('bien_material', datos)
        else:
            self.ejecutar(
                'UPDATE bien_material SET '
                + ','.join(c + '=%s' for c in datos)
                + ' WHERE id_bien=%s',
                (*datos.values(), identificador),
            )
        return bien.id_bien

    def cambiar_estado_bien_material(self, identificador, anterior, nuevo, motivo, actor):
        self.ejecutar('UPDATE bien_material SET estado=%s WHERE id_bien=%s', (nuevo, identificador))
        self.registrar_historial_estado(
            'BIEN_MATERIAL', identificador, anterior, nuevo, actor, motivo
        )

    def consultar_prestamo_pendiente(self, identificador):
        return self.consultar_sql(
            '''SELECT id_prestamo FROM detalle_prestamo
            WHERE id_bien=%s AND fecha_devolucion IS NULL LIMIT 1 FOR UPDATE''',
            (identificador,),
            una=True,
        )

    def eliminar_bien_material(self, identificador):
        self.ejecutar('DELETE FROM bien_material WHERE id_bien=%s', (identificador,))
