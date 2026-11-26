from datetime import datetime
import json
from typing import Mapping

from dominio.gestion_prestamos.reserva import (
    DatosParaValidarReserva,
    DetalleReserva,
    EN_ESPERA,
    ESTADOS_PENDIENTES,
    FILTRO_PENDIENTES,
    Reserva,
    ReservaEnCola,
)
from repositorio.base_datos.base_sql import RepositorioSQL
from repositorio.personas_usuarios.repositorio_persona_sql import CONSULTA_PARA_PRESTAMO
from repositorio.prestamos.repositorio_prestamo_sql import RepositorioPrestamoSQL

MARCAS_PENDIENTES = ','.join(['%s'] * len(ESTADOS_PENDIENTES))
RESERVAS_PENDIENTES_SQL = f'''re.estado IN ({MARCAS_PENDIENTES})
    AND (re.fecha_limite_vencimiento IS NULL OR re.fecha_limite_vencimiento>UTC_TIMESTAMP())'''
ORDEN_DE_PREPARACION = '''(fecha_requerida>{ahora}),
    CASE WHEN fecha_requerida>{ahora} THEN fecha_requerida ELSE fecha_solicitud END,
    fecha_solicitud, COALESCE(id_reserva_principal,id_reserva)'''
DETALLE_DE_RESERVA = '''SELECT re.*,r.nombre AS recurso,b.codigo_inventario,
    b.estado AS estado_bien,b.id_recurso AS recurso_bien,
    CONCAT(p.nombres,' ',p.apellidos) AS solicitante FROM reserva re
    JOIN recurso r ON r.id_recurso=re.id_recurso JOIN persona p ON p.dni=re.dni_persona
    LEFT JOIN bien_material b ON b.id_bien=re.id_bien'''


