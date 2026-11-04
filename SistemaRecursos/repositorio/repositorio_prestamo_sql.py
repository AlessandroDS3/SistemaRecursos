from __future__ import annotations
from dominio.gestion_prestamos.solicitud_prestamo import SolicitudPrestamo
from dominio.resultados_consulta import PrestamoDetalle, PrestamoListado, ResumenPrestamos
from repositorio.repositorio_bien_material_sql import registrar_historial_bien
from dominio.gestion_prestamos.i_repositorio_prestamo import IRepositorioPrestamo
from dominio.gestion_prestamos.validacion_prestamo import validar_persona, ConflictoPrestamoError
from dominio.gestion_prestamos.prestamo import Prestamo
from dominio.gestion_prestamos.detalle_prestamo import DetallePrestamo
from dominio.gestion_control.fabrica_politica_prestamo import FabricaPoliticaPrestamo
from repositorio.conexion_mysql import MySQLConnection
from repositorio.horario_atencion_sql import consultar_horario_atencion
from repositorio.sanciones_vencimiento_sql import aplicar_sancion_vencimiento
from repositorio.registro_fuera_servicio_sql import guardar_cambio_fuera_servicio
from dominio.gestion_recursos.bien_material import EstadoBienMaterial
from repositorio.repositorio_persona_sql import CONSULTA as CONSULTA_PERSONAS


# Estado actual para lecturas: no modifica préstamo ni historial.
ORIGEN_PRESTAMOS_CON_ESTADO = """
    (SELECT base.id_prestamo, base.dni_persona, base.dni_encargado,
            base.tipo_prestamo, base.fecha_solicitud, base.fecha_entrega, base.observaciones,
            CASE
              WHEN NOT EXISTS (SELECT 1 FROM detalle_prestamo estado_detalle
                WHERE estado_detalle.id_prestamo=base.id_prestamo
                  AND estado_detalle.estado_devolucion IS NULL) THEN 'DEVUELTO'
              WHEN EXISTS (SELECT 1 FROM detalle_prestamo estado_detalle
                WHERE estado_detalle.id_prestamo=base.id_prestamo
                  AND estado_detalle.estado_devolucion IS NULL
                  AND estado_detalle.fecha_limite_devolucion < UTC_TIMESTAMP()) THEN 'VENCIDO'
              WHEN EXISTS (SELECT 1 FROM detalle_prestamo estado_detalle
                WHERE estado_detalle.id_prestamo=base.id_prestamo
                  AND estado_detalle.estado_devolucion IS NOT NULL) THEN 'PARCIALMENTE_DEVUELTO'
              ELSE 'ACTIVO'
            END AS estado
     FROM prestamo base)
"""


