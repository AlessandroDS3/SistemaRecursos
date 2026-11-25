-- Ejecutar con la base del sistema seleccionada y la aplicación detenida.
SET @actualizar = IF(NOT EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE()
      AND TABLE_NAME='detalle_prestamo' AND COLUMN_NAME='ampliado'),
  'ALTER TABLE detalle_prestamo ADD COLUMN ampliado BOOLEAN NOT NULL DEFAULT FALSE',
  'DO 0');
PREPARE actualizar FROM @actualizar;
EXECUTE actualizar;
DEALLOCATE PREPARE actualizar;

SET @actualizar = IF(NOT EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE()
      AND TABLE_NAME='sancion' AND COLUMN_NAME='fecha_recuperacion_original'),
  'ALTER TABLE sancion ADD COLUMN fecha_recuperacion_original DATETIME NULL',
  'DO 0');
PREPARE actualizar FROM @actualizar;
EXECUTE actualizar;
DEALLOCATE PREPARE actualizar;

UPDATE detalle_prestamo d SET ampliado=TRUE
WHERE d.id_detalle>0 AND d.ampliado=FALSE AND (
  EXISTS(SELECT 1 FROM solicitud_ampliacion s
      WHERE s.id_detalle=d.id_detalle AND s.estado='APROBADA')
  OR EXISTS(SELECT 1 FROM historial_estado h
      WHERE h.entidad='PRESTAMO' AND h.id_entidad=d.id_prestamo
        AND h.observacion LIKE CONCAT('Detalle #',d.id_detalle,': % UTC → % UTC%'))
)
LIMIT 2147483647;

SET @actualizar = IF(NOT EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE()
      AND TABLE_NAME='historial_estado' AND COLUMN_NAME='entidad'
      AND COLUMN_TYPE LIKE '%RECTIFICACION_DEVOLUCION%' AND COLUMN_TYPE LIKE '%''CUENTA''%'),
  'ALTER TABLE historial_estado
    MODIFY entidad ENUM(''BIEN_MATERIAL'',''RESERVA'',''SANCION'',''PRESTAMO'',''CONFIGURACION_SANCIONES'',
      ''TIPO_PERSONA'',''AUTORIZACION_PROPIA'',''RECTIFICACION_DEVOLUCION'',''CUENTA'') NOT NULL,
    MODIFY id_entidad INT NULL',
  'DO 0');
PREPARE actualizar FROM @actualizar;
EXECUTE actualizar;
DEALLOCATE PREPARE actualizar;

SET @actualizar = IF(NOT EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE()
      AND TABLE_NAME='historial_estado' AND COLUMN_NAME='dni_objetivo'),
  'ALTER TABLE historial_estado ADD COLUMN dni_objetivo VARCHAR(8) NULL,
    ADD INDEX idx_historial_dni_objetivo (entidad, dni_objetivo),
    ADD CONSTRAINT fk_historial_dni_objetivo FOREIGN KEY (dni_objetivo) REFERENCES persona(dni) ON UPDATE CASCADE',
  'DO 0');
PREPARE actualizar FROM @actualizar;
EXECUTE actualizar;
DEALLOCATE PREPARE actualizar;

SET @actualizar = IF(NOT EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE()
      AND TABLE_NAME='historial_estado' AND COLUMN_NAME='datos'),
  'ALTER TABLE historial_estado ADD COLUMN datos JSON NULL',
  'DO 0');
PREPARE actualizar FROM @actualizar;
EXECUTE actualizar;
DEALLOCATE PREPARE actualizar;

-- Recupera los registros y códigos si se usó la versión preliminar.
SET @ultimo_codigo = 0;
SET @actualizar = IF(EXISTS(SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE()
      AND TABLE_NAME='autorizacion_operacion_propia'),
  'SELECT COALESCE(MAX(id_autorizacion),0) INTO @ultimo_codigo FROM autorizacion_operacion_propia',
  'DO 0');
