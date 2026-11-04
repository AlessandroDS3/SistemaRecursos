from __future__ import annotations
from dominio.resultados_consulta import ReservaDetalle, ResultadoReservas
from dominio.gestion_prestamos.i_repositorio_reserva import IRepositorioReserva
from dominio.gestion_prestamos.reserva import Reserva, autorizar_resolucion, AccionReserva
from dominio.gestion_prestamos.validacion_prestamo import ConflictoPrestamoError
from dominio.gestion_control.fabrica_politica_prestamo import FabricaPoliticaPrestamo
from repositorio.conexion_mysql import MySQLConnection
from repositorio.repositorio_persona_sql import CONSULTA as CONSULTA_PERSONAS
from repositorio.repositorio_prestamo_sql import RepositorioPrestamoSQL
from repositorio.repositorio_bien_material_sql import registrar_historial_bien
from repositorio.politica_vencimiento_reserva_sql import consultar_politica_vencimiento_reserva


CONSULTA_RESERVA = """
    SELECT re.*,
           CONCAT(p.nombres, ' ', p.apellidos) AS solicitante,
           p.dni AS documento_identidad,
           CASE
               WHEN e.dni IS NOT NULL THEN 'ESTUDIANTE'
               WHEN d.dni IS NOT NULL THEN 'DOCENTE'
               WHEN a.dni IS NOT NULL THEN 'ADMINISTRATIVO'
           END AS tipo_persona,
           r.nombre AS recurso,
           r.id_recurso AS recurso_id,
           b.codigo_inventario
    FROM reserva re
    JOIN persona p ON p.dni = re.dni_persona
    JOIN recurso r ON r.id_recurso = re.id_recurso_ref
    LEFT JOIN bien_material b ON b.id_bien = re.id_bien_ref
    LEFT JOIN estudiante e ON e.dni = p.dni
    LEFT JOIN docente d ON d.dni = p.dni
    LEFT JOIN administrativo a ON a.dni = p.dni
"""

