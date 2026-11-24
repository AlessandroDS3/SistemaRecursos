"""Lecturas del historial. Cada consulta conserva el alcance exacto del sujeto."""

from dominio.compartido.validacion import NoEncontrado
from repositorio.base_datos.base_sql import RepositorioSQL
from repositorio.prestamos.repositorio_prestamo_sql import ESTADO_SQL, SITUACION_BIEN_SQL

TABLAS_DETALLE = '''FROM detalle_prestamo d
    JOIN prestamo p ON p.id_prestamo=d.id_prestamo
    JOIN persona per ON per.dni=p.dni_persona
    JOIN bien_material b ON b.id_bien=d.id_bien
    JOIN recurso r ON r.id_recurso=b.id_recurso'''
CONTEXTO_DETALLE = '''p.id_prestamo,p.dni_persona,p.tipo_prestamo,
    CONCAT(per.nombres,' ',per.apellidos) AS solicitante,
    b.codigo_inventario,r.nombre AS recurso'''
ALCANCE_PERSONA = '''(p.dni_persona=%s OR EXISTS (
    SELECT 1 FROM participante_prestamo pp
    WHERE pp.id_prestamo=p.id_prestamo AND pp.dni_persona=%s))'''


class RepositorioHistorialSQL(RepositorioSQL):
    def _buscar_sujetos(self, filtro):
        termino = f'%{filtro.q}%'
        if filtro.tipo == 'historial_bien':
            return self.consultar_sql(
                '''SELECT b.codigo_inventario,b.estado,b.ubicacion,
                r.nombre AS recurso,c.nombre AS categoria
                FROM bien_material b JOIN recurso r ON r.id_recurso=b.id_recurso
                JOIN categoria_recurso c ON c.id_categoria=r.id_categoria
                WHERE b.codigo_inventario LIKE %s OR r.nombre LIKE %s
                ORDER BY r.nombre,b.codigo_inventario LIMIT 50''',
                (termino, termino),
            )
        return self.consultar_sql(
            '''SELECT p.dni,p.nombres,p.apellidos,p.estado,e.cui,
            CONCAT(p.nombres,' ',p.apellidos) AS nombre_completo
            FROM persona p LEFT JOIN estudiante e ON e.dni=p.dni
            WHERE p.dni LIKE %s OR e.cui LIKE %s
                OR CONCAT(p.nombres,' ',p.apellidos) LIKE %s
                OR CONCAT(p.apellidos,' ',p.nombres) LIKE %s
            ORDER BY p.apellidos,p.nombres,p.dni LIMIT 50''',
            (termino,) * 4,
        )

    def consultar_historial(self, filtro, solo_prestamos=False):
        resultado = dict(
            sujeto=None,
            coincidencias=[],
            prestamos=[],
            historial_prestamos=[],
            historial_bienes=[],
            incidencias=[],
            sanciones=[],
            historial_sanciones=[],
            reservas=[],
            historial_reservas=[],
        )
        por_bien = filtro.tipo == 'historial_bien'
        valor = filtro.codigo_inventario if por_bien else filtro.dni_persona
        if not valor:
            if filtro.q and not solo_prestamos:
                resultado['coincidencias'] = self._buscar_sujetos(filtro)
            return resultado
        if por_bien:
            sujeto = self.consultar_sql(
                '''SELECT b.*,r.nombre AS recurso,c.nombre AS categoria
                FROM bien_material b JOIN recurso r ON r.id_recurso=b.id_recurso
                JOIN categoria_recurso c ON c.id_categoria=r.id_categoria
                WHERE b.codigo_inventario=%s''',
                (valor,),
                una=True,
            )
        else:
            sujeto = self.consultar_sql(
                '''SELECT p.dni,p.nombres,p.apellidos,p.estado,e.cui,
                CONCAT(p.nombres,' ',p.apellidos) AS nombre_completo
                FROM persona p LEFT JOIN estudiante e ON e.dni=p.dni
                WHERE p.dni=%s''',
                (valor,),
                una=True,
            )
        if sujeto is None:
            raise NoEncontrado('No se encontró el objeto o la persona seleccionada.')
        resultado['sujeto'] = sujeto
        if por_bien:
            alcance, parametros = 'd.id_bien=%s', (sujeto['id_bien'],)
            alcance_prestamo = '''EXISTS (SELECT 1 FROM detalle_prestamo dp
                WHERE dp.id_prestamo=p.id_prestamo AND dp.id_bien=%s)'''
        else:
            alcance, parametros = ALCANCE_PERSONA, (valor, valor)
            alcance_prestamo = alcance

        resultado['prestamos'] = self.consultar_sql(
            f'''SELECT d.*,p.fecha_entrega,
            p.observaciones AS observaciones_prestamo,p.dni_encargado,
            {CONTEXTO_DETALLE},{ESTADO_SQL} AS estado_prestamo,b.estado AS estado_bien,
            CONCAT(ent.nombres,' ',ent.apellidos) AS entregado_por,
            CONCAT(dev.nombres,' ',dev.apellidos) AS recibido_por,
            {SITUACION_BIEN_SQL} AS situacion
            {TABLAS_DETALLE}
            LEFT JOIN persona ent ON ent.dni=p.dni_encargado
            LEFT JOIN persona dev ON dev.dni=d.dni_encargado_devolucion
            WHERE {alcance} ORDER BY p.fecha_entrega DESC,p.id_prestamo DESC,d.id_detalle''',
            parametros,
        )

        resultado['historial_prestamos'] = self.consultar_sql(
            f'''SELECT h.*,
            p.id_prestamo,p.dni_persona,p.tipo_prestamo,
            CONCAT(per.nombres,' ',per.apellidos) AS solicitante,
            CONCAT(reg.nombres,' ',reg.apellidos) AS registrador
            FROM historial_estado h JOIN prestamo p ON p.id_prestamo=h.id_entidad
            JOIN persona per ON per.dni=p.dni_persona
            LEFT JOIN persona reg ON reg.dni=h.dni_responsable
            WHERE h.entidad='PRESTAMO' AND {alcance_prestamo}
            ORDER BY h.fecha,h.id_historial_estado''',
            parametros,
        )

        resultado['incidencias'] = self.consultar_sql(
            f'''SELECT i.*,{CONTEXTO_DETALLE},
            CONCAT(reg.nombres,' ',reg.apellidos) AS registrador
            {TABLAS_DETALLE} JOIN incidencia i ON i.id_detalle=d.id_detalle
            LEFT JOIN persona reg ON reg.dni=i.dni_registrador
            WHERE {alcance} ORDER BY i.fecha,i.id_incidencia''',
            parametros,
        )
        resultado['sanciones'] = self.consultar_sql(
            f'''SELECT s.*,{CONTEXTO_DETALLE},
            CONCAT(lev.nombres,' ',lev.apellidos) AS levantada_por
            {TABLAS_DETALLE} JOIN incidencia i ON i.id_detalle=d.id_detalle
            JOIN sancion s ON s.id_incidencia_ref=i.id_incidencia
            LEFT JOIN persona lev ON lev.dni=s.dni_levantamiento
            WHERE {alcance} ORDER BY s.fecha,s.id_sancion''',
            parametros,
        )
        resultado['historial_sanciones'] = self.consultar_sql(
            f'''SELECT h.*,
            s.id_sancion,{CONTEXTO_DETALLE},
            CONCAT(reg.nombres,' ',reg.apellidos) AS registrador
            {TABLAS_DETALLE} JOIN incidencia i ON i.id_detalle=d.id_detalle
            JOIN sancion s ON s.id_incidencia_ref=i.id_incidencia
            JOIN historial_estado h ON h.entidad='SANCION' AND h.id_entidad=s.id_sancion
            LEFT JOIN persona reg ON reg.dni=h.dni_responsable
            WHERE {alcance} ORDER BY h.fecha,h.id_historial_estado''',
            parametros,
        )

        # Un usuario solo ve eventos de sus préstamos. Los cambios generales del
        # bien podrían pertenecer a otra persona y no forman parte de esta lectura.
        if por_bien:
            resultado['historial_bienes'] = self.consultar_sql(
                '''SELECT h.*,
                b.codigo_inventario,r.nombre AS recurso,
                CONCAT(reg.nombres,' ',reg.apellidos) AS registrador
                FROM historial_estado h JOIN bien_material b ON b.id_bien=h.id_entidad
                JOIN recurso r ON r.id_recurso=b.id_recurso
                LEFT JOIN persona reg ON reg.dni=h.dni_responsable
                WHERE h.entidad='BIEN_MATERIAL' AND b.id_bien=%s
                ORDER BY h.fecha,h.id_historial_estado''',
                parametros,
            )
        if not solo_prestamos:
            campo = 're.id_bien' if por_bien else 're.dni_persona'
            seleccion = sujeto['id_bien'] if por_bien else valor
            tablas_reserva = '''FROM reserva re JOIN persona per ON per.dni=re.dni_persona
                JOIN recurso r ON r.id_recurso=re.id_recurso
                LEFT JOIN bien_material b ON b.id_bien=re.id_bien'''
            resultado['reservas'] = self.consultar_sql(
                f'''SELECT re.*,
                CONCAT(per.nombres,' ',per.apellidos) AS solicitante,
                r.nombre AS recurso,b.codigo_inventario
                {tablas_reserva} WHERE {campo}=%s
                ORDER BY re.fecha_solicitud,re.id_reserva''',
                (seleccion,),
            )
            resultado['historial_reservas'] = self.consultar_sql(
                f'''SELECT h.*,
                re.id_reserva,re.dni_persona,
                CONCAT(per.nombres,' ',per.apellidos) AS solicitante,
                r.nombre AS recurso,b.codigo_inventario,
                CONCAT(reg.nombres,' ',reg.apellidos) AS registrador
                {tablas_reserva}
                JOIN historial_estado h ON h.entidad='RESERVA' AND h.id_entidad=re.id_reserva
                LEFT JOIN persona reg ON reg.dni=h.dni_responsable
                WHERE {campo}=%s ORDER BY h.fecha,h.id_historial_estado''',
                (seleccion,),
            )
        return resultado
