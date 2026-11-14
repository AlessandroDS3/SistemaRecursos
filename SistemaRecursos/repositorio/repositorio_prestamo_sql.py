from __future__ import annotations
from contextlib import contextmanager
from dominio.control import FabricaPoliticaPrestamo, HorarioAtencion, LimiteArticulosPrestamo
from dominio.prestamos import (
    ConflictoAmpliacionError,
    ContextoEntrega,
    DetallePrestamo,
    IOperacionPrestamo,
    IRepositorioPrestamo,
    Prestamo,
    PrestamoDetalle,
    PrestamoListado,
    ResumenPrestamos,
)
from repositorio.conexion_mysql import MySQLConnection
from repositorio.repositorio_bien_material_sql import registrar_historial_bien
from repositorio.repositorio_persona_sql import CONSULTA as CONSULTA_PERSONAS
from repositorio.repositorio_sancion_sql import consultar_sanciones_activas
from repositorio.sanciones_vencimiento_sql import aplicar_sancion_vencimiento


# Estado actual para lecturas: no modifica préstamo ni historial.
ORIGEN_PRESTAMOS_CON_ESTADO = """
    (SELECT base.id_prestamo, base.dni_persona, base.dni_encargado,
            base.tipo_prestamo, base.fecha_solicitud, base.fecha_entrega, base.observaciones,
            CASE
              WHEN NOT EXISTS (SELECT 1 FROM detalle_prestamo estado_detalle
                WHERE estado_detalle.id_prestamo=base.id_prestamo
                  AND estado_detalle.fecha_devolucion IS NULL) THEN 'DEVUELTO'
              WHEN EXISTS (SELECT 1 FROM detalle_prestamo estado_detalle
                WHERE estado_detalle.id_prestamo=base.id_prestamo
                  AND estado_detalle.fecha_devolucion IS NULL
                  AND estado_detalle.fecha_limite_devolucion < UTC_TIMESTAMP()) THEN 'VENCIDO'
              WHEN EXISTS (SELECT 1 FROM detalle_prestamo estado_detalle
                WHERE estado_detalle.id_prestamo=base.id_prestamo
                  AND estado_detalle.fecha_devolucion IS NOT NULL) THEN 'PARCIALMENTE_DEVUELTO'
              ELSE 'ACTIVO'
            END AS estado
     FROM prestamo base)
"""