class RepositorioReservaSQL(RepositorioSQL):
    aislamiento = 'READ COMMITTED'

    def consultar_recursos_para_reserva(self, documento):
        persona = self.consultar_sql(CONSULTA_PARA_PRESTAMO + ' WHERE p.dni=%s', (documento,), una=True)
        return self.consultar_sql(
            '''SELECT r.id_recurso,r.nombre,p.plazo_maximo,p.unidad_plazo,p.permite_salida,
            c.hora_apertura,c.hora_cierre,c.dias_atencion
            FROM recurso r LEFT JOIN politica_prestamo p ON p.id_categoria=r.id_categoria
            AND p.tipo_persona=%s AND p.vigente=TRUE
            LEFT JOIN configuracion_general c ON c.id_configuracion=1 ORDER BY r.nombre''',
            (persona['tipo'] if persona else None,),
        )

    @property
    def prestamos(self):
        return RepositorioPrestamoSQL(self.conexion, self._cursor)

    def contar_reservas_pendientes(self, documento: str | None = None) -> int:
        sql = ('SELECT COUNT(*) AS total FROM reserva re WHERE re.id_reserva_principal IS NULL AND '
               + RESERVAS_PENDIENTES_SQL)
        parametros = ESTADOS_PENDIENTES
        if documento is not None:
            sql += ' AND (re.dni_persona=%s OR JSON_CONTAINS(re.participantes,JSON_QUOTE(%s)))'
            parametros += (documento, documento)
        return self.consultar_sql(sql, parametros, una=True)['total']

    def consultar_reservas(
        self, documento: str | None = None, filtros: Mapping[str, str] | None = None
    ) -> list[ReservaEnCola]:
        filtros = filtros or {}
        orden = ORDEN_DE_PREPARACION.format(ahora='UTC_TIMESTAMP()')
        sql = f'''WITH cola_preparacion AS (
            SELECT id_reserva, DENSE_RANK() OVER (PARTITION BY id_recurso ORDER BY {orden}) AS posicion
            FROM reserva WHERE estado=%s
            AND (fecha_limite_vencimiento IS NULL OR fecha_limite_vencimiento>UTC_TIMESTAMP())
            ), contenido AS (
            SELECT COALESCE(linea.id_reserva_principal,linea.id_reserva) AS id_principal,
                COUNT(*) AS cantidad_bienes, GROUP_CONCAT(DISTINCT recurso.nombre ORDER BY recurso.nombre SEPARATOR ', ') AS recursos
            FROM reserva linea JOIN recurso ON recurso.id_recurso=linea.id_recurso
            GROUP BY id_principal
            )
            SELECT re.*,r.nombre AS recurso,
            CONCAT(p.nombres,' ',p.apellidos) AS solicitante,
            cola.posicion, contenido.cantidad_bienes, contenido.recursos
            FROM reserva re JOIN recurso r ON r.id_recurso=re.id_recurso
            JOIN persona p ON p.dni=re.dni_persona
            JOIN contenido ON contenido.id_principal=re.id_reserva
            LEFT JOIN cola_preparacion cola ON cola.id_reserva=re.id_reserva
            WHERE re.id_reserva_principal IS NULL'''
        parametros = [EN_ESPERA]
        if documento:
            sql += ' AND (re.dni_persona=%s OR JSON_CONTAINS(re.participantes,JSON_QUOTE(%s)))'
            parametros.extend((documento, documento))
        estado = filtros.get('estado')
        if estado == FILTRO_PENDIENTES:
            sql += ' AND ' + RESERVAS_PENDIENTES_SQL
            parametros.extend(ESTADOS_PENDIENTES)
        elif estado:
            sql += ' AND re.estado=%s'
            parametros.append(estado)
        if filtros.get('tipo_gestion'):
            sql += ' AND re.tipo_gestion=%s'
            parametros.append(filtros['tipo_gestion'])
        if filtros.get('q'):
            sql += " AND (re.dni_persona LIKE %s OR contenido.recursos LIKE %s OR CONCAT(p.nombres,' ',p.apellidos) LIKE %s)"
            parametros += [f"%{filtros['q']}%"] * 3
        return self.consultar_sql(
            sql + ' ORDER BY re.fecha_solicitud DESC,re.id_reserva DESC', parametros
        )

    def consultar_reserva(
        self, identificador: int, bloquear: bool = False
    ) -> DetalleReserva | None:
        return self.consultar_sql(
            DETALLE_DE_RESERVA + ' WHERE re.id_reserva=%s AND re.id_reserva_principal IS NULL'
            + (' FOR UPDATE OF re' if bloquear else ''),
            (identificador,),
            una=True,
        )

    def consultar_lineas_de_reserva(self, identificador: int, bloquear: bool = False) -> list[DetalleReserva]:
        return self.consultar_sql(
            DETALLE_DE_RESERVA + ' WHERE re.id_reserva_principal=%s ORDER BY re.id_reserva'
            + (' FOR UPDATE OF re' if bloquear else ''),
            (identificador,),
        )

    def consultar_datos_para_validar_reserva(self, documento: str, recurso: int) -> DatosParaValidarReserva:
        fila = self.consultar_sql(
            'SELECT id_categoria FROM recurso WHERE id_recurso=%s FOR UPDATE', (recurso,), una=True
        )
        persona = self.consultar_sql(
            CONSULTA_PARA_PRESTAMO + ' WHERE p.dni=%s FOR UPDATE', (documento,), una=True
        )
        politica = self.consultar_sql(
            '''SELECT permite_salida FROM politica_prestamo
            WHERE tipo_persona=%s AND id_categoria=%s AND vigente=TRUE FOR SHARE''',
            (persona['tipo'] if persona else None, fila['id_categoria'] if fila else None),
            una=True,
        )
        vencido = self.consultar_sql(
            '''SELECT d.id_detalle FROM detalle_prestamo d
            JOIN prestamo p ON p.id_prestamo=d.id_prestamo WHERE d.fecha_devolucion IS NULL AND d.fecha_regularizacion IS NULL
            AND d.fecha_limite_devolucion<UTC_TIMESTAMP() AND (p.dni_persona=%s OR EXISTS(
                SELECT 1 FROM participante_prestamo pp WHERE pp.id_prestamo=p.id_prestamo
                AND pp.dni_persona=%s)) LIMIT 1''',
            (documento, documento),
        )
        duplicada = self.consultar_sql(
            f'''SELECT id_reserva FROM reserva
            WHERE dni_persona=%s AND id_recurso=%s AND estado IN ({MARCAS_PENDIENTES})
            AND (fecha_limite_vencimiento IS NULL OR fecha_limite_vencimiento>%s) FOR UPDATE''',
            (documento, recurso, *ESTADOS_PENDIENTES, self.consultar_fecha_actual()),
        )
        sancion = self.prestamos.sanciones.existen_sanciones_activas([documento])
        return DatosParaValidarReserva(
            persona=persona,
            existe_recurso=fila is not None,
            permite_salida=bool(politica['permite_salida']) if politica else None,
            bloqueado=bool(vencido) or sancion,
            duplicada=bool(duplicada),
        )

    def consultar_horario_y_plazos_de_reserva(self):
        return self.consultar_sql(
            'SELECT * FROM configuracion_general WHERE id_configuracion=1 FOR SHARE', una=True
        )

    def guardar_nueva_reserva(self, reserva: Reserva) -> int:
        return self.insertar_fila_sql('reserva', dict(
            dni_persona=reserva.dni_persona, id_recurso=reserva.id_recurso,
            fecha_solicitud=reserva.fecha_solicitud, fecha_requerida=reserva.fecha_requerida,
            tipo_gestion=reserva.tipo_gestion, observaciones=reserva.observaciones,
            salida_solicitada=reserva.salida_solicitada, fecha_limite_vencimiento=reserva.fecha_limite_vencimiento,
            id_reserva_principal=reserva.id_reserva_principal,
            participantes=json.dumps(reserva.participantes) if reserva.participantes else None,
            estado=reserva.estado,
        ))

    def actualizar_reserva(self, reserva: Reserva) -> None:
        self.ejecutar_escritura_sql(
            '''UPDATE reserva SET estado=%s,id_bien=%s,fecha_preparacion=%s,
            fecha_limite_vencimiento=%s,id_prestamo_ref=%s WHERE id_reserva=%s''',
            (reserva.estado, reserva.id_bien, reserva.fecha_preparacion,
             reserva.fecha_limite_vencimiento, reserva.id_prestamo_ref, reserva.identificador),
        )

    def bloquear_recurso(self, identificador):
        return self.consultar_sql(
            'SELECT id_recurso FROM recurso WHERE id_recurso=%s FOR UPDATE',
            (identificador,),
            una=True,
        )

    def bloquear_persona(self, documento: str) -> None:
        self.consultar_sql('SELECT dni FROM persona WHERE dni=%s FOR UPDATE', (documento,), una=True)

    def consultar_primera_reserva_en_espera(self, recurso: int, ahora: datetime) -> int | None:
        # Las líneas de una reserva tienen la misma prioridad y quedan juntas en cada cola.
        orden = ORDEN_DE_PREPARACION.format(ahora='%s')
        fila = self.consultar_sql(
            f'''SELECT COALESCE(id_reserva_principal,id_reserva) AS id_reserva FROM reserva WHERE id_recurso=%s
            AND estado=%s
            AND (fecha_limite_vencimiento IS NULL OR fecha_limite_vencimiento>%s)
            ORDER BY {orden} LIMIT 1 FOR UPDATE''',
            (recurso, EN_ESPERA, ahora, ahora, ahora),
            una=True,
        )
        return fila['id_reserva'] if fila else None

    def consultar_bien_disponible(self, recurso: int) -> int | None:
        fila = self.consultar_sql(
            '''SELECT b.id_bien FROM bien_material b WHERE b.id_recurso=%s
            AND b.estado='DISPONIBLE' AND NOT EXISTS(SELECT 1 FROM detalle_prestamo d
                WHERE d.id_bien=b.id_bien AND d.fecha_devolucion IS NULL AND d.fecha_regularizacion IS NULL)
            ORDER BY b.id_bien LIMIT 1 FOR UPDATE''',
            (recurso,),
            una=True,
        )
        return fila['id_bien'] if fila else None

    def cambiar_estado_bien_reservado(self, bien, estado, esperado, actor, reserva):
        from dominio.compartido.validacion import Conflicto

        self.ejecutar_escritura_sql(
            'UPDATE bien_material SET estado=%s WHERE id_bien=%s AND estado=%s',
            (estado, bien, esperado),
        )
        if self._cursor.rowcount != 1:
            raise Conflicto('El bien cambió de estado. Recarga la reserva.')
        self.registrar_historial_estado(
            'BIEN_MATERIAL', bien, esperado, estado, actor, f'Reserva #{reserva}.'
        )

    def consultar_reservas_vencidas(self) -> list[int]:
        filas = self.consultar_sql(
            f'''SELECT id_reserva FROM reserva WHERE estado IN ({MARCAS_PENDIENTES})
            AND id_reserva_principal IS NULL AND fecha_limite_vencimiento<=UTC_TIMESTAMP()
            ORDER BY id_reserva LIMIT 100''',
            ESTADOS_PENDIENTES,
        )
        return [fila['id_reserva'] for fila in filas]
