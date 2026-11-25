"""Datos de préstamos y sus escrituras atómicas; no decide elegibilidad ni plazos."""

from collections import Counter

from dominio.compartido.validacion import Conflicto
from dominio.gestion_control.politica_prestamo import HorarioAtencion
from dominio.gestion_prestamos.prestamo import ContextoEntrega
from dominio.gestion_prestamos.reserva import EN_ESPERA, ESTADOS_PENDIENTES
from repositorio.base_datos.base_sql import RepositorioSQL
from repositorio.personas_usuarios.repositorio_persona_sql import CONSULTA as PERSONAS
from repositorio.control.repositorio_sancion_sql import RepositorioSancionSQL

ESTADO_SQL = '''CASE
    WHEN NOT EXISTS(SELECT 1 FROM detalle_prestamo e WHERE e.id_prestamo=p.id_prestamo
        AND e.fecha_devolucion IS NULL AND e.fecha_regularizacion IS NULL) THEN CASE WHEN EXISTS(SELECT 1 FROM detalle_prestamo z WHERE z.id_prestamo=p.id_prestamo AND z.fecha_regularizacion IS NOT NULL) THEN 'REGULARIZADO' ELSE 'DEVUELTO' END
    WHEN EXISTS(SELECT 1 FROM detalle_prestamo e WHERE e.id_prestamo=p.id_prestamo
        AND e.fecha_devolucion IS NULL AND e.fecha_regularizacion IS NULL AND e.fecha_limite_devolucion<UTC_TIMESTAMP()) THEN 'VENCIDO'
    WHEN EXISTS(SELECT 1 FROM detalle_prestamo e WHERE e.id_prestamo=p.id_prestamo
        AND (e.fecha_devolucion IS NOT NULL OR e.fecha_regularizacion IS NOT NULL)) THEN 'PARCIALMENTE_DEVUELTO'
    ELSE 'ACTIVO' END'''