class RepositorioPrestamoSQL(IRepositorioPrestamo):
    """Lecturas de prestamos y apertura de una operacion SQL por transaccion."""

    def __init__(self, conexion=None):
        self.conexion = conexion or MySQLConnection()

    @contextmanager
    def transaccion(self):
        with self.conexion.sesion(escritura=True) as cursor:
            yield OperacionPrestamoSQL(cursor)

    def consultar_prestamo(self, id_prestamo) -> PrestamoDetalle | None:
        with self.conexion.sesion() as cursor:
            cursor.execute(
                f"""
                SELECT
                    pr.*,
                    CONCAT(p.nombres, ' ', p.apellidos) AS solicitante,
                    p.dni AS documento_identidad,
                    CASE WHEN est.dni IS NOT NULL THEN est.cui END AS cui,
                    CONCAT(e.nombres, ' ', e.apellidos) AS encargado
                FROM {ORIGEN_PRESTAMOS_CON_ESTADO} pr
                JOIN persona p ON p.dni = pr.dni_persona
                LEFT JOIN estudiante est ON est.dni = p.dni
                JOIN persona e ON e.dni = pr.dni_encargado
                WHERE pr.id_prestamo = %s
                """,
                (id_prestamo,),
            )
            prestamo = cursor.fetchone()
            if not prestamo:
                return None
            cursor.execute(
                """
                SELECT
                    d.*, b.codigo_inventario, b.estado AS estado_actual,
                    r.nombre AS recurso, r.id_recurso AS recurso_id,
                    CASE WHEN s.id_sancion IS NOT NULL THEN s.estado
                         WHEN d.fecha_limite_devolucion < COALESCE(d.fecha_devolucion,UTC_TIMESTAMP()) THEN 'ACTIVA'
                         ELSE NULL END AS estado_sancion_vencimiento,
                    s.justificacion_levantamiento,
                    CONCAT(e.nombres, ' ', e.apellidos) AS encargado_devolucion
                FROM detalle_prestamo d
                JOIN bien_material b ON b.id_bien = d.id_bien
                JOIN recurso r ON r.id_recurso = b.id_recurso
                LEFT JOIN incidencia i ON i.id_detalle=d.id_detalle AND i.tipo='RETRASO'
                LEFT JOIN sancion s ON s.id_incidencia_ref=i.id_incidencia
                LEFT JOIN persona e ON e.dni = d.dni_encargado_devolucion
                WHERE d.id_prestamo = %s
                ORDER BY d.id_detalle
                """,
                (id_prestamo,),
            )
            prestamo["detalles"] = cursor.fetchall()
            cursor.execute(
                """
                SELECT pp.*, CONCAT(p.nombres, ' ', p.apellidos) AS nombre
                FROM participante_prestamo pp
                JOIN persona p ON p.dni = pp.dni_persona
                WHERE pp.id_prestamo = %s
                ORDER BY pp.responsable DESC, p.apellidos, p.nombres
                """,
                (id_prestamo,),
            )
            prestamo["participantes"] = cursor.fetchall()
            cursor.execute(
                """
                SELECT h.*, CONCAT(p.nombres, ' ', p.apellidos) AS responsable
                FROM historial_estado h
                LEFT JOIN persona p ON p.dni = h.dni_responsable
                WHERE h.entidad = 'PRESTAMO' AND h.id_entidad = %s
                ORDER BY h.fecha DESC, h.id_historial_estado DESC
                """,
                (id_prestamo,),
            )
            prestamo["historial"] = cursor.fetchall()
            return prestamo

    def consultar_resumen_prestamos(self, dni=None) -> ResumenPrestamos:
        condicion_persona = ""
        valores = ()
        if dni is not None:
            condicion_persona = """
                AND (
                    pr.dni_persona = %s
                    OR EXISTS (
                        SELECT 1
                        FROM participante_prestamo pp
                        WHERE pp.id_prestamo = pr.id_prestamo
                          AND pp.dni_persona = %s
                    )
                )
            """
            valores = (dni, dni)

        consulta_pendientes = f"""
            SELECT COUNT(DISTINCT pr.id_prestamo) AS cantidad
            FROM {ORIGEN_PRESTAMOS_CON_ESTADO} pr
            JOIN detalle_prestamo d ON d.id_prestamo = pr.id_prestamo
            WHERE d.fecha_devolucion IS NULL
              AND pr.estado IN ('ACTIVO', 'VENCIDO', 'PARCIALMENTE_DEVUELTO')
        """ + condicion_persona

        consulta_vencidos = f"""
            SELECT COUNT(DISTINCT pr.id_prestamo) AS cantidad
            FROM {ORIGEN_PRESTAMOS_CON_ESTADO} pr
            JOIN detalle_prestamo d ON d.id_prestamo = pr.id_prestamo
            WHERE d.fecha_devolucion IS NULL
              AND d.fecha_limite_devolucion < UTC_TIMESTAMP()
        """ + condicion_persona

        with self.conexion.sesion() as cursor:
            cursor.execute(consulta_pendientes, valores)
            pendientes = cursor.fetchone()["cantidad"]
            cursor.execute(consulta_vencidos, valores)
            vencidos = cursor.fetchone()["cantidad"]

        return {
            "prestamos_pendientes": pendientes,
            "prestamos_vencidos": vencidos,
        }

    def consultar_prestamos(self, filtros=None, dni=None) -> list[PrestamoListado]:
        sql, valores = self._consulta_todos(filtros, dni)
        with self.conexion.sesion() as cursor:
            cursor.execute(sql + " ORDER BY pr.fecha_entrega DESC,pr.id_prestamo DESC", valores)
            return cursor.fetchall()

    @staticmethod
    def _consulta_todos(filtros=None, dni=None):
        filtros = filtros or {}
        condiciones, valores = [], []
        if dni is not None:
            condiciones.append(
                """
                (
                    pr.dni_persona = %s
                    OR EXISTS (
                        SELECT 1
                        FROM participante_prestamo pp
                        WHERE pp.id_prestamo = pr.id_prestamo
                          AND pp.dni_persona = %s
                    )
                )
                """
            )
            valores.extend((dni, dni))
        termino = filtros.get("q", "").strip().casefold()
        for palabra in termino.split():
            if len(palabra) < 2 and not palabra.isdigit():
                continue
            if dni is not None:
                if palabra.isdigit():
                    condiciones.append("pr.id_prestamo=%s")
                    valores.append(int(palabra))
                else:
                    condiciones.append("1=0")
                continue
            coincidencia = """(
                est.cui LIKE %s
                OR p.apellidos LIKE %s
                OR p.dni LIKE %s
            """
            valores.extend([f"{palabra}%"] * 3)
            if palabra.isdigit():
                coincidencia += " OR pr.id_prestamo=%s"
                valores.append(int(palabra))
            condiciones.append(coincidencia + ")")
        estado = filtros.get("estado")
        if estado and estado not in {"PENDIENTES", "PERDIDOS"}:
            condiciones.append("pr.estado=%s")
            valores.append(estado)
        sql = f"""
            SELECT
                pr.*,
                CONCAT(p.nombres, ' ', p.apellidos) AS solicitante,
                p.dni AS documento_identidad,
                MAX(CASE WHEN est.dni IS NOT NULL THEN est.cui END) AS cui,
                COUNT(d.id_detalle) AS total,
                SUM(CASE WHEN d.fecha_devolucion IS NOT NULL THEN 1 ELSE 0 END)
                    AS devueltos,
                SUM(CASE WHEN d.fecha_devolucion IS NULL THEN 1 ELSE 0 END)
                    AS pendientes,
                SUM(
                    CASE
                        WHEN d.fecha_devolucion IS NULL AND b.estado = 'PERDIDO'
                        THEN 1 ELSE 0
                    END
                ) AS perdidos,
                MIN(
                    CASE WHEN d.fecha_devolucion IS NULL
                         THEN d.fecha_limite_devolucion END
                ) AS proximo_vencimiento
            FROM {ORIGEN_PRESTAMOS_CON_ESTADO} pr
            JOIN persona p ON p.dni = pr.dni_persona
            LEFT JOIN estudiante est ON est.dni = p.dni
            JOIN detalle_prestamo d ON d.id_prestamo = pr.id_prestamo
            JOIN bien_material b ON b.id_bien = d.id_bien
        """
        if condiciones:
            sql += " WHERE " + " AND ".join(condiciones)
        sql += " GROUP BY pr.id_prestamo,pr.dni_persona,pr.dni_encargado,pr.tipo_prestamo,pr.fecha_solicitud,pr.fecha_entrega,pr.observaciones,pr.estado,p.dni"
        if estado == "PENDIENTES":
            sql += " HAVING pendientes > 0"
        elif estado == "PERDIDOS":
            sql += " HAVING perdidos > 0"
        return sql, tuple(valores)

