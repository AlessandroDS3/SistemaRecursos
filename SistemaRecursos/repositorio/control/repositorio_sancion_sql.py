from repositorio.base_datos.base_sql import RepositorioSQL

TABLAS = '''FROM sancion s JOIN incidencia i ON i.id_incidencia=s.id_incidencia_ref
    JOIN detalle_prestamo d ON d.id_detalle=i.id_detalle
    JOIN bien_material b ON b.id_bien=d.id_bien
    JOIN recurso r ON r.id_recurso=b.id_recurso
    JOIN politica_prestamo po ON po.id_politica=d.id_politica
    JOIN prestamo pr ON pr.id_prestamo=d.id_prestamo
    JOIN persona p ON p.dni=pr.dni_persona'''
CAMPOS = '''s.*,i.tipo,i.id_detalle,d.id_prestamo,d.id_bien,d.id_politica,
    d.fecha_limite_devolucion,d.fecha_devolucion,d.condicion_devolucion,
    d.fecha_regularizacion AS fecha_cierre_regularizacion,b.estado AS estado_bien,
    b.codigo_inventario,r.nombre AS recurso,r.id_recurso,po.permite_salida,
    pr.dni_persona,CONCAT(p.nombres,' ',p.apellidos) AS responsable'''


class RepositorioSancionSQL(RepositorioSQL):
    def consultar_configuracion_sanciones(self, bloquear=False):
        return self.consultar_sql(
            '''SELECT dias_leve,dias_grave,dias_espera_perdida
            FROM configuracion_general WHERE id_configuracion=1'''
            + (' FOR UPDATE' if bloquear else ''), una=True,
        )

    def guardar_configuracion_sanciones(self, datos):
        self.ejecutar_escritura_sql(
            '''UPDATE configuracion_general SET dias_leve=%s,dias_grave=%s,
            dias_espera_perdida=%s WHERE id_configuracion=1''',
            tuple(datos[k] for k in ('dias_leve', 'dias_grave', 'dias_espera_perdida')),
        )

    def consultar_detalle_sancion(self, identificador):
        fila = self.consultar_sancion(identificador)
        if fila is not None:
            fila['participantes'] = self.consultar_sql(
                '''SELECT pp.dni_persona,CONCAT(p.nombres,' ',p.apellidos) AS nombre
                FROM participante_prestamo pp JOIN persona p ON p.dni=pp.dni_persona
                WHERE pp.id_prestamo=%s AND pp.dni_persona<>%s ORDER BY p.apellidos,p.nombres''',
                (fila['id_prestamo'], fila['dni_persona']),
            )
        return fila

    def consultar_sanciones(self, filtros=None):
        filtros = filtros or {}
        sql = 'SELECT ' + CAMPOS + ' ' + TABLAS + ' WHERE 1=1'
        parametros = []
        if filtros.get('estado'):
            sql += ' AND s.estado=%s'
            parametros.append(filtros['estado'])
        if filtros.get('q'):
            consulta = filtros['q']
            sql += " AND (CONCAT(p.nombres,' ',p.apellidos) LIKE %s OR p.dni LIKE %s OR d.id_prestamo=%s)"
            parametros.extend(
                [f'%{consulta}%', f'%{consulta}%', consulta if consulta.isdigit() else 0]
            )
        return self.consultar_sql(sql + ' ORDER BY s.fecha DESC,s.id_sancion DESC', parametros)

    def consultar_sancion(self, identificador, bloquear=False):
        return self.consultar_sql(
            'SELECT ' + CAMPOS + ' ' + TABLAS + ' WHERE s.id_sancion=%s'
            + (' FOR UPDATE' if bloquear else ''),
            (identificador,),
            una=True,
        )

    def existen_sanciones_activas(self, documentos):
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

    def consultar_sancion_por_detalle_prestamo(self, detalle):
        return self.consultar_sql(
            'SELECT ' + CAMPOS + ' ' + TABLAS + ''' WHERE i.id_detalle=%s
            ORDER BY (s.estado='ACTIVA') DESC,s.id_sancion DESC LIMIT 1 FOR UPDATE''',
            (detalle,),
            una=True,
        )

    def registrar_incidencia(self, detalle, tipo, descripcion, fecha):
        return self.insertar_fila_sql(
            'incidencia',
            dict(
                id_detalle=detalle,
                tipo=tipo,
                descripcion=descripcion,
                fecha=fecha,
                estado='REGISTRADA',
            ),
        )

    def consultar_incidencia_sin_sancion(self, detalle, tipo):
        return self.consultar_sql(
            '''SELECT i.id_incidencia FROM incidencia i LEFT JOIN sancion s ON s.id_incidencia_ref=i.id_incidencia
            WHERE i.id_detalle=%s AND i.tipo=%s AND s.id_sancion IS NULL
            ORDER BY i.id_incidencia LIMIT 1 FOR UPDATE OF i''', (detalle, tipo), una=True,
        )

    def registrar_sancion(self, datos):
        return self.insertar_fila_sql('sancion', datos)

    def actualizar_sancion(self, identificador, datos):
        permitidos = {
            'gravedad', 'fecha_inicio_nivel', 'fecha_fin', 'motivo', 'descripcion', 'estado',
            'fecha_regularizacion', 'tipo_regularizacion', 'dni_regularizacion',
            'observacion_regularizacion', 'id_bien_reposicion', 'fecha_levantamiento',
            'dni_levantamiento', 'justificacion_levantamiento', 'fecha_recuperacion_original',
        }
        if not datos or set(datos) - permitidos:
            raise ValueError('Campos de sanción inválidos.')
        self.ejecutar_escritura_sql('UPDATE sancion SET ' + ','.join(k + '=%s' for k in datos)
                      + ' WHERE id_sancion=%s', (*datos.values(), identificador))

    def actualizar_incidencia(self, identificador, datos):
        if not datos or set(datos) - {'tipo', 'estado', 'descripcion', 'dni_registrador'}:
            raise ValueError('Campos de incidencia inválidos.')
        self.ejecutar_escritura_sql('UPDATE incidencia SET ' + ','.join(k + '=%s' for k in datos)
                      + ' WHERE id_incidencia=%s', (*datos.values(), identificador))

    def consultar_detalles_de_prestamo_vencidos(self):
        return self.consultar_sql('''SELECT d.id_detalle,d.id_prestamo FROM detalle_prestamo d
            WHERE d.fecha_devolucion IS NULL AND d.fecha_regularizacion IS NULL
            AND d.fecha_limite_devolucion<UTC_TIMESTAMP()
            AND NOT EXISTS(SELECT 1 FROM incidencia i JOIN sancion s ON s.id_incidencia_ref=i.id_incidencia
                WHERE i.id_detalle=d.id_detalle)
            ORDER BY d.id_prestamo,d.id_detalle LIMIT 100''')

    def consultar_sanciones_activas_para_revision(self):
        return self.consultar_sql('''SELECT i.id_detalle,s.id_sancion FROM sancion s
            JOIN incidencia i ON i.id_incidencia=s.id_incidencia_ref
            WHERE s.estado='ACTIVA' AND s.gravedad<>'MUY_GRAVE'
            AND s.fecha_regularizacion IS NOT NULL AND s.fecha_fin<=UTC_TIMESTAMP()
            ORDER BY s.id_sancion LIMIT 100''')

    @property
    def prestamos(self):
        from repositorio.prestamos.repositorio_prestamo_sql import RepositorioPrestamoSQL
        return RepositorioPrestamoSQL(self.conexion, self._cursor)

    @property
    def bienes(self):
        from repositorio.recursos.repositorio_bien_material_sql import RepositorioBienMaterialSQL
        return RepositorioBienMaterialSQL(self.conexion, self._cursor)
