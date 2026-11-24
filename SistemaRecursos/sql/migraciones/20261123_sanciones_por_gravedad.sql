-- Ejecutar con la base existente del sistema seleccionada y la aplicación detenida.
-- Actualiza el esquema previo a sanciones por gravedad. No crea ni elimina bases.
-- Cada ALTER se confirma por separado en MySQL. Los bloques se pueden volver a ejecutar.

SET @actualizar = IF(EXISTS (
    SELECT 1 FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='configuracion_general' AND COLUMN_NAME='dias_leve'
), 'DO 0', 'ALTER TABLE configuracion_general
    ADD dias_leve INT NOT NULL DEFAULT 14 CHECK (dias_leve BETWEEN 1 AND 3650),
    ADD dias_grave INT NOT NULL DEFAULT 180 CHECK (dias_grave BETWEEN 1 AND 3650),
    ADD dias_espera_perdida INT NOT NULL DEFAULT 7 CHECK (dias_espera_perdida BETWEEN 1 AND 365)');
PREPARE actualizar FROM @actualizar;
EXECUTE actualizar;
DEALLOCATE PREPARE actualizar;

SET @actualizar = IF(EXISTS (
    SELECT 1 FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='prestamo' AND COLUMN_NAME='estado'
        AND COLUMN_TYPE LIKE '%REGULARIZADO%'
), 'DO 0', 'ALTER TABLE prestamo MODIFY estado
    ENUM(''ACTIVO'',''VENCIDO'',''DEVUELTO'',''PARCIALMENTE_DEVUELTO'',''REGULARIZADO'')
    NOT NULL DEFAULT ''ACTIVO''');
PREPARE actualizar FROM @actualizar;
EXECUTE actualizar;
DEALLOCATE PREPARE actualizar;

SET @actualizar = IF(EXISTS (
    SELECT 1 FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='detalle_prestamo' AND COLUMN_NAME='fecha_regularizacion'
), 'DO 0', 'ALTER TABLE detalle_prestamo
    ADD fecha_regularizacion DATETIME NULL AFTER fecha_devolucion,
    ADD CHECK (fecha_regularizacion IS NULL OR fecha_devolucion IS NULL)');
PREPARE actualizar FROM @actualizar;
EXECUTE actualizar;
DEALLOCATE PREPARE actualizar;

SET @actualizar = IF(EXISTS (
    SELECT 1 FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='incidencia' AND COLUMN_NAME='tipo'
        AND COLUMN_TYPE LIKE '%CUSTODIA%'
), 'DO 0', 'ALTER TABLE incidencia MODIFY tipo
    ENUM(''RETRASO'',''DANIO'',''PERDIDA'',''SALIDA_NO_AUTORIZADA'',''CUSTODIA'') NOT NULL');
PREPARE actualizar FROM @actualizar;
EXECUTE actualizar;
DEALLOCATE PREPARE actualizar;

SET @actualizar = IF(EXISTS (
    SELECT 1 FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='sancion' AND COLUMN_NAME='gravedad'
), 'DO 0', 'ALTER TABLE sancion
    ADD gravedad ENUM(''LEVE'',''GRAVE'',''MUY_GRAVE'') NOT NULL DEFAULT ''LEVE'',
    ADD dias_leve INT NOT NULL DEFAULT 14,
    ADD dias_grave INT NOT NULL DEFAULT 180,
    ADD dias_espera_perdida INT NOT NULL DEFAULT 7,
    ADD fecha_inicio_nivel DATETIME NULL,
    ADD fecha_fin DATETIME NULL,
    ADD fecha_revision DATETIME NULL,
    ADD fecha_regularizacion DATETIME NULL,
    ADD tipo_regularizacion ENUM(''DEVOLUCION'',''RECUPERACION'',''REPARACION'',''REPOSICION'',''VERIFICACION'') NULL,
    ADD dni_regularizacion VARCHAR(8) NULL,
    ADD observacion_regularizacion VARCHAR(255) NULL,
    ADD id_bien_reposicion INT NULL,
    ADD FOREIGN KEY (dni_regularizacion) REFERENCES persona(dni) ON UPDATE CASCADE,
    ADD FOREIGN KEY (id_bien_reposicion) REFERENCES bien_material(id_bien)');
PREPARE actualizar FROM @actualizar;
EXECUTE actualizar;
DEALLOCATE PREPARE actualizar;

SET @actualizar = IF(EXISTS (
    SELECT 1 FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='historial_estado' AND COLUMN_NAME='entidad'
        AND COLUMN_TYPE LIKE '%CONFIGURACION_SANCIONES%'
), 'DO 0', 'ALTER TABLE historial_estado MODIFY entidad
    ENUM(''BIEN_MATERIAL'',''RESERVA'',''SANCION'',''PRESTAMO'',''CONFIGURACION_SANCIONES'') NOT NULL');
PREPARE actualizar FROM @actualizar;
EXECUTE actualizar;
DEALLOCATE PREPARE actualizar;

-- Conserva fechas y estados históricos. Solo incorpora una regularización si
-- hay una devolución en buen estado registrada y la causa fue el retraso.
START TRANSACTION;
UPDATE sancion s
JOIN incidencia i ON i.id_incidencia=s.id_incidencia_ref
JOIN detalle_prestamo d ON d.id_detalle=i.id_detalle
SET s.gravedad=CASE WHEN i.tipo='RETRASO' THEN 'LEVE' ELSE 'GRAVE' END,
    s.fecha_inicio_nivel=s.fecha,
    s.fecha_fin=DATE_ADD(s.fecha, INTERVAL (CASE WHEN i.tipo='RETRASO' THEN s.dias_leve ELSE s.dias_grave END) DAY),
    s.fecha_revision=DATE_ADD(d.fecha_limite_devolucion, INTERVAL (s.dias_leve+s.dias_espera_perdida) DAY),
    s.fecha_regularizacion=IF(i.tipo='RETRASO' AND d.condicion_devolucion='BUENO', d.fecha_devolucion, NULL),
    s.tipo_regularizacion=IF(i.tipo='RETRASO' AND d.condicion_devolucion='BUENO'
        AND d.fecha_devolucion IS NOT NULL, 'DEVOLUCION', NULL),
    s.dni_regularizacion=IF(i.tipo='RETRASO' AND d.condicion_devolucion='BUENO'
        AND d.fecha_devolucion IS NOT NULL, d.dni_encargado_devolucion, NULL)
WHERE s.fecha_inicio_nivel IS NULL;
COMMIT;
