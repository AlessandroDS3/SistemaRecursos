from repositorio.base_sql import RepositorioSQL


class RepositorioSancionSQL(RepositorioSQL):
    def listar(self):
        return self.consultar_sql('''SELECT s.*,i.tipo,i.id_detalle,d.id_prestamo,
            CONCAT(p.nombres,' ',p.apellidos) AS responsable FROM sancion s
            JOIN incidencia i ON i.id_incidencia=s.id_incidencia_ref
            JOIN detalle_prestamo d ON d.id_detalle=i.id_detalle
            JOIN prestamo pr ON pr.id_prestamo=d.id_prestamo JOIN persona p ON p.dni=pr.dni_persona
            ORDER BY s.fecha DESC,s.id_sancion DESC''')

    def consultar(self, identificador, bloquear=False):
        return self.consultar_sql(
            'SELECT * FROM sancion WHERE id_sancion=%s' + (' FOR UPDATE' if bloquear else ''),
            (identificador,),
            una=True,
        )

    def tiene_activas(self, documentos):
        documentos = tuple(sorted(set(documentos)))
        marcas = ','.join(['%s'] * len(documentos))
        if not documentos:
            return False
        filas = self.consultar_sql(
            f'''SELECT s.id_sancion FROM sancion s
            JOIN incidencia i ON i.id_incidencia=s.id_incidencia_ref
            JOIN detalle_prestamo d ON d.id_detalle=i.id_detalle JOIN prestamo pr ON pr.id_prestamo=d.id_prestamo
            WHERE s.estado='ACTIVA' AND (pr.dni_persona IN ({marcas}) OR EXISTS (
                SELECT 1 FROM participante_prestamo pp WHERE pp.id_prestamo=pr.id_prestamo
                AND pp.dni_persona IN ({marcas}))) FOR UPDATE''',
            documentos * 2,
        )
        return bool(filas)

    def buscar_retraso(self, detalle):
        return self.consultar_sql(
            '''SELECT i.id_incidencia,s.id_sancion,s.estado FROM incidencia i
            LEFT JOIN sancion s ON s.id_incidencia_ref=i.id_incidencia
            WHERE i.id_detalle=%s AND i.tipo='RETRASO' FOR UPDATE''',
            (detalle,),
            una=True,
        )

    def guardar_incidencia(self, detalle, tipo, descripcion, fecha):
        return self.insertar(
            'incidencia',
            dict(
                id_detalle=detalle,
                tipo=tipo,
                descripcion=descripcion,
                fecha=fecha,
                estado='REGISTRADA',
            ),
        )

    def guardar_sancion(self, incidencia, motivo, descripcion, fecha):
        return self.insertar(
            'sancion',
            dict(
                id_incidencia_ref=incidencia,
                motivo=motivo,
                descripcion=descripcion,
                fecha=fecha,
                estado='ACTIVA',
            ),
        )

    def candidatos(self):
        return self.consultar_sql('''SELECT d.id_detalle FROM detalle_prestamo d
            WHERE d.fecha_devolucion IS NULL AND d.fecha_limite_devolucion<UTC_TIMESTAMP()
            AND NOT EXISTS(SELECT 1 FROM incidencia i JOIN sancion s ON s.id_incidencia_ref=i.id_incidencia
                WHERE i.id_detalle=d.id_detalle AND i.tipo='RETRASO')
            ORDER BY d.id_prestamo,d.id_detalle LIMIT 100''')

    def cargar_detalle(self, identificador):
        return self.consultar_sql(
            '''SELECT d.* FROM detalle_prestamo d
            JOIN prestamo pr ON pr.id_prestamo=d.id_prestamo WHERE d.id_detalle=%s FOR UPDATE''',
            (identificador,),
            una=True,
        )

    def levantar(self, identificador, fecha, documento, justificacion):
        self.ejecutar(
            '''UPDATE sancion SET estado='LEVANTADA',fecha_levantamiento=%s,
            dni_levantamiento=%s,justificacion_levantamiento=%s WHERE id_sancion=%s''',
            (fecha, documento, justificacion, identificador),
        )
        self.ejecutar(
            '''UPDATE incidencia SET estado='RESUELTA'
            WHERE id_incidencia=(SELECT id_incidencia_ref FROM sancion WHERE id_sancion=%s)''',
            (identificador,),
        )