class RepositorioPrestamoSQL(IRepositorioPrestamo):
    """Coordina las operaciones de préstamos y su historial en MySQL."""

    def __init__(self, conexion=None):
        self.conexion = conexion or MySQLConnection()

    @staticmethod
    def _validar_encargado(cursor, dni):
        cursor.execute(
            "SELECT estado FROM persona WHERE dni = %s FOR UPDATE",
            (dni,),
        )
        persona = cursor.fetchone()
        if not persona or persona["estado"] != "ACTIVA":
            raise ValueError("El encargado debe ser una persona activa.")

    @staticmethod
    def _guardar_historial(cursor, id_prestamo, anterior, nuevo_estado, observacion, responsable):
        cursor.execute(
            """
            INSERT INTO historial_prestamo (
                id_prestamo, estado_anterior, estado_nuevo, fecha,
                observacion, dni_responsable
            )
            VALUES (%s, %s, %s, UTC_TIMESTAMP(), %s, %s)
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
                id_bien_ref=fila_detalle["id_bien_ref"],
                id_politica_ref=fila_detalle["id_politica_ref"],
                fecha_limite_devolucion=fila_detalle["fecha_limite_devolucion"],
                estado_entrega=fila_detalle["estado_entrega"],
                estado_devolucion=fila_detalle["estado_devolucion"],
                observaciones=fila_detalle["observaciones"],
            )
            prestamo.detalles.append(detalle)
        return prestamo

    def registrar_prestamo(self, solicitud: SolicitudPrestamo, *, cursor=None, id_bien_reservado=None) -> Prestamo:
        """Entrada común de entrega directa y reserva; comparte la transacción del llamante."""
        if cursor is not None:
            return self._registrar_prestamo_con_cursor(cursor, solicitud, id_bien_reservado)
        with self.conexion.sesion(escritura=True) as cursor:
            return self._registrar_prestamo_con_cursor(cursor, solicitud, id_bien_reservado)

    def _registrar_prestamo_con_cursor(self, cursor, solicitud, id_bien_reservado):
        personas = self._validar_personas(cursor, solicitud)
        bienes = self._consultar_bienes_disponibles(cursor, solicitud, id_bien_reservado)
        tipo_persona = personas[solicitud.dni_persona]["tipo"]
        politicas = self._consultar_politicas(cursor, bienes, tipo_persona, solicitud.salida_solicitada)

        cursor.execute("SELECT UTC_TIMESTAMP() AS ahora")
        ahora = cursor.fetchone()["ahora"]
        horario = consultar_horario_atencion(cursor, bloquear=True)
        horario.cierre_para_entrega(ahora)
        prestamo = solicitud.construir_prestamo(bienes, politicas, ahora, horario)
        cursor.execute(
            """
            INSERT INTO prestamo (
                dni_persona, dni_encargado, tipo_prestamo,
                fecha_solicitud, fecha_entrega, estado, observaciones
            )
            VALUES (%s, %s, %s, %s, %s, 'ACTIVO', %s)
            """,
            (
                prestamo.dni_persona, prestamo.dni_encargado,
                prestamo.tipo_prestamo.value, ahora, ahora, prestamo.observaciones,
            ),
        )
        nuevo_id = cursor.lastrowid
        detalles = self._guardar_detalles(
            cursor, nuevo_id, bienes, prestamo.detalles, prestamo.dni_encargado
        )
        for participante in prestamo.participantes:
            cursor.execute(
                """
                INSERT INTO participante_prestamo (
                    id_prestamo, dni_persona, rol_participacion, responsable
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    nuevo_id, participante.dni_persona,
                    participante.rol_participacion, participante.responsable,
                ),
            )
        self._guardar_historial(
            cursor, nuevo_id, None, "ACTIVO", "Entrega registrada", prestamo.dni_encargado
        )
        prestamo.id_prestamo = nuevo_id
        prestamo.fecha_solicitud = ahora
        prestamo.fecha_entrega = ahora
        prestamo.detalles = detalles
        return prestamo

    @staticmethod
    def validar_sin_prestamos_vencidos(cursor, dnis):
        marcadores = ",".join(["%s"] * len(dnis))
        cursor.execute(
            f"""SELECT pr.id_prestamo FROM prestamo pr
                JOIN detalle_prestamo d ON d.id_prestamo = pr.id_prestamo
                WHERE d.estado_devolucion IS NULL
                  AND d.fecha_limite_devolucion < UTC_TIMESTAMP()
                  AND (pr.dni_persona IN ({marcadores}) OR EXISTS (
                      SELECT 1 FROM participante_prestamo pp
                      WHERE pp.id_prestamo = pr.id_prestamo
                        AND pp.dni_persona IN ({marcadores})
                  )) LIMIT 1""",
            tuple(sorted(dnis)) * 2,
        )
        if cursor.fetchone():
            raise ConflictoPrestamoError(
                "La persona tiene un préstamo vencido pendiente de devolución."
            )

    @staticmethod
    def _validar_personas(cursor, solicitud):
        dnis_participantes = {solicitud.dni_persona}
        for participante in solicitud.participantes:
            dnis_participantes.add(participante.dni_persona)
        dnis_personas = set(dnis_participantes)
        dnis_personas.add(solicitud.dni_encargado)
        # Los bloqueos se toman siempre en el mismo orden.
        dnis_personas = sorted(dnis_personas)
        marcadores = ",".join(["%s"] * len(dnis_personas))
        cursor.execute(
            CONSULTA_PERSONAS
            + f" WHERE p.dni IN ({marcadores}) ORDER BY p.dni FOR UPDATE",
            tuple(dnis_personas),
        )
        personas = {}
        for fila_persona in cursor.fetchall():
            personas[fila_persona["dni"]] = fila_persona
        if len(personas) != len(dnis_personas):
            raise ValueError("Una de las personas seleccionadas ya no existe.")
        if personas[solicitud.dni_encargado]["estado"] != "ACTIVA":
            raise ValueError("El encargado está inactivo.")
        for dni in dnis_participantes:
            validar_persona(personas[dni])

        RepositorioPrestamoSQL.validar_sin_prestamos_vencidos(cursor, dnis_participantes)

        marcadores = ",".join(["%s"] * len(dnis_participantes))
        cursor.execute(
            f"""
            SELECT id_sancion
            FROM sancion
            WHERE dni_persona IN ({marcadores})
              AND estado = 'ACTIVA'
            FOR UPDATE
            """,
            tuple(sorted(dnis_participantes)),
        )
        if cursor.fetchall():
            raise ConflictoPrestamoError(
                "El solicitante o un participante tiene una sanción activa."
            )
        return personas

    @staticmethod
    def _consultar_bienes_disponibles(cursor, solicitud, id_bien_reservado):
        ids_bienes = sorted(solicitud.ids_bienes)
        marcadores = ",".join(["%s"] * len(ids_bienes))
        cursor.execute(
            f"""
            SELECT b.*, r.id_recurso AS recurso_id, r.id_categoria_ref
            FROM bien_material b
            JOIN recurso r ON r.id_recurso = b.id_recurso_ref
            WHERE b.id_bien IN ({marcadores})
            ORDER BY b.id_bien
            FOR UPDATE
            """,
            tuple(ids_bienes),
        )
        bienes = cursor.fetchall()
        if len(bienes) != len(ids_bienes):
            raise ValueError("Uno de los bienes seleccionados ya no existe.")
        for bien in bienes:
            estado_esperado = "DISPONIBLE"
            if bien["id_bien"] == id_bien_reservado:
                estado_esperado = "RESERVADO"
            if bien["estado"] != estado_esperado:
                raise ConflictoPrestamoError(
                    "Uno de los bienes dejó de estar disponible. No se registró la entrega."
                )
        cursor.execute(
            f"""
            SELECT id_detalle
            FROM detalle_prestamo
            WHERE id_bien_ref IN ({marcadores})
              AND estado_devolucion IS NULL
            FOR UPDATE
            """,
            tuple(ids_bienes),
        )
        if cursor.fetchall():
            raise ConflictoPrestamoError(
                "Uno de los bienes tiene una entrega pendiente, aunque su inventario indique disponible. Revisa su préstamo antes de una nueva entrega."
            )
        return bienes

    @staticmethod
    def _consultar_politicas(cursor, bienes, tipo_persona, salida_solicitada):
        ids_categorias = set()
        for bien in bienes:
            ids_categorias.add(bien["id_categoria_ref"])
        ids_categorias = sorted(ids_categorias)
        marcadores = ",".join(["%s"] * len(ids_categorias))
        cursor.execute(
            "SELECT * FROM politica_prestamo WHERE vigente=TRUE AND tipo_persona=%s AND id_categoria_ref IN ("
            + marcadores + ") ORDER BY id_politica FOR UPDATE",
            (tipo_persona, *ids_categorias),
        )
        politicas = {}
        for fila_politica in cursor.fetchall():
            politica = FabricaPoliticaPrestamo.construir(fila_politica)
            politicas[fila_politica["id_categoria_ref"]] = politica
        if set(ids_categorias) != set(politicas):
            raise ValueError(
                "Falta una política para el tipo de persona y una de las categorías seleccionadas."
            )
        if salida_solicitada:
            for politica in politicas.values():
                if not politica.permite_salida:
                    raise ValueError("Una de las políticas no permite sacar el bien de la institución.")
        return politicas

    @staticmethod
    def _guardar_detalles(cursor, id_prestamo, bienes, detalles, dni_encargado):
        for bien, detalle in zip(bienes, detalles):
            cursor.execute(
                """
                INSERT INTO detalle_prestamo (
                    id_prestamo, id_bien_ref, id_politica_ref,
                    fecha_limite_devolucion, estado_entrega, observaciones
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    id_prestamo, detalle.id_bien_ref, detalle.id_politica_ref,
                    detalle.fecha_limite_devolucion, detalle.estado_entrega.value, "",
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
                    dev.fecha AS fecha_devolucion,
                    dev.observaciones AS observaciones_devolucion,
                    CASE WHEN s.id_sancion IS NOT NULL THEN s.estado
                         WHEN d.fecha_limite_devolucion < COALESCE(dev.fecha,UTC_TIMESTAMP()) THEN 'ACTIVA'
                         ELSE NULL END AS estado_sancion_vencimiento,
                    s.justificacion_levantamiento,
                    CONCAT(e.nombres, ' ', e.apellidos) AS encargado_devolucion
                FROM detalle_prestamo d
                JOIN bien_material b ON b.id_bien = d.id_bien_ref
                JOIN recurso r ON r.id_recurso = b.id_recurso_ref
                LEFT JOIN devolucion dev ON dev.id_detalle_ref = d.id_detalle
                LEFT JOIN sancion s ON s.id_detalle_vencido_ref=d.id_detalle
                LEFT JOIN persona e ON e.dni = dev.dni_encargado
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
                FROM historial_prestamo h
                JOIN persona p ON p.dni = h.dni_responsable
                WHERE h.id_prestamo = %s
                ORDER BY h.fecha DESC, h.id_historial DESC
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
            WHERE d.estado_devolucion IS NULL
              AND pr.estado IN ('ACTIVO', 'VENCIDO', 'PARCIALMENTE_DEVUELTO')
        """ + condicion_persona

        consulta_vencidos = f"""
            SELECT COUNT(DISTINCT pr.id_prestamo) AS cantidad
            FROM {ORIGEN_PRESTAMOS_CON_ESTADO} pr
            JOIN detalle_prestamo d ON d.id_prestamo = pr.id_prestamo
            WHERE d.estado_devolucion IS NULL
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
                SUM(CASE WHEN d.estado_devolucion IS NOT NULL THEN 1 ELSE 0 END)
                    AS devueltos,
                SUM(CASE WHEN d.estado_devolucion IS NULL THEN 1 ELSE 0 END)
                    AS pendientes,
                SUM(
                    CASE
                        WHEN d.estado_devolucion IS NULL AND b.estado = 'PERDIDO'
                        THEN 1 ELSE 0
                    END
                ) AS perdidos,
                MIN(
                    CASE WHEN d.estado_devolucion IS NULL
                         THEN d.fecha_limite_devolucion END
                ) AS proximo_vencimiento
            FROM {ORIGEN_PRESTAMOS_CON_ESTADO} pr
            JOIN persona p ON p.dni = pr.dni_persona
            LEFT JOIN estudiante est ON est.dni = p.dni
            JOIN detalle_prestamo d ON d.id_prestamo = pr.id_prestamo
            JOIN bien_material b ON b.id_bien = d.id_bien_ref
        """
        if condiciones:
            sql += " WHERE " + " AND ".join(condiciones)
        sql += " GROUP BY pr.id_prestamo,pr.dni_persona,pr.dni_encargado,pr.tipo_prestamo,pr.fecha_solicitud,pr.fecha_entrega,pr.observaciones,pr.estado,p.dni"
        if estado == "PENDIENTES":
            sql += " HAVING pendientes > 0"
        elif estado == "PERDIDOS":
            sql += " HAVING perdidos > 0"
        return sql, tuple(valores)

    def actualizar_prestamos_vencidos(self, dni_responsable, dni=None) -> None:
        with self.conexion.sesion(escritura=True) as cursor:
            sql = """
                SELECT pr.*
                FROM prestamo pr
                WHERE pr.estado IN ('ACTIVO', 'PARCIALMENTE_DEVUELTO')
                  AND EXISTS (
                      SELECT 1
                      FROM detalle_prestamo d
                      WHERE d.id_prestamo = pr.id_prestamo
                        AND d.estado_devolucion IS NULL
                        AND d.fecha_limite_devolucion < UTC_TIMESTAMP()
                  )
            """
            valores = []
            if dni is not None:
                sql += """
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
                valores.extend((dni, dni))
            cursor.execute(sql + " ORDER BY pr.id_prestamo FOR UPDATE", tuple(valores))
            filas = cursor.fetchall()
            for fila in filas:
                cursor.execute(
                    "SELECT * FROM detalle_prestamo WHERE id_prestamo=%s ORDER BY id_detalle FOR UPDATE",
                    (fila["id_prestamo"],),
                )
                prestamo = self._construir_prestamo(fila, cursor.fetchall())
                nuevo_estado = prestamo.estado_actual().value
                if nuevo_estado != fila["estado"]:
                    cursor.execute(
                        "UPDATE prestamo SET estado=%s WHERE id_prestamo=%s",
                        (nuevo_estado, fila["id_prestamo"]),
                    )
                    self._guardar_historial(
                        cursor,
                        fila["id_prestamo"],
                        fila["estado"],
                        nuevo_estado,
                        "Vencimiento registrado por el encargado",
                        dni_responsable,
                    )

    @staticmethod
    def _registrar_devolucion_detalle(
        cursor, id_prestamo, devolucion, detalle, ahora, dni_encargado,
    ):
        estado = devolucion.estado_devolucion
        cursor.execute(
            """
            INSERT INTO devolucion (
                id_detalle_ref, dni_encargado, fecha, observaciones
            )
            VALUES (%s, %s, %s, %s)
            """,
            (detalle["id_detalle"], dni_encargado, ahora, devolucion.observaciones),
        )
        cursor.execute(
            "UPDATE detalle_prestamo SET estado_devolucion=%s WHERE id_detalle=%s",
            (estado, detalle["id_detalle"]),
        )
        cursor.execute(
            "UPDATE bien_material SET estado=%s WHERE id_bien=%s",
            (estado, detalle["id_bien_ref"]),
        )
        guardar_cambio_fuera_servicio(
            cursor, detalle["id_bien_ref"], estado,
            f"Devolución del préstamo #{id_prestamo}", ahora,
            descripcion=devolucion.observaciones,
        )
        registrar_historial_bien(
            cursor,
            detalle["id_bien_ref"],
            detalle["estado_actual"],
            estado,
            f"Recepción del préstamo #{id_prestamo}",
            dni_encargado,
        )

    def registrar_devolucion(self, id_prestamo, devoluciones, dni_encargado) -> None:
        if not devoluciones or len({detalle.id_detalle_ref for detalle in devoluciones}) != len(devoluciones):
            raise ValueError("Selecciona bienes distintos para registrar la devolución.")
        with self.conexion.sesion(escritura=True) as cursor:
            self._validar_encargado(cursor, dni_encargado)
            cursor.execute("SELECT * FROM prestamo WHERE id_prestamo=%s FOR UPDATE", (id_prestamo,))
            fila = cursor.fetchone()
            if not fila:
                raise LookupError("No se encontró el préstamo.")
            cursor.execute(
                """
                SELECT d.*, b.estado AS estado_actual
                FROM detalle_prestamo d
                JOIN bien_material b ON b.id_bien = d.id_bien_ref
                WHERE d.id_prestamo = %s
                ORDER BY b.id_bien
                FOR UPDATE
                """,
                (id_prestamo,),
            )
            detalles = cursor.fetchall()
            detalles_por_id = {}
            for detalle in detalles:
                detalles_por_id[detalle["id_detalle"]] = detalle
            for devolucion in devoluciones:
                detalle = detalles_por_id.get(devolucion.id_detalle_ref)
                if not detalle or detalle["estado_devolucion"] is not None:
                    raise ConflictoPrestamoError(
                        "Uno de los bienes no pertenece a este préstamo o ya fue devuelto. No se registró ninguna devolución."
                    )
                if detalle["estado_actual"] not in {"PRESTADO", "PERDIDO"}:
                    raise ConflictoPrestamoError(
                        "El estado actual de un bien no corresponde a un préstamo pendiente."
                    )
            cursor.execute("SELECT UTC_TIMESTAMP() AS ahora")
            ahora = cursor.fetchone()["ahora"]
            prestamo = self._construir_prestamo(fila, detalles)
            for devolucion in devoluciones:
                detalle = detalles_por_id[devolucion.id_detalle_ref]
                aplicar_sancion_vencimiento(cursor, detalle, fila['dni_persona'], ahora)
                estado = devolucion.estado_devolucion
                prestamo.registrar_devolucion(detalle["id_detalle"], estado, ahora)
                self._registrar_devolucion_detalle(
                    cursor, id_prestamo, devolucion, detalle, ahora, dni_encargado
                )
            nuevo_estado = prestamo.estado_actual(ahora).value
            cursor.execute("UPDATE prestamo SET estado=%s WHERE id_prestamo=%s", (nuevo_estado, id_prestamo))
            self._guardar_historial(
                cursor,
                id_prestamo,
                fila["estado"],
                nuevo_estado,
                f"Recepción de {len(devoluciones)} bien(es)",
                dni_encargado,
            )

    def reportar_perdida(self, id_prestamo, id_detalle, motivo, dni_encargado) -> None:
        with self.conexion.sesion(escritura=True) as cursor:
            self._validar_encargado(cursor, dni_encargado)
            cursor.execute("SELECT * FROM prestamo WHERE id_prestamo=%s FOR UPDATE", (id_prestamo,))
            prestamo = cursor.fetchone()
            if not prestamo:
                raise LookupError("No se encontró el préstamo.")
            cursor.execute(
                """
                SELECT d.*, b.estado AS estado_actual
                FROM detalle_prestamo d
                JOIN bien_material b ON b.id_bien = d.id_bien_ref
                WHERE d.id_detalle = %s AND d.id_prestamo = %s
                FOR UPDATE
                """,
                (id_detalle, id_prestamo),
            )
            detalle = cursor.fetchone()
            if (
                not detalle
                or detalle["estado_devolucion"] is not None
                or detalle["estado_actual"] != "PRESTADO"
            ):
                raise ConflictoPrestamoError(
                    "Solo se puede reportar la pérdida de un bien prestado y pendiente de devolución."
                )
            cursor.execute(
                "UPDATE bien_material SET estado='PERDIDO' WHERE id_bien=%s",
                (detalle["id_bien_ref"],),
            )
            cursor.execute("SELECT UTC_TIMESTAMP() AS ahora")
            ahora = cursor.fetchone()["ahora"]
            guardar_cambio_fuera_servicio(
                cursor, detalle["id_bien_ref"], EstadoBienMaterial.PERDIDO,
                f"Pérdida durante el préstamo #{id_prestamo}", ahora, descripcion=motivo,
            )
            registrar_historial_bien(
                cursor, detalle["id_bien_ref"], "PRESTADO", "PERDIDO", motivo, dni_encargado
            )
            self._guardar_historial(
                cursor,
                id_prestamo,
                prestamo["estado"],
                prestamo["estado"],
                "Pérdida reportada; el bien sigue pendiente de devolución",
                dni_encargado,
            )
