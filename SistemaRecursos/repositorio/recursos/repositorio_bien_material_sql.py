from dataclasses import asdict

from mysql.connector import IntegrityError

from dominio.compartido.validacion import Conflicto
from dominio.gestion_recursos.bien_material import generar_identificador_sistema
from repositorio.base_datos.base_sql import RepositorioSQL

INTENTOS_IDENTIFICADOR = 8


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
                '(b.codigo_inventario LIKE %s OR b.identificador_sistema LIKE %s OR b.numero_serie LIKE %s'
                ' OR r.nombre LIKE %s OR r.marca LIKE %s OR r.modelo LIKE %s)'
            )
            parametros.extend([f"%{filtros['q']}%"] * 6)
        sql = '''SELECT b.*,r.nombre AS recurso,r.id_categoria FROM bien_material b
            JOIN recurso r ON r.id_recurso=b.id_recurso'''
        if condiciones:
            sql += ' WHERE ' + ' AND '.join(condiciones)
        return self.consultar_sql(sql + ' ORDER BY r.nombre,b.codigo_inventario', parametros)

    def guardar_bien_material(self, bien) -> int:
        datos = asdict(bien)
        identificador = datos.pop('id_bien')
        if bien.numero_serie:
            recurso = self.consultar_sql('SELECT marca,modelo FROM recurso WHERE id_recurso=%s FOR SHARE',
                                         (bien.id_recurso,), una=True)
            if recurso and recurso['marca'] and recurso['modelo']:
                self.validar_serie_por_modelo(bien.numero_serie, recurso['marca'], recurso['modelo'], identificador)
        if identificador is None:
            bien.id_bien = self._insertar_bien_con_identificador_de_sistema(datos)
        else:
            self.ejecutar_escritura_sql(
                'UPDATE bien_material SET '
                + ','.join(c + '=%s' for c in datos)
                + ' WHERE id_bien=%s',
                (*datos.values(), identificador),
            )
        return bien.id_bien

    def validar_serie_por_modelo(self, serie, marca, modelo, bien=None):
        self.consultar_sql('SELECT id_recurso FROM recurso WHERE marca=%s AND modelo=%s '
                           'ORDER BY id_recurso FOR UPDATE', (marca, modelo))
        repetido = self.consultar_sql(
            '''SELECT b.id_bien FROM bien_material b JOIN recurso r ON r.id_recurso=b.id_recurso
            WHERE r.marca=%s AND r.modelo=%s AND b.numero_serie=%s AND NOT (b.id_bien<=>%s)
            LIMIT 1 FOR SHARE''', (marca, modelo, serie, bien), una=True,
        )
        if repetido:
            raise Conflicto('Ese número de serie ya está registrado para la misma marca y modelo.')

    def _insertar_bien_con_identificador_de_sistema(self, datos: dict) -> int:
        """Genera el identificador en el servidor; una colisión reintenta con otro valor.

        En InnoDB un INSERT rechazado por clave única no revierte la transacción en curso.
        """
        anio = self.consultar_fecha_actual().year
        for _ in range(INTENTOS_IDENTIFICADOR):
            try:
                return self.insertar_fila_sql(
                    'bien_material',
                    dict(datos, identificador_sistema=generar_identificador_sistema(anio)),
                )
            except IntegrityError as error:
                if 'identificador_sistema' not in (error.msg or ''):
                    raise
        raise RuntimeError('No se pudo generar un identificador único para el bien.')

    def cambiar_estado_bien_material(self, identificador, anterior, nuevo, motivo, actor) -> None:
        self.ejecutar_escritura_sql('UPDATE bien_material SET estado=%s WHERE id_bien=%s', (nuevo, identificador))
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
        self.ejecutar_escritura_sql('DELETE FROM bien_material WHERE id_bien=%s', (identificador,))

    # Mantenimientos (MAN-01)

    def consultar_mantenimiento_abierto(self, identificador: int, bloquear=False) -> dict | None:
        return self.consultar_sql(
            '''SELECT * FROM mantenimiento_bien WHERE id_bien=%s AND fecha_fin_real IS NULL'''
            + (' FOR UPDATE' if bloquear else ''),
            (identificador,),
            una=True,
        )

    def consultar_mantenimientos(self, identificador: int) -> list[dict]:
        return self.consultar_sql(
            '''SELECT m.*,CONCAT(pa.nombres,' ',pa.apellidos) AS responsable_apertura,
            CONCAT(pc.nombres,' ',pc.apellidos) AS responsable_cierre
            FROM mantenimiento_bien m
            LEFT JOIN persona pa ON pa.dni=m.dni_apertura
            LEFT JOIN persona pc ON pc.dni=m.dni_cierre
            WHERE m.id_bien=%s ORDER BY m.fecha_inicio DESC,m.id_mantenimiento DESC''',
            (identificador,),
        )

    def abrir_mantenimiento(self, identificador, apertura, estado_previo, actor) -> int:
        return self.ejecutar_escritura_sql(
            '''INSERT INTO mantenimiento_bien(id_bien,tipo,motivo,estado_previo,fecha_inicio,
            fecha_fin_estimada,dni_apertura) VALUES(%s,%s,%s,%s,UTC_TIMESTAMP(),%s,%s)''',
            (identificador, apertura.tipo, apertura.motivo, estado_previo,
             apertura.fecha_fin_estimada, actor),
        )

    def cerrar_mantenimiento(self, id_mantenimiento, cierre, actor) -> None:
        self.ejecutar_escritura_sql(
            '''UPDATE mantenimiento_bien SET fecha_fin_real=UTC_TIMESTAMP(),dni_cierre=%s,
            resultado=%s,observacion_cierre=%s
            WHERE id_mantenimiento=%s AND fecha_fin_real IS NULL''',
            (actor, cierre.resultado, cierre.observacion, id_mantenimiento),
        )
