from datetime import datetime
from typing import Mapping

from dominio.gestion_prestamos.reserva import (
    CambiosReserva,
    ContextoReserva,
    DetalleReserva,
    EN_ESPERA,
    ESTADOS_PENDIENTES,
    NuevaReserva,
    Reserva,
)
from repositorio.base_sql import RepositorioSQL
from repositorio.repositorio_persona_sql import CONSULTA as PERSONAS
from repositorio.repositorio_prestamo_sql import RepositorioPrestamoSQL

MARCAS_PENDIENTES = ','.join(['%s'] * len(ESTADOS_PENDIENTES))


class RepositorioReservaSQL(RepositorioSQL):
    def consultar_recursos_para_reserva(self, documento):
        persona = self.consultar_sql(PERSONAS + ' WHERE p.dni=%s', (documento,), una=True)
        return self.consultar_sql(
            '''SELECT r.id_recurso,r.nombre,p.plazo_maximo,p.unidad_plazo,p.permite_salida,
            c.hora_apertura,c.hora_cierre
            FROM recurso r LEFT JOIN politica_prestamo p ON p.id_categoria=r.id_categoria
            AND p.tipo_persona=%s AND p.vigente=TRUE
            LEFT JOIN configuracion_general c ON c.id_configuracion=1 ORDER BY r.nombre''',
            (persona['tipo'] if persona else None,),
        )

    @property
    def prestamos(self):
        return RepositorioPrestamoSQL(self.conexion, self._cursor)

    def consultar_reservas(
        self, documento: str | None = None, filtros: Mapping[str, str] | None = None
    ) -> list[Reserva]:
        filtros = filtros or {}
        sql = '''SELECT re.*,r.nombre AS recurso,
            CONCAT(p.nombres,' ',p.apellidos) AS solicitante,
            CASE WHEN re.estado=%s THEN (SELECT COUNT(*) FROM reserva otra
                WHERE otra.id_recurso=re.id_recurso AND otra.estado=%s
                AND (otra.fecha_solicitud<re.fecha_solicitud OR
                    (otra.fecha_solicitud=re.fecha_solicitud AND otra.id_reserva<=re.id_reserva))) END AS posicion
            FROM reserva re JOIN recurso r ON r.id_recurso=re.id_recurso
            JOIN persona p ON p.dni=re.dni_persona''' + ' WHERE 1=1'
        parametros = [EN_ESPERA, EN_ESPERA]
        if documento:
            sql += ' AND re.dni_persona=%s'
            parametros.append(documento)
        for campo in ('estado', 'tipo_gestion'):
            if filtros.get(campo):
                sql += ' AND re.' + campo + '=%s'
                parametros.append(filtros[campo])
        if filtros.get('q'):
            sql += " AND (re.dni_persona LIKE %s OR r.nombre LIKE %s OR CONCAT(p.nombres,' ',p.apellidos) LIKE %s)"
            parametros += [f"%{filtros['q']}%"] * 3
        return self.consultar_sql(
            sql + ' ORDER BY re.fecha_solicitud DESC,re.id_reserva DESC', parametros
        )

    def consultar_reserva(
        self, identificador: int, bloquear: bool = False
    ) -> DetalleReserva | None:
        return self.consultar_sql(
            '''SELECT re.*,r.nombre AS recurso,b.codigo_inventario,
            b.estado AS estado_bien,b.id_recurso AS recurso_bien,
            CONCAT(p.nombres,' ',p.apellidos) AS solicitante FROM reserva re
            JOIN recurso r ON r.id_recurso=re.id_recurso JOIN persona p ON p.dni=re.dni_persona
            LEFT JOIN bien_material b ON b.id_bien=re.id_bien WHERE re.id_reserva=%s'''
            + (' FOR UPDATE' if bloquear else ''),
            (identificador,),
            una=True,
        )

    def consultar_contexto_reserva(self, documento: str, recurso: int) -> ContextoReserva:
        persona = self.consultar_sql(
            PERSONAS + ' WHERE p.dni=%s FOR UPDATE', (documento,), una=True
        )
        fila = self.consultar_sql(
            'SELECT * FROM recurso WHERE id_recurso=%s FOR UPDATE', (recurso,), una=True
        )
        politica = self.consultar_sql(
            '''SELECT * FROM politica_prestamo
            WHERE tipo_persona=%s AND id_categoria=%s AND vigente=TRUE FOR UPDATE''',
            (persona['tipo'] if persona else None, fila['id_categoria'] if fila else None),
            una=True,
        )
        vencido = self.consultar_sql(
            '''SELECT d.id_detalle FROM detalle_prestamo d
            JOIN prestamo p ON p.id_prestamo=d.id_prestamo WHERE d.fecha_devolucion IS NULL
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
        return dict(
            persona=persona,
            recurso=fila,
            politica=politica,
            vencido=bool(vencido),
            sancion=self.prestamos.sanciones.existen_sanciones_activas([documento]),
            duplicada=bool(duplicada),
        )

    def consultar_configuracion_general(self):
        return self.consultar_sql(
            'SELECT * FROM configuracion_general WHERE id_configuracion=1 FOR UPDATE', una=True
        )

    def registrar_reserva(self, datos: NuevaReserva) -> int:
        return self.insertar('reserva', datos)

    def actualizar_reserva(self, identificador: int, datos: CambiosReserva) -> None:
        permitidos = {
            'estado',
            'id_bien',
            'fecha_preparacion',
            'fecha_limite_vencimiento',
            'id_prestamo_ref',
        }
        if not datos or not set(datos) <= permitidos:
            raise ValueError('Campos de reserva inválidos.')
        self.ejecutar(
            'UPDATE reserva SET ' + ','.join(c + '=%s' for c in datos) + ' WHERE id_reserva=%s',
            (*datos.values(), identificador),
        )

    def bloquear_recurso(self, identificador):
        return self.consultar_sql(
            'SELECT id_recurso FROM recurso WHERE id_recurso=%s FOR UPDATE',
            (identificador,),
            una=True,
        )

    def consultar_primera_reserva_en_espera(self, recurso: int, ahora: datetime) -> dict | None:
        return self.consultar_sql(
            '''SELECT id_reserva FROM reserva WHERE id_recurso=%s
            AND estado=%s AND fecha_requerida<=%s
            AND (fecha_limite_vencimiento IS NULL OR fecha_limite_vencimiento>%s)
            ORDER BY fecha_solicitud,id_reserva LIMIT 1 FOR UPDATE''',
            (recurso, EN_ESPERA, ahora, ahora),
            una=True,
        )

    def consultar_bien_disponible(self, recurso):
        return self.consultar_sql(
            '''SELECT b.* FROM bien_material b WHERE b.id_recurso=%s
            AND b.estado='DISPONIBLE' AND NOT EXISTS(SELECT 1 FROM detalle_prestamo d
                WHERE d.id_bien=b.id_bien AND d.fecha_devolucion IS NULL)
            ORDER BY b.id_bien LIMIT 1 FOR UPDATE''',
            (recurso,),
            una=True,
        )

    def cambiar_estado_bien_reservado(self, bien, estado, esperado, actor, reserva):
        from dominio.compartido.validacion import Conflicto

        self.ejecutar(
            'UPDATE bien_material SET estado=%s WHERE id_bien=%s AND estado=%s',
            (estado, bien, esperado),
        )
        if self._cursor.rowcount != 1:
            raise Conflicto('El bien cambió de estado. Recarga la reserva.')
        self.registrar_historial_estado(
            'BIEN_MATERIAL', bien, esperado, estado, actor, f'Reserva #{reserva}.'
        )

    def consultar_reservas_vencidas(self):
        return self.consultar_sql(
            f'''SELECT id_reserva FROM reserva WHERE estado IN ({MARCAS_PENDIENTES})
            AND fecha_limite_vencimiento<=UTC_TIMESTAMP() ORDER BY id_reserva LIMIT 100''',
            ESTADOS_PENDIENTES,
        )
