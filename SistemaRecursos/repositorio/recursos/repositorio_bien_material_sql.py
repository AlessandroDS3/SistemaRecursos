from dataclasses import asdict
from repositorio.base_datos.base_sql import RepositorioSQL


class RepositorioBienMaterialSQL(RepositorioSQL):
    def consultar_bien_material(self, identificador: int, bloquear: bool = False) -> dict | None:
        return self.consultar_sql(
            '''SELECT b.*,r.nombre AS recurso,r.id_categoria,c.nombre AS categoria
            FROM bien_material b JOIN recurso r ON r.id_recurso=b.id_recurso
            JOIN categoria_recurso c ON c.id_categoria=r.id_categoria WHERE b.id_bien=%s'''
            + (' FOR UPDATE' if bloquear else ''),
            (identificador,),
            una=True,
        )

    def consultar_bienes_materiales(self, filtros: dict) -> list[dict]:
        condiciones, parametros = [], []
        for campo in ('id_recurso', 'estado'):
            if filtros.get(campo):
                condiciones.append('b.' + campo + '=%s')
                parametros.append(filtros[campo])
        if filtros.get('id_categoria'):
            condiciones.append('r.id_categoria=%s')
            parametros.append(filtros['id_categoria'])
        if filtros.get('solo_disponibles'):
            condiciones.append("b.estado='DISPONIBLE'")
        if filtros.get('q'):
            condiciones.append(
                '(b.codigo_inventario LIKE %s OR r.nombre LIKE %s OR r.marca LIKE %s OR r.modelo LIKE %s)'
            )
            parametros.extend([f"%{filtros['q']}%"] * 4)
        sql = '''SELECT b.*,r.nombre AS recurso,r.id_categoria FROM bien_material b
            JOIN recurso r ON r.id_recurso=b.id_recurso'''
        if condiciones:
            sql += ' WHERE ' + ' AND '.join(condiciones)
        return self.consultar_sql(sql + ' ORDER BY r.nombre,b.codigo_inventario', parametros)

    def guardar_bien_material(self, bien) -> int:
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

    def cambiar_estado_bien_material(self, identificador, anterior, nuevo, motivo, actor) -> None:
        self.ejecutar('UPDATE bien_material SET estado=%s WHERE id_bien=%s', (nuevo, identificador))
        self.registrar_historial_estado(
            'BIEN_MATERIAL', identificador, anterior, nuevo, actor, motivo
        )

    def consultar_prestamo_pendiente(self, identificador: int, bloquear=True) -> dict | None:
        return self.consultar_sql(
            '''SELECT id_prestamo FROM detalle_prestamo
            WHERE id_bien=%s AND fecha_devolucion IS NULL AND fecha_regularizacion IS NULL LIMIT 1'''
            + (' FOR UPDATE' if bloquear else ''),
            (identificador,),
            una=True,
        )

    def consultar_relaciones_bien_material(self, identificador: int, bloquear=True) -> dict:
        consultas = {
            'prestamos': 'SELECT id_detalle FROM detalle_prestamo WHERE id_bien=%s LIMIT 1 FOR UPDATE',
            'reservas': 'SELECT id_reserva FROM reserva WHERE id_bien=%s LIMIT 1 FOR UPDATE',
            'historial': """SELECT id_historial_estado FROM historial_estado
                WHERE entidad='BIEN_MATERIAL' AND id_entidad=%s LIMIT 1 FOR UPDATE""",
        }
        return {
            relacion: self.consultar_sql(
                sql if bloquear else sql.removesuffix(' FOR UPDATE'), (identificador,), una=True
            )
            is not None
            for relacion, sql in consultas.items()
        }

    def consultar_danio_pendiente(self, identificador: int, bloquear=False) -> dict | None:
        return self.consultar_sql(
            """SELECT s.id_sancion FROM detalle_prestamo d
            JOIN incidencia i ON i.id_detalle=d.id_detalle
            JOIN sancion s ON s.id_incidencia_ref=i.id_incidencia
            WHERE d.id_bien=%s AND i.tipo='DANIO'
                AND s.estado='ACTIVA' AND s.fecha_regularizacion IS NULL
            ORDER BY s.id_sancion DESC LIMIT 1"""
            + (' FOR UPDATE OF s' if bloquear else ''),
            (identificador,),
            una=True,
        )

    def eliminar_bien_material(self, identificador: int) -> None:
        self.ejecutar('DELETE FROM bien_material WHERE id_bien=%s', (identificador,))