class RepositorioReservaSQL(IRepositorioReserva):
    def __init__(self, conexion=None, prestamos=None):
        self.conexion = conexion or MySQLConnection()
        self.prestamos = prestamos if prestamos is not None else RepositorioPrestamoSQL(self.conexion)

    def registrar_reserva(self, reserva, responsable) -> int:
        with self.conexion.sesion(escritura=True) as cursor:
            self._validar_elegibilidad(cursor, reserva)
            self._verificar_solicitud_duplicada(cursor, reserva)
            politica_vencimiento = consultar_politica_vencimiento_reserva(cursor, bloquear=True)
            id_reserva = self._insertar_reserva(cursor, reserva, politica_vencimiento)
            self._guardar_historial(
                cursor, id_reserva, None, reserva.estado.value,
                "Solicitud registrada", responsable,
            )
        return id_reserva

    def preparar_reserva(self, id_reserva, responsable, gestionar, motivo="", acepta=False) -> int | None:
        return self._resolver_reserva(id_reserva, AccionReserva.PREPARAR, responsable, gestionar, motivo, acepta)

    def entregar_reserva(self, id_reserva, responsable, gestionar, motivo="", acepta=False) -> int | None:
        return self._resolver_reserva(id_reserva, AccionReserva.ENTREGAR, responsable, gestionar, motivo, acepta)

    def cancelar_reserva(self, id_reserva, responsable, gestionar, motivo="", acepta=False) -> int | None:
        return self._resolver_reserva(id_reserva, AccionReserva.CANCELAR, responsable, gestionar, motivo, acepta)

    def rechazar_reserva(self, id_reserva, responsable, gestionar, motivo="", acepta=False) -> int | None:
        return self._resolver_reserva(id_reserva, AccionReserva.RECHAZAR, responsable, gestionar, motivo, acepta)

    def expirar_reserva(self, id_reserva, responsable, gestionar, motivo="", acepta=False) -> int | None:
        return self._resolver_reserva(id_reserva, AccionReserva.EXPIRAR, responsable, gestionar, motivo, acepta)

    def _resolver_reserva(self, id_reserva, accion, responsable, gestionar, motivo="", acepta=False):
        accion = AccionReserva.desde_valor(accion)
        with self.conexion.sesion(escritura=True) as cursor:
            reserva = self._bloquear_reserva(cursor, id_reserva, accion, responsable, gestionar)
            estado_anterior = reserva.estado.value
            if accion in (AccionReserva.PREPARAR, AccionReserva.ENTREGAR):
                cursor.execute("SELECT UTC_TIMESTAMP() AS ahora")
                ahora = cursor.fetchone()["ahora"]
                if reserva.fecha_limite_vencimiento and ahora >= reserva.fecha_limite_vencimiento:
                    raise ConflictoPrestamoError("El plazo de retiro venció. La solicitud será expirada y el bien liberado por el sistema.")
            reserva.resolver_reserva(accion, responsable, gestionar, motivo, acepta)
            id_prestamo = None
            if accion == AccionReserva.PREPARAR:
                self._preparar_bien(cursor, reserva, responsable)
            elif accion == AccionReserva.ENTREGAR:
                id_prestamo = self._entregar_bien(cursor, reserva, responsable)
            else:
                self._liberar_bien(cursor, reserva, responsable)
            self._guardar_resolucion(
                cursor, reserva, estado_anterior, motivo or accion.observacion, responsable,
            )
        return id_prestamo

    @staticmethod
    def _desde_fila(fila):
        return Reserva(
            id_reserva=fila["id_reserva"],
            dni_persona=fila["dni_persona"],
            id_recurso_ref=fila["id_recurso_ref"],
            fecha_requerida=fila["fecha_requerida"],
            tipo_gestion=fila["tipo_gestion"],
            estado=fila["estado"],
            observaciones=fila["observaciones"],
            salida_solicitada=fila["salida_solicitada"],
            id_bien_ref=fila["id_bien_ref"],
            fecha_limite_vencimiento=fila.get("fecha_limite_vencimiento"),
        )

    def _bloquear_reserva(self, cursor, id_reserva, accion, dni_responsable, gestionar):
        cursor.execute(
            "SELECT dni_persona,id_recurso_ref FROM reserva WHERE id_reserva=%s",
            (id_reserva,),
        )
        referencia = cursor.fetchone()
        if not referencia:
            raise LookupError("No se encontró la solicitud o reserva.")
        autorizar_resolucion(referencia["dni_persona"], accion, dni_responsable, gestionar)
        # Mantener este orden evita invertir bloqueos con las entregas simultáneas.
        self._bloquear_personas(cursor, referencia["dni_persona"], dni_responsable)
        self._consultar_recurso_bloqueado(cursor, referencia["id_recurso_ref"])
        cursor.execute("SELECT * FROM reserva WHERE id_reserva=%s FOR UPDATE", (id_reserva,))
        fila = cursor.fetchone()
        if not fila:
            raise LookupError("No se encontró la solicitud o reserva.")
        return self._desde_fila(fila)

    @staticmethod
    def _bloquear_personas(cursor, dni_solicitante, dni_responsable):
        personas = sorted({dni_solicitante, dni_responsable})
        marcadores = ",".join(["%s"] * len(personas))
        cursor.execute(
            "SELECT dni FROM persona WHERE dni IN (" + marcadores
            + ") ORDER BY dni FOR UPDATE", tuple(personas),
        )
        cursor.fetchall()

    @staticmethod
    def _consultar_recurso_bloqueado(cursor, id_recurso):
        cursor.execute("SELECT * FROM recurso WHERE id_recurso=%s FOR UPDATE", (id_recurso,))
        recurso = cursor.fetchone()
        if not recurso:
            raise LookupError("No se encontró el recurso.")
        return recurso

    @staticmethod
    def _consultar_solicitante(cursor, dni):
        cursor.execute(CONSULTA_PERSONAS + " WHERE p.dni=%s FOR UPDATE", (dni,))
        persona = cursor.fetchone()
        cursor.execute(
            "SELECT id_sancion FROM sancion WHERE dni_persona=%s AND estado='ACTIVA' FOR UPDATE",
            (dni,),
        )
        return persona, bool(cursor.fetchall())

    @staticmethod
    def _consultar_politica(cursor, tipo_persona, id_categoria_ref):
        cursor.execute(
            "SELECT * FROM politica_prestamo WHERE vigente=TRUE AND tipo_persona=%s AND id_categoria_ref=%s FOR UPDATE",
            (tipo_persona, id_categoria_ref),
        )
        fila = cursor.fetchone()
        return FabricaPoliticaPrestamo.construir(fila) if fila else None

    def _validar_elegibilidad(self, cursor, reserva):
        persona, tiene_sancion = self._consultar_solicitante(cursor, reserva.dni_persona)
        reserva.validar_solicitante(persona, tiene_sancion)
        self.prestamos.validar_sin_prestamos_vencidos(cursor, {reserva.dni_persona})
        recurso = self._consultar_recurso_bloqueado(cursor, reserva.id_recurso_ref)
        politica = self._consultar_politica(cursor, persona["tipo"], recurso["id_categoria_ref"])
        reserva.validar_politica(politica)
        return politica

    def _condiciones_de_retiro(self, cursor, reserva):
        politica = self._validar_elegibilidad(cursor, reserva)
        cursor.execute("SELECT UTC_TIMESTAMP() AS ahora")
        ahora = cursor.fetchone()["ahora"]
        reserva.validar_fecha_retiro(ahora)
        return politica, ahora

    @staticmethod
    def _verificar_solicitud_duplicada(cursor, reserva):
        cursor.execute(
            """SELECT id_reserva FROM reserva
               WHERE dni_persona=%s AND id_recurso_ref=%s
                 AND estado IN ('EN_ESPERA','LISTA_PARA_RETIRO')
                 AND (fecha_limite_vencimiento IS NULL OR fecha_limite_vencimiento>UTC_TIMESTAMP()) FOR UPDATE""",
            (reserva.dni_persona, reserva.id_recurso_ref),
        )
        if cursor.fetchall():
            raise ConflictoPrestamoError("Ya tienes una solicitud o reserva pendiente para este recurso.")

    @staticmethod
    def _insertar_reserva(cursor, reserva, politica_vencimiento):
        cursor.execute(
            "SELECT COALESCE(MAX(posicion_en_cola),0)+1 AS posicion FROM reserva WHERE id_recurso_ref=%s",
            (reserva.id_recurso_ref,),
        )
        posicion = cursor.fetchone()["posicion"]
        cursor.execute(
            """INSERT INTO reserva
               (dni_persona,id_recurso_ref,fecha_solicitud,fecha_requerida,posicion_en_cola,
                estado,tipo_gestion,observaciones,salida_solicitada,fecha_limite_vencimiento)
               VALUES (%s,%s,UTC_TIMESTAMP(),%s,%s,%s,%s,%s,%s,%s)""",
            (reserva.dni_persona, reserva.id_recurso_ref, reserva.fecha_requerida,
             posicion, reserva.estado.value, reserva.tipo_gestion.value,
             reserva.observaciones, reserva.salida_solicitada,
             politica_vencimiento.vencimiento_espera(reserva.fecha_requerida)),
        )
        return cursor.lastrowid

    @staticmethod
    def _primera_solicitud_disponible(cursor, id_recurso):
        cursor.execute(
            """SELECT id_reserva FROM reserva
               WHERE id_recurso_ref=%s AND estado='EN_ESPERA'
                 AND fecha_requerida<=UTC_TIMESTAMP()
                 AND (fecha_limite_vencimiento IS NULL OR fecha_limite_vencimiento>UTC_TIMESTAMP())
               ORDER BY fecha_solicitud,id_reserva LIMIT 1 FOR UPDATE""",
            (id_recurso,),
        )
        primera = cursor.fetchone()
        return primera["id_reserva"] if primera else None

    @staticmethod
    def _consultar_bien_disponible(cursor, id_recurso):
        cursor.execute(
            """SELECT b.id_bien FROM bien_material b
               WHERE b.id_recurso_ref=%s AND b.estado='DISPONIBLE'
                 AND NOT EXISTS (SELECT 1 FROM detalle_prestamo d
                   WHERE d.id_bien_ref=b.id_bien AND d.estado_devolucion IS NULL)
               ORDER BY b.id_bien LIMIT 1 FOR UPDATE""",
            (id_recurso,),
        )
        bien = cursor.fetchone()
        if not bien:
            raise ConflictoPrestamoError("No hay un bien disponible. La solicitud sigue en espera.")
        return bien["id_bien"]

    def _preparar_bien(self, cursor, reserva, dni_responsable):
        _, ahora = self._condiciones_de_retiro(cursor, reserva)
        politica_vencimiento = consultar_politica_vencimiento_reserva(cursor, bloquear=True)
        id_primera_reserva = self._primera_solicitud_disponible(cursor, reserva.id_recurso_ref)
        reserva.validar_turno(id_primera_reserva)
        id_bien = self._consultar_bien_disponible(cursor, reserva.id_recurso_ref)
        cursor.execute("UPDATE bien_material SET estado='RESERVADO' WHERE id_bien=%s", (id_bien,))
        cursor.execute(
            "UPDATE reserva SET id_bien_ref=%s, fecha_preparacion=%s, fecha_limite_vencimiento=%s WHERE id_reserva=%s",
            (id_bien, ahora, politica_vencimiento.vencimiento_retiro(ahora), reserva.id_reserva),
        )
        registrar_historial_bien(
            cursor, id_bien, "DISPONIBLE", "RESERVADO",
            f"Preparado para solicitud #{reserva.id_reserva}", dni_responsable,
        )

    def _entregar_bien(self, cursor, reserva, dni_responsable):
        cursor.execute("SELECT UTC_TIMESTAMP() AS ahora")
        reserva.validar_fecha_retiro(cursor.fetchone()["ahora"])
        solicitud = reserva.preparar_solicitud_prestamo(dni_responsable)
        prestamo = self.prestamos.registrar_prestamo(solicitud, cursor=cursor, id_bien_reservado=reserva.id_bien_ref)
        cursor.execute(
            "UPDATE reserva SET id_prestamo_ref=%s WHERE id_reserva=%s",
            (prestamo.id_prestamo, reserva.id_reserva),
        )
        return prestamo.id_prestamo

    @staticmethod
    def _liberar_bien(cursor, reserva, dni_responsable):
        if reserva.id_bien_ref is None:
            return
        cursor.execute(
            "SELECT estado FROM bien_material WHERE id_bien=%s FOR UPDATE", (reserva.id_bien_ref,),
        )
        bien = cursor.fetchone()
        if not bien or bien["estado"] != "RESERVADO":
            raise ConflictoPrestamoError("El estado del bien cambió; revisa el inventario.")
        cursor.execute(
            "UPDATE bien_material SET estado='DISPONIBLE' WHERE id_bien=%s", (reserva.id_bien_ref,),
        )
        registrar_historial_bien(
            cursor, reserva.id_bien_ref, "RESERVADO", "DISPONIBLE",
            f"Solicitud #{reserva.id_reserva}: {reserva.estado.value}", dni_responsable,
        )
        cursor.execute("UPDATE reserva SET id_bien_ref=NULL WHERE id_reserva=%s", (reserva.id_reserva,))

    def _guardar_resolucion(self, cursor, reserva, estado_anterior, motivo, dni_responsable):
        cursor.execute(
            "UPDATE reserva SET estado=%s WHERE id_reserva=%s", (reserva.estado.value, reserva.id_reserva),
        )
        self._guardar_historial(
            cursor, reserva.id_reserva, estado_anterior, reserva.estado.value, motivo, dni_responsable,
        )

    @staticmethod
    def _guardar_historial(cursor, id_reserva, anterior, nuevo, motivo, dni_responsable):
        cursor.execute(
            """INSERT INTO historial_estado
               (entidad,id_entidad,estado_anterior,estado_nuevo,fecha,observacion,dni_responsable)
               VALUES ('RESERVA',%s,%s,%s,UTC_TIMESTAMP(),%s,%s)""",
            (id_reserva, anterior, nuevo, motivo, dni_responsable),
        )

    def consultar_reserva(self, id_reserva) -> ReservaDetalle | None:
        with self.conexion.sesion() as cursor:
            cursor.execute(CONSULTA_RESERVA + " WHERE re.id_reserva=%s", (id_reserva,))
            fila = cursor.fetchone()
            if fila:
                cursor.execute(
                    """SELECT h.*, CONCAT(p.nombres,' ',p.apellidos) AS responsable
                       FROM historial_estado h LEFT JOIN persona p ON p.dni=h.dni_responsable
                       WHERE h.entidad='RESERVA' AND h.id_entidad=%s
                       ORDER BY h.fecha,h.id_historial_estado""", (id_reserva,),
                )
                fila["historial"] = cursor.fetchall()
            return fila

    def consultar_reservas(self, filtros, dni) -> ResultadoReservas:
        condiciones, valores = [], []
        if dni is not None:
            condiciones.append("re.dni_persona=%s")
            valores.append(dni)
        if filtros.get("tipo"):
            condiciones.append("re.tipo_gestion = %s")
            valores.append(filtros["tipo"])
        if filtros.get("estado"):
            condiciones.append("re.estado = %s")
            valores.append(filtros["estado"])
        if filtros.get("q"):
            condiciones.append(
                "(r.nombre LIKE %s OR p.apellidos LIKE %s OR p.dni LIKE %s OR e.cui LIKE %s)"
            )
            valores.extend(["%" + filtros["q"] + "%"] * 4)
        where = " WHERE " + " AND ".join(condiciones) if condiciones else ""
        with self.conexion.sesion() as cursor:
            cursor.execute(
                CONSULTA_RESERVA + where + " ORDER BY re.fecha_solicitud,re.id_reserva",
                tuple(valores),
            )
            filas = cursor.fetchall()
        return {"reservas": filas, "total": len(filas)}


    def expirar_solicitudes_vencidas(self) -> int:
        with self.conexion.sesion() as cursor:
            cursor.execute(
                "SELECT id_reserva FROM reserva "
                "WHERE estado IN ('EN_ESPERA','LISTA_PARA_RETIRO') "
                "AND fecha_limite_vencimiento IS NOT NULL "
                "AND fecha_limite_vencimiento<=UTC_TIMESTAMP() "
                "ORDER BY fecha_limite_vencimiento,id_reserva LIMIT 100"
            )
            pendientes = [fila["id_reserva"] for fila in cursor.fetchall()]
        total = 0
        for id_reserva in pendientes:
            if self._expirar_vencida(id_reserva):
                total += 1
        return total

    def _expirar_vencida(self, id_reserva):
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute("SELECT dni_persona,id_recurso_ref FROM reserva WHERE id_reserva=%s", (id_reserva,))
            referencia = cursor.fetchone()
            if not referencia:
                return False
            self._bloquear_personas(cursor, referencia["dni_persona"], referencia["dni_persona"])
            self._consultar_recurso_bloqueado(cursor, referencia["id_recurso_ref"])
            cursor.execute("SELECT * FROM reserva WHERE id_reserva=%s FOR UPDATE", (id_reserva,))
            fila = cursor.fetchone()
            if not fila or fila["estado"] not in ("EN_ESPERA", "LISTA_PARA_RETIRO"):
                return False
            cursor.execute("SELECT UTC_TIMESTAMP() AS ahora")
            ahora = cursor.fetchone()["ahora"]
            if fila["fecha_limite_vencimiento"] is None or fila["fecha_limite_vencimiento"] > ahora:
                return False
            reserva = self._desde_fila(fila)
            anterior = reserva.estado.value
            motivo = "Vencimiento automático: plazo de atención" if anterior == "EN_ESPERA" else "Vencimiento automático: plazo de retiro"
            reserva.resolver_reserva(AccionReserva.EXPIRAR, None, True, motivo)
            self._liberar_bien(cursor, reserva, None)
            self._guardar_resolucion(cursor, reserva, anterior, motivo, None)
            return True