PREPARE actualizar FROM @actualizar;
EXECUTE actualizar;
DEALLOCATE PREPARE actualizar;

SET @actualizar = IF(@ultimo_codigo > 0 AND @ultimo_codigo >= (SELECT COALESCE(MAX(id_historial_estado),0) FROM historial_estado),
  CONCAT('ALTER TABLE historial_estado AUTO_INCREMENT=', @ultimo_codigo + 1), 'DO 0');
PREPARE actualizar FROM @actualizar;
EXECUTE actualizar;
DEALLOCATE PREPARE actualizar;

SET @actualizar = IF(EXISTS(SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE()
      AND TABLE_NAME='autorizacion_operacion_propia'),
  'INSERT INTO historial_estado(entidad,id_entidad,estado_anterior,estado_nuevo,fecha,observacion,dni_responsable,dni_objetivo,datos)
   SELECT ''AUTORIZACION_PROPIA'',a.id_prestamo_objetivo,IF(a.fecha_uso IS NULL,NULL,''EMITIDA''),
     IF(a.fecha_uso IS NULL,''EMITIDA'',''UTILIZADA''),a.fecha,a.motivo,a.dni_administrador,a.dni_operador,
     JSON_OBJECT(''accion'',a.accion,''fecha_uso'',a.fecha_uso,''id_prestamo_uso'',a.id_prestamo_uso,''codigo_anterior'',a.id_autorizacion)
   FROM autorizacion_operacion_propia a
   WHERE NOT EXISTS(SELECT 1 FROM historial_estado h WHERE h.entidad=''AUTORIZACION_PROPIA''
       AND h.datos->>''$.codigo_anterior''=CAST(a.id_autorizacion AS CHAR))',
  'DO 0');
PREPARE actualizar FROM @actualizar;
EXECUTE actualizar;
DEALLOCATE PREPARE actualizar;

SET @actualizar = IF(EXISTS(SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE()
      AND TABLE_NAME='historial_tipo_persona'),
  'INSERT INTO historial_estado(entidad,id_entidad,estado_anterior,estado_nuevo,fecha,observacion,dni_responsable,dni_objetivo,datos)
   SELECT ''TIPO_PERSONA'',NULL,c.tipo_anterior,c.tipo_nuevo,c.fecha,c.motivo,c.dni_responsable,c.dni_persona,
     JSON_OBJECT(''datos_institucionales'',c.datos_anteriores,''id_anterior'',c.id_cambio)
   FROM historial_tipo_persona c
   WHERE NOT EXISTS(SELECT 1 FROM historial_estado h WHERE h.entidad=''TIPO_PERSONA''
       AND h.datos->>''$.id_anterior''=CAST(c.id_cambio AS CHAR))',
  'DO 0');
PREPARE actualizar FROM @actualizar;
EXECUTE actualizar;
DEALLOCATE PREPARE actualizar;

SET @actualizar = IF(EXISTS(SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE()
      AND TABLE_NAME='rectificacion_devolucion'),
  'INSERT INTO historial_estado(entidad,id_entidad,estado_anterior,estado_nuevo,fecha,observacion,dni_responsable,dni_objetivo,datos)
   SELECT ''RECTIFICACION_DEVOLUCION'',r.id_detalle,''DEVUELTO'',''PENDIENTE'',r.fecha,r.motivo,r.dni_administrador,r.dni_receptor_original,
     JSON_OBJECT(''fecha_devolucion_original'',r.fecha_devolucion_original,''condicion_original'',r.condicion_original,
       ''observacion_original'',r.observacion_original,''id_anterior'',r.id_rectificacion)
   FROM rectificacion_devolucion r
   WHERE NOT EXISTS(SELECT 1 FROM historial_estado h WHERE h.entidad=''RECTIFICACION_DEVOLUCION''
       AND h.datos->>''$.id_anterior''=CAST(r.id_rectificacion AS CHAR))',
  'DO 0');
PREPARE actualizar FROM @actualizar;
EXECUTE actualizar;
DEALLOCATE PREPARE actualizar;
