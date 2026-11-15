"""Datos de préstamos y sus escrituras atómicas; no decide elegibilidad ni plazos."""

from dominio.compartido.validacion import Conflicto
from dominio.gestion_control.politica_prestamo import HorarioAtencion
from repositorio.base_sql import RepositorioSQL
from repositorio.repositorio_persona_sql import CONSULTA as PERSONAS
from repositorio.repositorio_sancion_sql import RepositorioSancionSQL

ESTADO_SQL = '''CASE
    WHEN NOT EXISTS(SELECT 1 FROM detalle_prestamo e WHERE e.id_prestamo=p.id_prestamo
        AND e.fecha_devolucion IS NULL) THEN 'DEVUELTO'
    WHEN EXISTS(SELECT 1 FROM detalle_prestamo e WHERE e.id_prestamo=p.id_prestamo
        AND e.fecha_devolucion IS NULL AND e.fecha_limite_devolucion<UTC_TIMESTAMP()) THEN 'VENCIDO'
    WHEN EXISTS(SELECT 1 FROM detalle_prestamo e WHERE e.id_prestamo=p.id_prestamo
        AND e.fecha_devolucion IS NOT NULL) THEN 'PARCIALMENTE_DEVUELTO'
    ELSE 'ACTIVO' END'''


class RepositorioPrestamoSQL(RepositorioSQL):
    def consultar_condiciones_prestamo(self, documento):
        persona = self.consultar_sql(PERSONAS + ' WHERE p.dni=%s', (documento,), una=True)
        tipo = persona['tipo'] if persona else None
        politicas = self.consultar_sql(
            '''SELECT c.nombre AS categoria,p.plazo_maximo,p.unidad_plazo,p.permite_salida
            FROM politica_prestamo p JOIN categoria_recurso c ON c.id_categoria=p.id_categoria
            WHERE p.tipo_persona=%s AND p.vigente=TRUE ORDER BY c.nombre''',
            (tipo,),
        )
        limite = self.consultar_sql(
            'SELECT maximo_articulos FROM limite_articulos_prestamo WHERE tipo_persona=%s',
            (tipo,),
            una=True,
        )
        pendientes = self.consultar_sql(
            '''SELECT COUNT(*) AS total FROM detalle_prestamo d
            JOIN prestamo p ON p.id_prestamo=d.id_prestamo WHERE p.dni_persona=%s AND d.fecha_devolucion IS NULL''',
            (documento,),
            una=True,
        )
        horario = self.consultar_sql(
            '''SELECT TIME_FORMAT(hora_apertura,'%H:%i') AS apertura,
            TIME_FORMAT(hora_cierre,'%H:%i') AS cierre FROM configuracion_general WHERE id_configuracion=1''',
            una=True,
        )
        return dict(
            persona=persona,
            politicas=politicas,
            limite=limite['maximo_articulos'] if limite else None,
            pendientes=pendientes['total'],
            horario=horario,
        )

    @property
    def sanciones(self):
        return RepositorioSancionSQL(self.conexion, self._cursor)

    def consultar_prestamos(self, filtros, documento=None):
        sql = f'''SELECT p.*,CONCAT(per.nombres,' ',per.apellidos) AS solicitante,
            {ESTADO_SQL} AS estado_actual,
            (SELECT COUNT(*) FROM detalle_prestamo d WHERE d.id_prestamo=p.id_prestamo) AS total_bienes,
            (SELECT COUNT(*) FROM detalle_prestamo d WHERE d.id_prestamo=p.id_prestamo AND d.fecha_devolucion IS NOT NULL) AS devueltos,
            (SELECT MIN(d.fecha_limite_devolucion) FROM detalle_prestamo d WHERE d.id_prestamo=p.id_prestamo AND d.fecha_devolucion IS NULL) AS fecha_limite
            FROM prestamo p JOIN persona per ON per.dni=p.dni_persona WHERE 1=1'''
        parametros = []
        if documento:
            sql += ''' AND (p.dni_persona=%s OR EXISTS(SELECT 1 FROM participante_prestamo pp
                WHERE pp.id_prestamo=p.id_prestamo AND pp.dni_persona=%s))'''
            parametros += [documento, documento]
        if filtros.get('q'):
            sql += " AND (p.dni_persona LIKE %s OR CONCAT(per.nombres,' ',per.apellidos) LIKE %s OR p.id_prestamo=%s)"
            parametros += [
                f"%{filtros['q']}%",
                f"%{filtros['q']}%",
                filtros['q'] if filtros['q'].isdigit() else 0,
            ]
        if filtros.get('estado') == 'PENDIENTES':
            sql += ''' AND EXISTS(SELECT 1 FROM detalle_prestamo e
                WHERE e.id_prestamo=p.id_prestamo AND e.fecha_devolucion IS NULL)'''
        elif filtros.get('estado') == 'PERDIDOS':
            sql += ''' AND EXISTS(SELECT 1 FROM detalle_prestamo e JOIN bien_material b ON b.id_bien=e.id_bien
                WHERE e.id_prestamo=p.id_prestamo AND e.fecha_devolucion IS NULL AND b.estado='PERDIDO')'''
        elif filtros.get('estado'):
            sql += ' AND (' + ESTADO_SQL + ')=%s'
            parametros.append(filtros['estado'])
        return self.consultar_sql(
            sql + ' ORDER BY p.fecha_entrega DESC,p.id_prestamo DESC', parametros
        )

    def consultar_prestamo(self, identificador, bloquear=False):
        fila = self.consultar_sql(
            f'''SELECT p.*,CONCAT(per.nombres,' ',per.apellidos) AS solicitante,
            {ESTADO_SQL} AS estado_actual FROM prestamo p JOIN persona per ON per.dni=p.dni_persona
            WHERE p.id_prestamo=%s''' + (' FOR UPDATE' if bloquear else ''),
            (identificador,),
            una=True,
        )
        if fila is None:
            return None
        fila['detalles'] = self.consultar_sql(
            '''SELECT d.*,b.estado AS estado_bien,b.codigo_inventario,
            r.nombre AS recurso,po.plazo_maximo,po.unidad_plazo,s.id_sancion,s.estado AS estado_sancion
            FROM detalle_prestamo d JOIN bien_material b ON b.id_bien=d.id_bien
            JOIN recurso r ON r.id_recurso=b.id_recurso JOIN politica_prestamo po ON po.id_politica=d.id_politica
            LEFT JOIN incidencia i ON i.id_detalle=d.id_detalle AND i.tipo='RETRASO'
            LEFT JOIN sancion s ON s.id_incidencia_ref=i.id_incidencia
            WHERE d.id_prestamo=%s ORDER BY b.id_bien''' + (' FOR UPDATE' if bloquear else ''),
            (identificador,),
        )
        fila['participantes'] = self.consultar_sql(
            '''SELECT pp.*,CONCAT(per.nombres,' ',per.apellidos) AS nombre
            FROM participante_prestamo pp JOIN persona per ON per.dni=pp.dni_persona
            WHERE pp.id_prestamo=%s ORDER BY pp.responsable DESC,per.apellidos''',
            (identificador,),
        )
        return fila

    def consultar_contexto_entrega_prestamo(self, solicitud):
        documentos = tuple(sorted(set([*solicitud.solicitantes, solicitud.dni_encargado])))
        marcas = ','.join(['%s'] * len(documentos))
        personas = {
            p['dni']: p
            for p in self.consultar_sql(
                PERSONAS + f' WHERE p.dni IN ({marcas}) ORDER BY p.dni FOR UPDATE', documentos
            )
        }
        participantes = tuple(sorted(set(solicitud.solicitantes)))
        marcas_personas = ','.join(['%s'] * len(participantes))
        vencidos = self.consultar_sql(
            f'''SELECT d.id_detalle FROM detalle_prestamo d
            JOIN prestamo p ON p.id_prestamo=d.id_prestamo WHERE d.fecha_devolucion IS NULL
            AND d.fecha_limite_devolucion<UTC_TIMESTAMP() AND (p.dni_persona IN ({marcas_personas})
            OR EXISTS(SELECT 1 FROM participante_prestamo pp WHERE pp.id_prestamo=p.id_prestamo
                AND pp.dni_persona IN ({marcas_personas}))) LIMIT 1''',
            participantes * 2,
        )
        tipo = personas.get(solicitud.dni_persona, {}).get('tipo')
        limite = self.consultar_sql(
            'SELECT maximo_articulos FROM limite_articulos_prestamo WHERE tipo_persona=%s FOR UPDATE',
            (tipo,),
            una=True,
        )
        pendientes = self.consultar_sql(
            '''SELECT COUNT(*) AS total FROM detalle_prestamo d
            JOIN prestamo p ON p.id_prestamo=d.id_prestamo WHERE p.dni_persona=%s AND d.fecha_devolucion IS NULL''',
            (solicitud.dni_persona,),
            una=True,
        )['total']
        ids = tuple(sorted(solicitud.bienes))
        marcas_bienes = ','.join(['%s'] * len(ids))
        bienes = self.consultar_sql(
            f'''SELECT b.*,r.id_categoria FROM bien_material b
            JOIN recurso r ON r.id_recurso=b.id_recurso WHERE b.id_bien IN ({marcas_bienes})
            ORDER BY b.id_bien FOR UPDATE''',
            ids,
        )
        entregas = self.consultar_sql(
            f'''SELECT id_detalle FROM detalle_prestamo
            WHERE id_bien IN ({marcas_bienes}) AND fecha_devolucion IS NULL FOR UPDATE''',
            ids,
        )
        politicas = self.consultar_sql(
            'SELECT * FROM politica_prestamo WHERE tipo_persona=%s AND vigente=TRUE ORDER BY id_politica FOR UPDATE',
            (tipo,),
        )
        configuracion = self.consultar_sql(
            'SELECT hora_apertura,hora_cierre FROM configuracion_general WHERE id_configuracion=1 FOR UPDATE',
            una=True,
        )
        return dict(
            personas=personas,
            sancion=self.sanciones.existen_sanciones_activas(participantes),
            vencido=bool(vencidos),
            limite=limite['maximo_articulos'] if limite else None,
            pendientes=pendientes,
            bienes=bienes,
            entregas_pendientes=bool(entregas),
            politicas={p['id_categoria']: p for p in politicas},
            horario=HorarioAtencion(**configuracion) if configuracion else None,
            ahora=self.consultar_fecha_actual(),
        )

    def registrar_entrega_prestamo(self, solicitud, plan, fecha):
        identificador = self.insertar(
            'prestamo',
            dict(
                dni_persona=solicitud.dni_persona,
                dni_encargado=solicitud.dni_encargado,
                tipo_prestamo=solicitud.tipo_prestamo,
                fecha_solicitud=fecha,
                fecha_entrega=fecha,
                estado='ACTIVO',
                observaciones=solicitud.observaciones_registro,
            ),
        )
        for detalle in plan:
            fila = dict(detalle)
            anterior = fila.pop('estado_anterior')
            self.insertar('detalle_prestamo', dict(id_prestamo=identificador, **fila))
            self.ejecutar(
                "UPDATE bien_material SET estado='PRESTADO' WHERE id_bien=%s AND estado=%s",
                (fila['id_bien'], anterior),
            )
            if self._cursor.rowcount != 1:
                raise Conflicto('El inventario cambió durante la entrega.')
            self.registrar_historial_estado(
                'BIEN_MATERIAL',
                fila['id_bien'],
                anterior,
                'PRESTADO',
                solicitud.dni_encargado,
                f'Entrega del préstamo #{identificador}.',
            )
        if solicitud.tipo_prestamo == 'GRUPAL':
            for documento in solicitud.solicitantes:
                responsable = documento == solicitud.dni_persona
                self.insertar(
                    'participante_prestamo',
                    dict(
                        id_prestamo=identificador,
                        dni_persona=documento,
                        responsable=responsable,
                        rol_participacion='Responsable' if responsable else 'Integrante',
                    ),
                )
        self.registrar_historial_estado(
            'PRESTAMO',
            identificador,
            None,
            'ACTIVO',
            solicitud.dni_encargado,
            'Entrega registrada.',
        )
        return identificador

    def registrar_devolucion(self, detalle, devolucion, fecha, actor):
        self.ejecutar(
            '''UPDATE detalle_prestamo SET fecha_devolucion=%s,dni_encargado_devolucion=%s,
            condicion_devolucion=%s,observaciones_devolucion=%s WHERE id_detalle=%s AND fecha_devolucion IS NULL''',
            (
                fecha,
                actor,
                devolucion.condicion,
                devolucion.observacion or None,
                detalle['id_detalle'],
            ),
        )
        if self._cursor.rowcount != 1:
            raise Conflicto('El detalle ya fue recibido.')
        self.ejecutar(
            'UPDATE bien_material SET estado=%s WHERE id_bien=%s',
            (devolucion.estado_bien, detalle['id_bien']),
        )
        self.registrar_historial_estado(
            'BIEN_MATERIAL',
            detalle['id_bien'],
            detalle['estado_bien'],
            devolucion.estado_bien,
            actor,
            f'Recepción del préstamo #{detalle["id_prestamo"]}.',
        )

    def actualizar_estado_prestamo(self, prestamo, nuevo, actor, motivo):
        self.ejecutar(
            'UPDATE prestamo SET estado=%s WHERE id_prestamo=%s', (nuevo, prestamo['id_prestamo'])
        )
        self.registrar_historial_estado(
            'PRESTAMO', prestamo['id_prestamo'], prestamo['estado'], nuevo, actor, motivo
        )

    def registrar_perdida_bien_material(self, prestamo, detalle, actor, motivo):
        self.ejecutar(
            "UPDATE bien_material SET estado='PERDIDO' WHERE id_bien=%s", (detalle['id_bien'],)
        )
        self.registrar_historial_estado(
            'BIEN_MATERIAL', detalle['id_bien'], detalle['estado_bien'], 'PERDIDO', actor, motivo
        )
        self.registrar_historial_estado(
            'PRESTAMO',
            prestamo['id_prestamo'],
            prestamo['estado'],
            prestamo['estado'],
            actor,
            'Pérdida reportada; la devolución continúa pendiente.',
        )
