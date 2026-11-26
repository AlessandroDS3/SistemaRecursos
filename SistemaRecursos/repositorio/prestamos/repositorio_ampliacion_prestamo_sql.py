from datetime import datetime

from dominio.compartido.validacion import Conflicto
from dominio.gestion_control.politica_prestamo import HorarioAtencion, PoliticaPrestamo
from dominio.gestion_prestamos.ampliacion_prestamo import (
    DatosParaValidarAmpliacion, DetalleParaAmpliar, PrestamoParaAmpliar, RestriccionesAmpliacion,
)
from dominio.gestion_prestamos.prestamo import EstadoPrestamo
from dominio.gestion_prestamos.solicitud_ampliacion import EstadoSolicitudAmpliacion, SolicitudAmpliacion
from dominio.gestion_recursos.bien_material import EstadoBien
from repositorio.base_datos.base_sql import RepositorioSQL
from repositorio.personas_usuarios.repositorio_persona_sql import CONSULTA_PARA_PRESTAMO
from repositorio.prestamos.repositorio_prestamo_sql import RepositorioPrestamoSQL


class RepositorioAmpliacionPrestamoSQL(RepositorioSQL):
    def consultar_datos_para_validar_ampliacion(self, prestamo: int, detalle: int) -> DatosParaValidarAmpliacion:
        recurso = self.consultar_sql(
            '''SELECT b.id_recurso FROM detalle_prestamo d JOIN bien_material b ON b.id_bien=d.id_bien
            WHERE d.id_prestamo=%s AND d.id_detalle=%s''', (prestamo, detalle), una=True,
        )
        if recurso:
            self.consultar_sql('SELECT id_recurso FROM recurso WHERE id_recurso=%s FOR UPDATE',
                               (recurso['id_recurso'],), una=True)
        cabecera = self.consultar_sql(
            'SELECT id_prestamo,dni_persona,estado FROM prestamo WHERE id_prestamo=%s FOR UPDATE',
            (prestamo,), una=True,
        )
        if cabecera is None:
            return DatosParaValidarAmpliacion()
        cabecera = PrestamoParaAmpliar(cabecera['id_prestamo'], cabecera['dni_persona'], EstadoPrestamo(cabecera['estado']))
        fila = self.consultar_sql(
            '''SELECT d.id_politica,d.fecha_limite_devolucion,d.fecha_devolucion,d.fecha_regularizacion,
            d.ampliado,b.estado AS estado_bien,b.id_recurso FROM detalle_prestamo d
            JOIN bien_material b ON b.id_bien=d.id_bien WHERE d.id_prestamo=%s AND d.id_detalle=%s FOR UPDATE''',
            (prestamo, detalle),
            una=True,
        )
        if fila is None:
            return DatosParaValidarAmpliacion(prestamo=cabecera)
        politica = self.consultar_sql(
            'SELECT * FROM politica_prestamo WHERE id_politica=%s FOR UPDATE',
            (fila['id_politica'],),
            una=True,
        )
        horario = self.consultar_sql(
            'SELECT hora_apertura,hora_cierre,dias_atencion FROM configuracion_general '
            'WHERE id_configuracion=1 FOR UPDATE',
            una=True,
        )
        bien = DetalleParaAmpliar(
            id_recurso=fila['id_recurso'], fecha_limite_devolucion=fila['fecha_limite_devolucion'],
            prestado_pendiente=(fila['fecha_devolucion'] is None and fila['fecha_regularizacion'] is None
                                and fila['estado_bien'] == EstadoBien.PRESTADO),
            ampliado=bool(fila['ampliado']),
        )
        return DatosParaValidarAmpliacion(
            prestamo=cabecera, detalle=bien, politica=PoliticaPrestamo.desde_datos(politica) if politica else None,
            horario=HorarioAtencion.desde_datos(horario) if horario else None,
        )

    def consultar_restricciones_ampliacion(
        self, prestamo: PrestamoParaAmpliar, recurso: int,
    ) -> RestriccionesAmpliacion:
        documentos = {prestamo.dni_persona}
        documentos.update(fila['dni_persona'] for fila in self.consultar_sql(
            'SELECT dni_persona FROM participante_prestamo WHERE id_prestamo=%s FOR SHARE',
            (prestamo.id_prestamo,),
        ))
        documentos = tuple(sorted(documentos))
        marcas = ','.join(['%s'] * len(documentos))
        personas = self.consultar_sql(
            CONSULTA_PARA_PRESTAMO + f' WHERE p.dni IN ({marcas}) ORDER BY p.dni FOR SHARE', documentos,
        )
        prestamos = RepositorioPrestamoSQL(self.conexion, self._cursor)
        disponibles, en_espera = prestamos.contar_disponibles_y_reservas_en_espera(recurso)
        return RestriccionesAmpliacion(
            personas=personas, sancion=prestamos.sanciones.existen_sanciones_activas(documentos),
            reservas_sin_bien=en_espera > disponibles,
        )

    # Solicitudes del usuario (AMP-01)

    def registrar_solicitud_ampliacion(self, prestamo: int, detalle: int, solicitante: str,
                                       solicitud: SolicitudAmpliacion, fecha_anterior: datetime) -> int:
        return self.ejecutar_escritura_sql(
            '''INSERT INTO solicitud_ampliacion(id_prestamo,id_detalle,dni_solicitante,cantidad,
            unidad,motivo,fecha_solicitud,fecha_limite_anterior)
            VALUES(%s,%s,%s,%s,%s,%s,UTC_TIMESTAMP(),%s)''',
            (prestamo, detalle, solicitante, solicitud.cantidad, solicitud.unidad,
             solicitud.motivo, fecha_anterior),
        )

    def consultar_solicitud_ampliacion(self, identificador, bloquear=False):
        return self.consultar_sql(
            'SELECT * FROM solicitud_ampliacion WHERE id_solicitud=%s'
            + (' FOR UPDATE' if bloquear else ''),
            (identificador,),
            una=True,
        )

    def consultar_solicitudes_ampliacion(self, estado=None, prestamo=None):
        condiciones, parametros = [], []
        if estado:
            condiciones.append('s.estado=%s')
            parametros.append(estado)
        if prestamo:
            condiciones.append('s.id_prestamo=%s')
            parametros.append(prestamo)
        sql = '''SELECT s.*,b.codigo_inventario,r.nombre AS recurso,d.fecha_limite_devolucion,
            d.fecha_devolucion,d.fecha_regularizacion,
            CONCAT(p.nombres,' ',p.apellidos) AS solicitante,
            CONCAT(pr.nombres,' ',pr.apellidos) AS responsable_resolucion
            FROM solicitud_ampliacion s
            JOIN detalle_prestamo d ON d.id_detalle=s.id_detalle
            JOIN bien_material b ON b.id_bien=d.id_bien
            JOIN recurso r ON r.id_recurso=b.id_recurso
            JOIN persona p ON p.dni=s.dni_solicitante
            LEFT JOIN persona pr ON pr.dni=s.dni_resolucion'''
        if condiciones:
            sql += ' WHERE ' + ' AND '.join(condiciones)
        return self.consultar_sql(
            sql + " ORDER BY s.estado<>'PENDIENTE', s.fecha_solicitud DESC LIMIT 200", parametros
        )

    def resolver_solicitud_ampliacion(self, identificador: int, estado: EstadoSolicitudAmpliacion,
                                      actor: str, nueva: datetime | None, observacion: str | None) -> None:
        self.ejecutar_escritura_sql(
            """UPDATE solicitud_ampliacion SET estado=%s,fecha_resolucion=UTC_TIMESTAMP(),
            dni_resolucion=%s,fecha_limite_nueva=%s,observacion_resolucion=%s
            WHERE id_solicitud=%s AND estado='PENDIENTE'""",
            (estado, actor, nueva, observacion, identificador),
        )
        if self._cursor.rowcount != 1:
            raise Conflicto('La solicitud ya fue resuelta. Recarga la lista.')

    def actualizar_plazo_prestamo(self, detalle: int, anterior: datetime, nueva: datetime) -> None:
        self.ejecutar_escritura_sql(
            '''UPDATE detalle_prestamo SET fecha_limite_devolucion=%s,ampliado=TRUE
            WHERE id_detalle=%s AND fecha_limite_devolucion=%s
            AND fecha_devolucion IS NULL AND fecha_regularizacion IS NULL AND ampliado=FALSE''',
            (nueva, detalle, anterior),
        )
        if self._cursor.rowcount != 1:
            raise Conflicto('El plazo cambió. Recarga el préstamo.')