SITUACION_BIEN_SQL = """CASE
    WHEN d.fecha_regularizacion IS NOT NULL THEN 'REGULARIZADO'
    WHEN d.fecha_devolucion IS NOT NULL THEN 'DEVUELTO'
    WHEN b.estado='PERDIDO' THEN 'PERDIDO'
    WHEN d.fecha_limite_devolucion<UTC_TIMESTAMP() THEN 'VENCIDO'
    ELSE 'PENDIENTE' END"""


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
        pendientes = self._consultar_bienes_pendientes((documento,))[documento]
        reservas = self._contar_reservas_activas((documento,), bloquear=False)[documento]
        horario = self.consultar_sql(
            '''SELECT TIME_FORMAT(hora_apertura,'%H:%i') AS apertura,
            TIME_FORMAT(hora_cierre,'%H:%i') AS cierre FROM configuracion_general WHERE id_configuracion=1''',
            una=True,
        )
        return dict(
            persona=persona,
            politicas=politicas,
            limite=limite['maximo_articulos'] if limite else None,
            pendientes=len(pendientes),
            reservas=reservas,
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
            (SELECT MIN(d.fecha_limite_devolucion) FROM detalle_prestamo d WHERE d.id_prestamo=p.id_prestamo AND d.fecha_devolucion IS NULL AND d.fecha_regularizacion IS NULL) AS fecha_limite
            FROM prestamo p JOIN persona per ON per.dni=p.dni_persona WHERE 1=1'''
        parametros = []
        if documento:
            sql += ''' AND (p.dni_persona=%s OR EXISTS(SELECT 1 FROM participante_prestamo pp
                WHERE pp.id_prestamo=p.id_prestamo AND pp.dni_persona=%s))'''
            parametros += [documento, documento]
        if filtros.get('q'):
            sql += """ AND (p.dni_persona LIKE %s OR CONCAT(per.nombres,' ',per.apellidos) LIKE %s
                OR EXISTS(SELECT 1 FROM estudiante e WHERE e.dni=per.dni AND e.cui LIKE %s)
                OR p.id_prestamo=%s)"""
            parametros += [
                f"%{filtros['q']}%",
                f"%{filtros['q']}%",
                f"%{filtros['q']}%",
                filtros['q'] if filtros['q'].isdigit() else 0,
            ]
        if filtros.get('estado') == 'PENDIENTES':
            sql += ''' AND EXISTS(SELECT 1 FROM detalle_prestamo e
                WHERE e.id_prestamo=p.id_prestamo AND e.fecha_devolucion IS NULL AND e.fecha_regularizacion IS NULL)'''
        elif filtros.get('estado') == 'PERDIDOS':
            sql += ''' AND EXISTS(SELECT 1 FROM detalle_prestamo e JOIN bien_material b ON b.id_bien=e.id_bien
                WHERE e.id_prestamo=p.id_prestamo AND e.fecha_devolucion IS NULL AND e.fecha_regularizacion IS NULL AND b.estado='PERDIDO')'''
        elif filtros.get('estado'):
            sql += ' AND (' + ESTADO_SQL + ')=%s'
            parametros.append(filtros['estado'])
        return self.consultar_sql(
            sql + ' ORDER BY p.fecha_entrega DESC,p.id_prestamo DESC', parametros
        )

    def consultar_resumen_prestamos(self, documento=None):
        sql = '''SELECT COALESCE(SUM(d.pendientes>0),0) AS prestamos_pendientes,
            COALESCE(SUM(d.vencidos>0),0) AS prestamos_vencidos FROM prestamo p JOIN (
                SELECT id_prestamo,SUM(fecha_devolucion IS NULL AND fecha_regularizacion IS NULL) AS pendientes,
                SUM(fecha_devolucion IS NULL AND fecha_regularizacion IS NULL AND fecha_limite_devolucion<UTC_TIMESTAMP()) AS vencidos
                FROM detalle_prestamo GROUP BY id_prestamo
            ) d ON d.id_prestamo=p.id_prestamo'''
        parametros: tuple = ()
        if documento is not None:
            sql += ''' WHERE p.dni_persona=%s OR EXISTS(SELECT 1 FROM participante_prestamo pp
                WHERE pp.id_prestamo=p.id_prestamo AND pp.dni_persona=%s)'''
            parametros = (documento, documento)
        return self.consultar_sql(sql, parametros, una=True)

    def consultar_prestamo_para_actualizar(self, identificador):
        prestamo = self.consultar_sql(
            'SELECT id_prestamo,dni_persona,estado FROM prestamo WHERE id_prestamo=%s FOR UPDATE',
            (identificador,),
            una=True,
        )
        if prestamo is not None:
            prestamo['detalles'] = self.consultar_sql(
                '''SELECT d.*,b.estado AS estado_bien,b.codigo_inventario FROM detalle_prestamo d
                JOIN bien_material b ON b.id_bien=d.id_bien
                WHERE d.id_prestamo=%s ORDER BY b.id_bien FOR UPDATE''',
                (identificador,),
            )
        return prestamo

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
            r.nombre AS recurso,po.plazo_maximo,po.unidad_plazo,s.id_sancion,s.estado AS estado_sancion,
            s.gravedad,s.fecha_fin AS fecha_fin_sancion
            FROM detalle_prestamo d JOIN bien_material b ON b.id_bien=d.id_bien
            JOIN recurso r ON r.id_recurso=b.id_recurso JOIN politica_prestamo po ON po.id_politica=d.id_politica
            LEFT JOIN sancion s ON s.id_sancion=(SELECT sx.id_sancion FROM sancion sx
                JOIN incidencia ix ON ix.id_incidencia=sx.id_incidencia_ref
                WHERE ix.id_detalle=d.id_detalle
                ORDER BY (sx.estado='ACTIVA') DESC,sx.id_sancion DESC LIMIT 1)
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

    def es_participante(self, prestamo, documento):
        return self.consultar_sql('''SELECT id_participante FROM participante_prestamo
            WHERE id_prestamo=%s AND dni_persona=%s FOR SHARE''', (prestamo, documento), una=True) is not None

    def consultar_operador_autorizable(self, documento):
        return self.consultar_sql('''SELECT u.id_usuario FROM usuario_sistema u
            JOIN persona p ON p.dni=u.dni_persona WHERE u.dni_persona=%s AND p.estado='ACTIVA'
            AND u.estado_cuenta='ACTIVA' AND u.rol IN ('ENCARGADO_PRESTAMOS','ADMINISTRADOR') FOR SHARE''',
            (documento,), una=True) is not None

    def guardar_autorizacion_propia(self, datos):
        return self.registrar_historial_estado(
            'AUTORIZACION_PROPIA', datos['id_prestamo_objetivo'], None, 'EMITIDA',
            datos['dni_administrador'], datos['motivo'], dni_objetivo=datos['dni_operador'],
            datos={'accion': datos['accion']},
        )

    def consultar_autorizacion_propia(self, identificador, documento, accion, prestamo):
        return self.consultar_sql('''SELECT a.id_historial_estado AS id_registro,
            a.dni_objetivo AS dni_operador,a.dni_responsable AS dni_administrador,a.observacion AS motivo
            FROM historial_estado a
            JOIN usuario_sistema administrador ON administrador.dni_persona=a.dni_responsable
            JOIN persona p ON p.dni=a.dni_responsable AND p.dni<>a.dni_objetivo
            WHERE a.entidad='AUTORIZACION_PROPIA' AND a.estado_nuevo='EMITIDA' AND a.dni_objetivo=%s
            AND COALESCE(a.datos->>'$.codigo_anterior',CAST(a.id_historial_estado AS CHAR))=%s
            AND a.datos->>'$.accion'=%s AND a.id_entidad<=>%s
            AND a.fecha>UTC_TIMESTAMP()-INTERVAL 1 DAY AND administrador.rol='ADMINISTRADOR'
            AND administrador.estado_cuenta='ACTIVA' AND p.estado='ACTIVA' FOR UPDATE OF a''',
            (documento, str(identificador), accion, prestamo), una=True)

    def consumir_autorizacion_propia(self, identificador, prestamo):
        self.ejecutar('''UPDATE historial_estado
            SET estado_anterior='EMITIDA',estado_nuevo='UTILIZADA',
                datos=JSON_SET(datos,'$.fecha_uso',UTC_TIMESTAMP(),'$.id_prestamo_uso',%s)
            WHERE id_historial_estado=%s AND entidad='AUTORIZACION_PROPIA' AND estado_nuevo='EMITIDA' ''',
            (prestamo, identificador))
        if self._cursor.rowcount != 1:
            raise Conflicto('La autorización ya se utilizó.')

    def _consultar_bienes_pendientes(self, documentos, bloquear=False):
        pendientes = {documento: {} for documento in documentos}
        marcas = ','.join(['%s'] * len(documentos))
        # La lectura con bloqueo ve entregas confirmadas aunque la transacción ya haya leído al encargado.
        bloqueo = ' FOR SHARE' if bloquear else ''
        for origen in ('prestamo', 'participante_prestamo'):
            filas = self.consultar_sql(
                f'''SELECT p.dni_persona,d.id_detalle,d.fecha_limite_devolucion<UTC_TIMESTAMP() AS vencido
                FROM {origen} p JOIN detalle_prestamo d ON d.id_prestamo=p.id_prestamo
                WHERE p.dni_persona IN ({marcas}) AND d.fecha_devolucion IS NULL
                AND d.fecha_regularizacion IS NULL''' + bloqueo,
                documentos,
            )
            for fila in filas:
                # El responsable puede figurar también entre los participantes del mismo préstamo.
                pendientes[fila['dni_persona']][fila['id_detalle']] = fila['vencido']
        return pendientes

    def _contar_reservas_activas(self, documentos, reserva_origen=None, bloquear=True):
        marcas = ','.join(['%s'] * len(documentos))
        sql = f'''SELECT dni_persona FROM reserva WHERE dni_persona IN ({marcas})
            AND estado IN (%s,%s)
            AND (fecha_limite_vencimiento IS NULL OR fecha_limite_vencimiento>UTC_TIMESTAMP())'''
        parametros = (*documentos, *ESTADOS_PENDIENTES)
        if reserva_origen is not None:
            sql += ' AND id_reserva<>%s'
            parametros += (reserva_origen,)
        conteo = dict.fromkeys(documentos, 0)
        for fila in self.consultar_sql(sql + (' FOR SHARE' if bloquear else ''), parametros):
            conteo[fila['dni_persona']] += 1
        return conteo

    def consultar_cupo_persona(self, persona, reserva_origen=None) -> dict:
        documento = persona['dni']
        limite = self.consultar_sql('SELECT maximo_articulos FROM limite_articulos_prestamo '
                                    'WHERE tipo_persona=%s FOR SHARE', (persona['tipo'],), una=True)
        return dict(limite=limite['maximo_articulos'] if limite else None,
                    pendientes=len(self._consultar_bienes_pendientes((documento,), bloquear=True)[documento]),
                    reservas=self._contar_reservas_activas((documento,), reserva_origen)[documento])

    def consultar_balance_cola(self, recurso, solo_en_turno=False) -> tuple[int, int]:
        disponibles = self.consultar_sql(
            "SELECT id_bien FROM bien_material WHERE id_recurso=%s AND estado='DISPONIBLE' FOR SHARE",
            (recurso,),
        )
        esperas = self.consultar_sql(
            '''SELECT id_reserva FROM reserva WHERE id_recurso=%s AND estado=%s
            AND (fecha_limite_vencimiento IS NULL OR fecha_limite_vencimiento>UTC_TIMESTAMP())'''
            + (' AND fecha_requerida<=UTC_TIMESTAMP()' if solo_en_turno else '') + ' FOR SHARE',
            (recurso, EN_ESPERA),
        )
        return len(disponibles), len(esperas)

    def consultar_contexto_entrega_prestamo(self, solicitud, reserva_origen=None) -> ContextoEntrega:
        ids = tuple(sorted(solicitud.bienes))
        marcas_bienes = ','.join(['%s'] * len(ids))
        recursos = tuple(sorted({fila['id_recurso'] for fila in self.consultar_sql(
            f'SELECT id_recurso FROM bien_material WHERE id_bien IN ({marcas_bienes})', ids
        )}))
        if recursos:
            marcas_recursos = ','.join(['%s'] * len(recursos))
            self.consultar_sql(f'SELECT id_recurso FROM recurso WHERE id_recurso IN ({marcas_recursos}) '
                               'ORDER BY id_recurso FOR UPDATE', recursos)
        documentos = tuple(sorted(set([*solicitud.solicitantes, solicitud.dni_encargado])))
        marcas = ','.join(['%s'] * len(documentos))
        personas = {
            p['dni']: p
            for p in self.consultar_sql(
                PERSONAS + f' WHERE p.dni IN ({marcas}) ORDER BY p.dni FOR UPDATE', documentos
            )
        }
        participantes = tuple(sorted(set(solicitud.solicitantes)))
        pendientes = self._consultar_bienes_pendientes(participantes, bloquear=True)
        reservas = self._contar_reservas_activas(participantes, reserva_origen)
        tipo = personas.get(solicitud.dni_persona, {}).get('tipo')
        limites = {
            fila['tipo_persona']: fila['maximo_articulos']
            for fila in self.consultar_sql('SELECT * FROM limite_articulos_prestamo FOR SHARE')
        }
        bienes = self.consultar_sql(
            f'''SELECT b.*,r.id_categoria FROM bien_material b
            JOIN recurso r ON r.id_recurso=b.id_recurso WHERE b.id_bien IN ({marcas_bienes})
            ORDER BY b.id_bien FOR UPDATE''',
            ids,
        )
        cola_prioritaria = False
        if reserva_origen is None:
            for recurso, cantidad in sorted(Counter(bien['id_recurso'] for bien in bienes).items()):
                disponibles, en_espera = self.consultar_balance_cola(recurso, solo_en_turno=True)
                if en_espera and disponibles - cantidad < en_espera:
                    cola_prioritaria = True
                    break
        entregas = self.consultar_sql(
            f'''SELECT id_detalle FROM detalle_prestamo
            WHERE id_bien IN ({marcas_bienes}) AND fecha_devolucion IS NULL
            AND fecha_regularizacion IS NULL FOR UPDATE''',
            ids,
        )
        politicas = self.consultar_sql(
            'SELECT * FROM politica_prestamo WHERE tipo_persona=%s AND vigente=TRUE ORDER BY id_politica FOR UPDATE',
            (tipo,),
        )
        configuracion = self.consultar_sql(
            'SELECT hora_apertura,hora_cierre,dias_atencion FROM configuracion_general '
            'WHERE id_configuracion=1 FOR UPDATE',
            una=True,
        )
        return dict(
            personas=personas,
            sancion=self.sanciones.existen_sanciones_activas(participantes),
            vencido=any(any(bienes.values()) for bienes in pendientes.values()),
            limites_por_persona={dni: limites.get(personas.get(dni, {}).get('tipo')) for dni in participantes},
            pendientes_por_persona={dni: len(bienes) for dni, bienes in pendientes.items()},
            reservas_por_persona=reservas,
            bienes=bienes,
            entregas_pendientes=bool(entregas),
            cola_prioritaria=cola_prioritaria,
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

    def consultar_politica_aplicada(self, identificador):
        return self.consultar_sql('SELECT * FROM politica_prestamo WHERE id_politica=%s',
                                  (identificador,), una=True)

    def registrar_devolucion(self, detalle, devolucion, fecha, actor):
        self.ejecutar(
            '''UPDATE detalle_prestamo SET fecha_devolucion=%s,dni_encargado_devolucion=%s,
            condicion_devolucion=%s,observaciones_devolucion=%s WHERE id_detalle=%s
            AND fecha_devolucion IS NULL AND fecha_regularizacion IS NULL''',
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

    def cerrar_detalle_por_reposicion(self, detalle, fecha):
        self.ejecutar(
            '''UPDATE detalle_prestamo SET fecha_regularizacion=%s
            WHERE id_detalle=%s AND fecha_devolucion IS NULL AND fecha_regularizacion IS NULL''',
            (fecha, detalle),
        )

    def consultar_ultimo_movimiento_bien(self, bien):
        return self.consultar_sql('''SELECT * FROM historial_estado WHERE entidad='BIEN_MATERIAL'
            AND id_entidad=%s ORDER BY id_historial_estado DESC LIMIT 1 FOR SHARE''', (bien,), una=True)

    def rectificar_devolucion(self, detalle, movimiento, motivo, actor):
        if self.consultar_sql('''SELECT id_detalle FROM detalle_prestamo WHERE id_bien=%s
                AND fecha_devolucion IS NULL AND fecha_regularizacion IS NULL LIMIT 1 FOR UPDATE''',
                (detalle['id_bien'],), una=True):
            raise Conflicto('El bien tiene otro préstamo pendiente.')
        self.registrar_historial_estado(
            'RECTIFICACION_DEVOLUCION', detalle['id_detalle'], 'DEVUELTO', 'PENDIENTE', actor, motivo,
            dni_objetivo=detalle['dni_encargado_devolucion'],
            datos={'fecha_devolucion_original': detalle['fecha_devolucion'].isoformat(sep=' '),
                   'condicion_original': detalle['condicion_devolucion'],
                   'observacion_original': detalle['observaciones_devolucion']},
        )
        self.ejecutar('''UPDATE detalle_prestamo SET fecha_devolucion=NULL,dni_encargado_devolucion=NULL,
            condicion_devolucion=NULL,observaciones_devolucion=NULL WHERE id_detalle=%s''', (detalle['id_detalle'],))
        self.ejecutar('UPDATE bien_material SET estado=%s WHERE id_bien=%s',
                      (movimiento['estado_anterior'], detalle['id_bien']))
        self.registrar_historial_estado('BIEN_MATERIAL', detalle['id_bien'], detalle['estado_bien'],
                                     movimiento['estado_anterior'], actor, f'Rectificación: {motivo}'[:255])

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