def hay_prestamos_vencidos(cursor, dnis):
    marcadores = ','.join(['%s'] * len(dnis))
    cursor.execute(f'''SELECT pr.id_prestamo FROM prestamo pr
        JOIN detalle_prestamo d ON d.id_prestamo=pr.id_prestamo
        WHERE d.fecha_devolucion IS NULL AND d.fecha_limite_devolucion < UTC_TIMESTAMP()
        AND (pr.dni_persona IN ({marcadores}) OR EXISTS (
            SELECT 1 FROM participante_prestamo pp WHERE pp.id_prestamo=pr.id_prestamo
            AND pp.dni_persona IN ({marcadores}))) LIMIT 1''', tuple(sorted(dnis))*2)
    return cursor.fetchone() is not None


class OperacionPrestamoSQL(IOperacionPrestamo):
    'Carga, bloquea y persiste con el cursor privado de una sola operacion.'

    def __init__(self, cursor):
        self._cursor = cursor

    def ahora(self):
        self._cursor.execute('SELECT UTC_TIMESTAMP() AS ahora')
        return self._cursor.fetchone()['ahora']

    def cargar_cuenta_ampliacion(self, id_usuario):
        self._cursor.execute('''SELECT u.dni_persona,u.rol,u.estado_cuenta,p.estado AS estado_persona
            FROM usuario_sistema u JOIN persona p ON p.dni=u.dni_persona
            WHERE u.id_usuario=%s''', (id_usuario,))
        cuenta = self._cursor.fetchone()
        if cuenta is not None:
            self._cursor.execute('SELECT permiso FROM rol_permiso WHERE rol=%s', (cuenta['rol'],))
            cuenta['permisos'] = {fila['permiso'] for fila in self._cursor.fetchall()}
        return cuenta

    def cargar_politica_ampliacion(self, id_politica):
        self._cursor.execute('''SELECT p.*,c.hora_apertura,c.hora_cierre FROM politica_prestamo p
            LEFT JOIN configuracion_general c ON c.id_configuracion=1
            WHERE p.id_politica=%s FOR UPDATE''', (id_politica,))
        fila = self._cursor.fetchone()
        if fila is None:
            return None, None
        horario = (HorarioAtencion(hora_apertura=fila['hora_apertura'], hora_cierre=fila['hora_cierre'])
                   if fila['hora_apertura'] is not None else None)
        return FabricaPoliticaPrestamo.construir(fila), horario

    def guardar_fecha_limite(self, id_detalle, anterior, nueva):
        self._cursor.execute('''UPDATE detalle_prestamo SET fecha_limite_devolucion=%s
            WHERE id_detalle=%s AND fecha_devolucion IS NULL AND fecha_limite_devolucion=%s''',
            (nueva, id_detalle, anterior))
        if self._cursor.rowcount != 1:
            raise ConflictoAmpliacionError('El plazo cambió. Recarga el préstamo.')

    def cargar_entrega(self, solicitud):
        c = self._cursor
        participantes = {solicitud.dni_persona, *(p.dni_persona for p in solicitud.participantes)}
        dnis = sorted(participantes | {solicitud.dni_encargado})
        marcadores = ','.join(['%s'] * len(dnis))
        c.execute(CONSULTA_PERSONAS+f' WHERE p.dni IN ({marcadores}) ORDER BY p.dni FOR UPDATE', tuple(dnis))
        personas = {p['dni']: p for p in c.fetchall()}
        vencidos = hay_prestamos_vencidos(c, participantes)
        sanciones = consultar_sanciones_activas(c, participantes)
        tipo = personas.get(solicitud.dni_persona, {}).get('tipo')
        c.execute('SELECT maximo_articulos FROM limite_articulos_prestamo WHERE tipo_persona=%s FOR UPDATE', (tipo,))
        fila = c.fetchone()
        limite = LimiteArticulosPrestamo(tipo_persona=tipo or 'ESTUDIANTE',
            maximo_articulos=fila['maximo_articulos'] if fila else None)
        c.execute('''SELECT COUNT(*) AS pendientes FROM detalle_prestamo d
            JOIN prestamo pr ON pr.id_prestamo=d.id_prestamo
            WHERE pr.dni_persona=%s AND d.fecha_devolucion IS NULL''', (solicitud.dni_persona,))
        pendientes = int(c.fetchone()['pendientes'])
        ids = tuple(sorted(solicitud.ids_bienes))
        m = ','.join(['%s']*len(ids))
        c.execute(f'''SELECT b.*,r.id_categoria FROM bien_material b JOIN recurso r ON r.id_recurso=b.id_recurso
            WHERE b.id_bien IN ({m}) ORDER BY b.id_bien FOR UPDATE''', ids)
        bienes = c.fetchall()
        c.execute(f'SELECT id_detalle FROM detalle_prestamo WHERE id_bien IN ({m}) AND fecha_devolucion IS NULL FOR UPDATE', ids)
        entregas = bool(c.fetchall())
        categorias = sorted({b['id_categoria'] for b in bienes})
        politicas = {}
        if categorias:
            m = ','.join(['%s']*len(categorias))
            c.execute('SELECT * FROM politica_prestamo WHERE vigente=TRUE AND tipo_persona=%s '
                +f'AND id_categoria IN ({m}) ORDER BY id_politica FOR UPDATE', (tipo, *categorias))
            politicas = {p['id_categoria']: FabricaPoliticaPrestamo.construir(p) for p in c.fetchall()}
        c.execute('SELECT hora_apertura,hora_cierre FROM configuracion_general WHERE id_configuracion=1 FOR UPDATE')
        fila = c.fetchone()
        horario = HorarioAtencion(**fila) if fila else None
        return ContextoEntrega(personas, vencidos, sanciones, limite, pendientes, bienes, entregas, politicas, horario, self.ahora())

    def guardar_entrega(self, prestamo, bienes, ahora):
        c = self._cursor
        c.execute('''INSERT INTO prestamo(dni_persona,dni_encargado,tipo_prestamo,fecha_solicitud,fecha_entrega,estado,observaciones)
            VALUES(%s,%s,%s,%s,%s,%s,%s)''', (prestamo.dni_persona, prestamo.dni_encargado,
            prestamo.tipo_prestamo.value, ahora, ahora, prestamo.estado.value, prestamo.observaciones))
        prestamo.id_prestamo = c.lastrowid
        self._guardar_detalles(c, prestamo.id_prestamo, bienes, prestamo.detalles, prestamo.dni_encargado)
        for participante in prestamo.participantes:
            c.execute('''INSERT INTO participante_prestamo(id_prestamo,dni_persona,rol_participacion,responsable)
                VALUES(%s,%s,%s,%s)''', (prestamo.id_prestamo, participante.dni_persona,
                participante.rol_participacion, participante.responsable))
        self._guardar_historial(c, prestamo.id_prestamo, None, prestamo.estado.value, 'Entrega registrada', prestamo.dni_encargado)
        prestamo.fecha_entrega = prestamo.fecha_solicitud = ahora
        return prestamo

    def cargar_recepcion(self, id_prestamo, dni_encargado):
        c = self._cursor
        c.execute('SELECT estado FROM persona WHERE dni=%s FOR UPDATE', (dni_encargado,))
        encargado = c.fetchone()
        c.execute('SELECT * FROM prestamo WHERE id_prestamo=%s FOR UPDATE', (id_prestamo,))
        fila = c.fetchone()
        if fila is None:
            raise LookupError('No se encontró el préstamo.')
        c.execute('''SELECT d.*,b.estado AS estado_actual FROM detalle_prestamo d
            JOIN bien_material b ON b.id_bien=d.id_bien WHERE d.id_prestamo=%s ORDER BY b.id_bien FOR UPDATE''', (id_prestamo,))
        detalles = c.fetchall()
        return encargado, self._construir_prestamo(fila, detalles), detalles, self.ahora()

    def registrar_sancion_vencimiento(self, detalle, ahora):
        return aplicar_sancion_vencimiento(self._cursor, detalle, ahora)

    def guardar_devoluciones(self, prestamo, anterior, devoluciones, detalles, dni_encargado, ahora):
        filas = {d['id_detalle']:d for d in detalles}
        for devolucion in devoluciones:
            self._registrar_devolucion_detalle(self._cursor, prestamo.id_prestamo, devolucion,
                filas[devolucion.id_detalle], ahora, dni_encargado)
        self.guardar_estado(prestamo, anterior, f'Recepción de {len(devoluciones)} bien(es)', dni_encargado)

    def guardar_perdida(self, prestamo, detalle, motivo, dni_encargado):
        self._cursor.execute("UPDATE bien_material SET estado='PERDIDO' WHERE id_bien=%s", (detalle.id_bien,))
        registrar_historial_bien(self._cursor, detalle.id_bien, 'PRESTADO', 'PERDIDO', motivo, dni_encargado)
        self._guardar_historial(self._cursor, prestamo.id_prestamo, prestamo.estado.value, prestamo.estado.value,
            'Pérdida reportada; el bien sigue pendiente de devolución', dni_encargado)

    def cargar_vencidos(self, dni=None):
        sql = '''SELECT pr.* FROM prestamo pr WHERE pr.estado IN ('ACTIVO','PARCIALMENTE_DEVUELTO')
            AND EXISTS(SELECT 1 FROM detalle_prestamo d WHERE d.id_prestamo=pr.id_prestamo
                AND d.fecha_devolucion IS NULL AND d.fecha_limite_devolucion<UTC_TIMESTAMP())'''
        valores = ()
        if dni is not None:
            sql+=''' AND (pr.dni_persona=%s OR EXISTS(SELECT 1 FROM participante_prestamo pp
                WHERE pp.id_prestamo=pr.id_prestamo AND pp.dni_persona=%s))'''
            valores = (dni, dni)
        self._cursor.execute(sql+' ORDER BY pr.id_prestamo FOR UPDATE', valores)
        filas = self._cursor.fetchall()
        prestamos = []
        for fila in filas:
            self._cursor.execute('SELECT * FROM detalle_prestamo WHERE id_prestamo=%s ORDER BY id_detalle FOR UPDATE', (fila['id_prestamo'],))
            prestamos.append(self._construir_prestamo(fila, self._cursor.fetchall()))
        return prestamos

    def guardar_estado(self, prestamo, anterior, observacion, dni_encargado):
        self._cursor.execute('UPDATE prestamo SET estado=%s WHERE id_prestamo=%s', (prestamo.estado.value, prestamo.id_prestamo))
        self._guardar_historial(self._cursor, prestamo.id_prestamo, anterior, prestamo.estado.value, observacion, dni_encargado)

    @staticmethod
    def _guardar_historial(cursor, id_prestamo, anterior, nuevo_estado, observacion, responsable):
        cursor.execute(
            """
            INSERT INTO historial_estado (
                entidad, id_entidad, estado_anterior, estado_nuevo, fecha,
                observacion, dni_responsable
            )
            VALUES ('PRESTAMO', %s, %s, %s, UTC_TIMESTAMP(), %s, %s)
            """,
            (id_prestamo, anterior, nuevo_estado, observacion, responsable),
        )

    @staticmethod
    def _construir_prestamo(fila, filas_detalles):
        prestamo = Prestamo(
            id_prestamo=fila["id_prestamo"],
            dni_persona=fila["dni_persona"],
            dni_encargado=fila["dni_encargado"],
            tipo_prestamo=fila["tipo_prestamo"],
            fecha_solicitud=fila["fecha_solicitud"],
            fecha_entrega=fila["fecha_entrega"],
            estado=fila["estado"],
            observaciones=fila["observaciones"],
        )
        for fila_detalle in filas_detalles:
            detalle = DetallePrestamo(
                id_detalle=fila_detalle["id_detalle"],
                id_bien=fila_detalle["id_bien"],
                id_politica=fila_detalle["id_politica"],
                fecha_limite_devolucion=fila_detalle["fecha_limite_devolucion"],
                condicion_entrega=fila_detalle["condicion_entrega"],
                condicion_devolucion=fila_detalle["condicion_devolucion"],
                observaciones_entrega=fila_detalle["observaciones_entrega"],
                fecha_devolucion=fila_detalle["fecha_devolucion"],
                dni_encargado_devolucion=fila_detalle["dni_encargado_devolucion"],
                observaciones_devolucion=fila_detalle["observaciones_devolucion"],
            )
            prestamo.detalles.append(detalle)
        return prestamo

    @staticmethod
    def _guardar_detalles(cursor, id_prestamo, bienes, detalles, dni_encargado):
        for bien, detalle in zip(bienes, detalles):
            cursor.execute(
                """
                INSERT INTO detalle_prestamo (
                    id_prestamo, id_bien, id_politica,
                    fecha_limite_devolucion, condicion_entrega, observaciones_entrega
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    id_prestamo, detalle.id_bien, detalle.id_politica,
                    detalle.fecha_limite_devolucion, detalle.condicion_entrega.value,
                    detalle.observaciones_entrega or None,
                ),
            )
            detalle.id_detalle = cursor.lastrowid
            cursor.execute(
                "UPDATE bien_material SET estado='PRESTADO' WHERE id_bien=%s",
                (bien["id_bien"],),
            )
            registrar_historial_bien(
                cursor, bien["id_bien"], bien["estado"], "PRESTADO",
                f"Entrega del préstamo #{id_prestamo}", dni_encargado,
            )
        return detalles

    @staticmethod
    def _registrar_devolucion_detalle(
        cursor, id_prestamo, devolucion, detalle, ahora, dni_encargado,
    ):
        estado = devolucion.estado_bien.value
        cursor.execute(
            "UPDATE detalle_prestamo SET fecha_devolucion=%s,dni_encargado_devolucion=%s,"
            "condicion_devolucion=%s,observaciones_devolucion=%s WHERE id_detalle=%s",
            (ahora, dni_encargado, devolucion.condicion_devolucion.value,
             devolucion.observaciones or None, detalle["id_detalle"]),
        )
        cursor.execute(
            "UPDATE bien_material SET estado=%s WHERE id_bien=%s",
            (estado, detalle["id_bien"]),
        )
        registrar_historial_bien(
            cursor,
            detalle["id_bien"],
            detalle["estado_actual"],
            estado,
            f"Recepción del préstamo #{id_prestamo}",
            dni_encargado,
        )
