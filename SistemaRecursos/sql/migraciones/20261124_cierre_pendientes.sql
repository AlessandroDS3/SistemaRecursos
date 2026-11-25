-- Ejecutar con la base existente del sistema seleccionada y la aplicación detenida.
-- Agrega lo necesario para el cierre de pendientes del informe:
--   AUT-01  identificador del sistema único por bien (la serie del fabricante se conserva aparte)
--   AUT-02  fecha de registro automática del bien
--   SEG-02  sesiones registradas en el servidor (inactividad, duración máxima y cierre real)
--   MAN-01  registro de mantenimientos con apertura y cierre
--   AMP-01  solicitudes de ampliación del usuario
--   OPE-01  estado del procesador automático de vencimientos
-- No crea ni elimina bases ni borra datos. Cada bloque se puede volver a ejecutar.

SET @actualizar = IF(EXISTS (
    SELECT 1 FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='bien_material' AND COLUMN_NAME='fecha_registro'
), 'DO 0', 'ALTER TABLE bien_material
    ADD fecha_registro DATETIME NOT NULL DEFAULT (UTC_TIMESTAMP()) AFTER fecha_adquisicion');
PREPARE actualizar FROM @actualizar;
EXECUTE actualizar;
DEALLOCATE PREPARE actualizar;

-- Para los bienes existentes, la fecha de registro es el primer movimiento conocido.
UPDATE bien_material b
JOIN (
    SELECT id_entidad, MIN(fecha) AS primera
    FROM historial_estado WHERE entidad='BIEN_MATERIAL' GROUP BY id_entidad
) h ON h.id_entidad=b.id_bien
SET b.fecha_registro=h.primera
WHERE h.primera < b.fecha_registro;

SET @actualizar = IF(EXISTS (
    SELECT 1 FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='bien_material' AND COLUMN_NAME='identificador_sistema'
), 'DO 0', 'ALTER TABLE bien_material
    ADD identificador_sistema VARCHAR(20) NULL AFTER codigo_inventario,
    ADD UNIQUE KEY uq_bien_identificador_sistema (identificador_sistema)');
PREPARE actualizar FROM @actualizar;
EXECUTE actualizar;
DEALLOCATE PREPARE actualizar;

-- Identificador estable para los bienes existentes; no modifica la serie del fabricante.
UPDATE bien_material
SET identificador_sistema=CONCAT(
    'SR-', DATE_FORMAT(fecha_registro, '%Y'), '-',
    LPAD(UPPER(CONV(id_bien * 7919 + 104729, 10, 36)), 6, '0'))
WHERE identificador_sistema IS NULL;

CREATE TABLE IF NOT EXISTS sesion_usuario (
  id_sesion         CHAR(64) PRIMARY KEY,
  id_usuario        INT NOT NULL,
  fecha_inicio      DATETIME NOT NULL,
  ultima_actividad  DATETIME NOT NULL,
  fecha_cierre      DATETIME NULL,
  INDEX idx_sesion_usuario (id_usuario, fecha_cierre),
  FOREIGN KEY (id_usuario) REFERENCES usuario_sistema(id_usuario) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS mantenimiento_bien (
  id_mantenimiento    INT AUTO_INCREMENT PRIMARY KEY,
  id_bien             INT NOT NULL,
  tipo                ENUM('PREVENTIVO','CORRECTIVO') NOT NULL,
  motivo              VARCHAR(255) NOT NULL,
  estado_previo       VARCHAR(30) NOT NULL,
  fecha_inicio        DATETIME NOT NULL,
  fecha_fin_estimada  DATE NULL,
  dni_apertura        VARCHAR(8) NOT NULL,
  fecha_fin_real      DATETIME NULL,
  dni_cierre          VARCHAR(8) NULL,
  resultado           ENUM('DISPONIBLE','DANADO') NULL,
  observacion_cierre  VARCHAR(255) NULL,
  abierto             TINYINT GENERATED ALWAYS AS (IF(fecha_fin_real IS NULL, 1, NULL)) STORED,
  UNIQUE KEY uq_mantenimiento_abierto (id_bien, abierto),
  INDEX idx_mantenimiento_bien (id_bien, fecha_inicio),
  FOREIGN KEY (id_bien) REFERENCES bien_material(id_bien),
  FOREIGN KEY (dni_apertura) REFERENCES persona(dni) ON UPDATE CASCADE,
  FOREIGN KEY (dni_cierre) REFERENCES persona(dni) ON UPDATE CASCADE,
  CHECK (fecha_fin_real IS NULL OR resultado IS NOT NULL)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS solicitud_ampliacion (
  id_solicitud            INT AUTO_INCREMENT PRIMARY KEY,
  id_prestamo             INT NOT NULL,
  id_detalle              INT NOT NULL,
  dni_solicitante         VARCHAR(8) NOT NULL,
  cantidad                INT NOT NULL CHECK (cantidad > 0),
  unidad                  ENUM('HORAS','DIAS') NOT NULL,
  motivo                  VARCHAR(255) NOT NULL,
  fecha_solicitud         DATETIME NOT NULL,
  fecha_limite_anterior   DATETIME NOT NULL,
  estado                  ENUM('PENDIENTE','APROBADA','RECHAZADA') NOT NULL DEFAULT 'PENDIENTE',
  fecha_resolucion        DATETIME NULL,
  dni_resolucion          VARCHAR(8) NULL,
  fecha_limite_nueva      DATETIME NULL,
  observacion_resolucion  VARCHAR(255) NULL,
  pendiente               TINYINT GENERATED ALWAYS AS (IF(estado='PENDIENTE', 1, NULL)) STORED,
  UNIQUE KEY uq_solicitud_pendiente (id_detalle, pendiente),
  INDEX idx_solicitud_estado (estado, fecha_solicitud),
  FOREIGN KEY (id_prestamo) REFERENCES prestamo(id_prestamo),
  FOREIGN KEY (id_detalle) REFERENCES detalle_prestamo(id_detalle),
  FOREIGN KEY (dni_solicitante) REFERENCES persona(dni) ON UPDATE CASCADE,
  FOREIGN KEY (dni_resolucion) REFERENCES persona(dni) ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS estado_procesador (
  id_procesador              TINYINT PRIMARY KEY CHECK (id_procesador = 1),
  ultima_ejecucion_correcta  DATETIME NULL,
  ultimo_error_fecha         DATETIME NULL,
  ultimo_error               VARCHAR(500) NULL,
  fallos_consecutivos        INT NOT NULL DEFAULT 0
) ENGINE=InnoDB;

INSERT IGNORE INTO estado_procesador(id_procesador) VALUES (1);
