-- Datos ficticios para probar el sistema de recursos con MySQL 8.
-- Crea prestamos_escuela_pruebas y carga registros de demostracion.
-- Ejecutar SOLO en una instalacion nueva; NO ejecutar sobre una base con datos.
-- Cuentas locales de demostracion (no usar en produccion):
-- admin / AdminPrueba2026!
-- encargado1 y encargado2 / EncargadoPrueba2026!
-- usuario1 y estudiante01 a estudiante08 / UsuarioPrueba2026!

-- Estructura del sistema de prestamos de recursos para MySQL 8.
-- Crea prestamos_escuela_pruebas para cargar los datos de demostracion.
SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS prestamos_escuela_pruebas
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE prestamos_escuela_pruebas;

CREATE TABLE IF NOT EXISTS persona (
  nombres             VARCHAR(100) NOT NULL,
  apellidos           VARCHAR(100) NOT NULL,
  dni                 VARCHAR(8) PRIMARY KEY,
  CONSTRAINT chk_persona_dni CHECK (dni REGEXP '^[0-9]{8}$'),
  telefono            VARCHAR(20),
  correo              VARCHAR(120) NOT NULL,
  estado              ENUM('ACTIVA','INACTIVA') NOT NULL DEFAULT 'ACTIVA',
  INDEX idx_persona_apellidos_nombres (apellidos, nombres),
  INDEX idx_persona_estado_apellidos_nombres (estado, apellidos, nombres)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS estudiante (
  dni          VARCHAR(8) PRIMARY KEY,
  cui                 VARCHAR(8) NOT NULL,
  CONSTRAINT uq_estudiante_cui UNIQUE(cui),
  CONSTRAINT chk_estudiante_cui CHECK (cui REGEXP '^[0-9]{8}$'),
  ciclo               INT NULL CHECK (ciclo IS NULL OR ciclo > 0),
  semestre_academico  VARCHAR(10) NULL,
  estado_matricula    ENUM('vigente','no_vigente') NOT NULL,
  FOREIGN KEY (dni) REFERENCES persona(dni) ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS docente (
  dni              VARCHAR(8) PRIMARY KEY,
  codigo_docente          VARCHAR(20) NOT NULL UNIQUE,
  departamento_academico  VARCHAR(100) NOT NULL,
  facultad                VARCHAR(100) NOT NULL,
  escuela_profesional     VARCHAR(100) NOT NULL,
  FOREIGN KEY (dni) REFERENCES persona(dni) ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS administrativo (
  dni       VARCHAR(8) PRIMARY KEY,
  codigo_empleado  VARCHAR(20) NOT NULL UNIQUE,
  area             VARCHAR(100) NOT NULL,
  FOREIGN KEY (dni) REFERENCES persona(dni) ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS rol (
  id_rol       INT AUTO_INCREMENT PRIMARY KEY,
  nombre       ENUM('USUARIO','ENCARGADO_PRESTAMOS','ADMINISTRADOR') NOT NULL UNIQUE,
  descripcion  VARCHAR(255),
  activo       BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS permiso (
  id_permiso   INT AUTO_INCREMENT PRIMARY KEY,
  codigo       VARCHAR(60) NOT NULL UNIQUE,
  descripcion  VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS rol_permiso (
  id_rol      INT NOT NULL,
  id_permiso  INT NOT NULL,
  PRIMARY KEY (id_rol, id_permiso),
  FOREIGN KEY (id_rol)     REFERENCES rol(id_rol)         ON DELETE CASCADE,
  FOREIGN KEY (id_permiso) REFERENCES permiso(id_permiso) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS usuario_sistema (
  id_usuario       INT AUTO_INCREMENT PRIMARY KEY,
  dni_persona   VARCHAR(8) NOT NULL UNIQUE,
  id_rol_ref       INT NOT NULL,
  nombre_usuario   VARCHAR(50)  NOT NULL UNIQUE,
  contrasena_hash  VARCHAR(255) NOT NULL,
  ultimo_acceso    DATETIME,
  activo           BOOLEAN NOT NULL DEFAULT TRUE,
  estado_cuenta    ENUM('ACTIVA','INACTIVA','BLOQUEADA') NOT NULL DEFAULT 'ACTIVA',
  FOREIGN KEY (dni_persona) REFERENCES persona(dni) ON UPDATE CASCADE,
  FOREIGN KEY (id_rol_ref)     REFERENCES rol(id_rol)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS sesion_acceso (
  token_hash BINARY(32) PRIMARY KEY,
  id_usuario INT NOT NULL,
  vence DATETIME NOT NULL,
  INDEX idx_sesion_vence (vence),
  FOREIGN KEY (id_usuario) REFERENCES usuario_sistema(id_usuario) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS intento_acceso (
  tipo ENUM('ORIGEN','USUARIO') NOT NULL,
  clave VARCHAR(64) NOT NULL,
  ventana BIGINT NOT NULL,
  intentos INT UNSIGNED NOT NULL,
  PRIMARY KEY (tipo, clave),
  INDEX idx_intento_ventana (ventana)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS categoria_recurso (
  id_categoria  INT AUTO_INCREMENT PRIMARY KEY,
  nombre        VARCHAR(80) NOT NULL UNIQUE,
  descripcion   VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS recurso (
  id_recurso        INT AUTO_INCREMENT PRIMARY KEY,
  id_categoria_ref  INT NOT NULL,
  nombre            VARCHAR(120) NOT NULL,
  marca             VARCHAR(80),
  modelo            VARCHAR(80),
  descripcion       VARCHAR(255),
  INDEX idx_recurso_nombre (nombre),
  INDEX idx_recurso_marca (marca),
  INDEX idx_recurso_modelo (modelo),
  FOREIGN KEY (id_categoria_ref) REFERENCES categoria_recurso(id_categoria)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bien_material (
  id_bien            INT AUTO_INCREMENT PRIMARY KEY,
  id_recurso_ref     INT NOT NULL,
  codigo_inventario  VARCHAR(40) NOT NULL UNIQUE,
  numero_serie       VARCHAR(60),
  fecha_adquisicion  DATE NOT NULL,
  estado             ENUM('DISPONIBLE','PRESTADO','RESERVADO','DANADO','MANTENIMIENTO','PERDIDO')
                     NOT NULL DEFAULT 'DISPONIBLE',
  ubicacion          VARCHAR(120),
  descripcion_bien   VARCHAR(255) NOT NULL DEFAULT '',
  INDEX idx_bien_estado_recurso_codigo (estado, id_recurso_ref, codigo_inventario),
  INDEX idx_bien_recurso_codigo (id_recurso_ref, codigo_inventario),
  FOREIGN KEY (id_recurso_ref) REFERENCES recurso(id_recurso)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS registro_fuera_servicio (
  id_registro         INT AUTO_INCREMENT PRIMARY KEY,
  id_bien_ref         INT NOT NULL,
  motivo              VARCHAR(255) NOT NULL,
  fecha_inicio        DATETIME NOT NULL,
  fecha_fin_estimada  DATETIME,
  fecha_fin_real      DATETIME,
  descripcion         VARCHAR(255),
  estado              ENUM('ACTIVO','RESUELTO') NOT NULL DEFAULT 'ACTIVO',
  FOREIGN KEY (id_bien_ref) REFERENCES bien_material(id_bien) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notificacion_danio (
  id_notificacion  INT AUTO_INCREMENT PRIMARY KEY,
  id_bien_ref      INT NOT NULL,
  dni_persona   VARCHAR(8) NOT NULL,
  mensaje          VARCHAR(255) NOT NULL,
  fecha_envio      DATETIME NOT NULL,
  FOREIGN KEY (id_bien_ref)    REFERENCES bien_material(id_bien),
  FOREIGN KEY (dni_persona) REFERENCES persona(dni) ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS horario_atencion (
  id_horario      TINYINT PRIMARY KEY CHECK (id_horario=1),
  hora_apertura   TIME NOT NULL,
  hora_cierre     TIME NOT NULL,
  CHECK (hora_apertura >= '00:00:00' AND hora_apertura < hora_cierre AND hora_cierre < '24:00:00')
) ENGINE=InnoDB;
INSERT INTO horario_atencion(id_horario,hora_apertura,hora_cierre)
VALUES(1,'08:00:00','16:00:00') ON DUPLICATE KEY UPDATE id_horario=id_horario;

CREATE TABLE IF NOT EXISTS limite_articulos_prestamo (
  tipo_persona      ENUM('ESTUDIANTE','DOCENTE','ADMINISTRATIVO') PRIMARY KEY,
  maximo_articulos  INT NULL CHECK (maximo_articulos > 0)
) ENGINE=InnoDB;
INSERT INTO limite_articulos_prestamo(tipo_persona,maximo_articulos)
VALUES('ESTUDIANTE',NULL),('DOCENTE',NULL),('ADMINISTRATIVO',NULL)
ON DUPLICATE KEY UPDATE tipo_persona=VALUES(tipo_persona);

CREATE TABLE IF NOT EXISTS politica_vencimiento_reserva (
  id_politica    TINYINT PRIMARY KEY CHECK (id_politica=1),
  plazo_espera   INT NOT NULL CHECK (plazo_espera BETWEEN 1 AND 87600),
  unidad_espera  ENUM('HORAS','DIAS') NOT NULL DEFAULT 'DIAS',
  plazo_retiro   INT NOT NULL CHECK (plazo_retiro BETWEEN 1 AND 87600),
  unidad_retiro  ENUM('HORAS','DIAS') NOT NULL DEFAULT 'HORAS'
) ENGINE=InnoDB;
INSERT INTO politica_vencimiento_reserva(id_politica,plazo_espera,unidad_espera,plazo_retiro,unidad_retiro)
VALUES(1,2,'DIAS',24,'HORAS') ON DUPLICATE KEY UPDATE id_politica=id_politica;

CREATE TABLE IF NOT EXISTS politica_prestamo (
  id_politica               INT AUTO_INCREMENT PRIMARY KEY,
  tipo_persona              ENUM('ESTUDIANTE','DOCENTE','ADMINISTRATIVO') NOT NULL,
  id_categoria_ref            INT NOT NULL,
  plazo_maximo              INT NOT NULL CHECK (plazo_maximo > 0),
  unidad_plazo              ENUM('HORAS','DIAS') NOT NULL,
  permite_salida            BOOLEAN NOT NULL DEFAULT FALSE,
  vigente                   BOOLEAN NOT NULL DEFAULT TRUE,
  categoria_vigente         INT GENERATED ALWAYS AS (CASE WHEN vigente THEN id_categoria_ref ELSE NULL END) STORED,
  UNIQUE KEY uq_politica_persona_categoria_vigente (tipo_persona, categoria_vigente),
  FOREIGN KEY (id_categoria_ref) REFERENCES categoria_recurso(id_categoria)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS prestamo (
  id_prestamo       INT AUTO_INCREMENT PRIMARY KEY,
  dni_persona    VARCHAR(8) NOT NULL,
  dni_encargado  VARCHAR(8) NOT NULL,
  tipo_prestamo     ENUM('INDIVIDUAL','GRUPAL') NOT NULL DEFAULT 'INDIVIDUAL',
  fecha_solicitud   DATETIME NOT NULL,
  fecha_entrega     DATETIME,
  estado            ENUM('ACTIVO','VENCIDO','DEVUELTO','PARCIALMENTE_DEVUELTO') NOT NULL DEFAULT 'ACTIVO',
  observaciones     VARCHAR(255),
  INDEX idx_prestamo_fecha_id (fecha_entrega, id_prestamo),
  FOREIGN KEY (dni_persona)   REFERENCES persona(dni) ON UPDATE CASCADE,
  FOREIGN KEY (dni_encargado) REFERENCES persona(dni) ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS detalle_prestamo (
  id_detalle               INT AUTO_INCREMENT PRIMARY KEY,
  id_prestamo              INT NOT NULL,
  id_bien_ref              INT NOT NULL,
  id_politica_ref          INT NOT NULL,
  fecha_limite_devolucion  DATETIME NOT NULL,
  estado_entrega           ENUM('DISPONIBLE','PRESTADO','RESERVADO','DANADO','MANTENIMIENTO','PERDIDO') NOT NULL,
  estado_devolucion        ENUM('DISPONIBLE','PRESTADO','RESERVADO','DANADO','MANTENIMIENTO','PERDIDO'),
  observaciones            VARCHAR(255),
  INDEX idx_detalle_vencimiento(estado_devolucion,fecha_limite_devolucion,id_prestamo),
  FOREIGN KEY (id_prestamo)  REFERENCES prestamo(id_prestamo) ON DELETE CASCADE,
  FOREIGN KEY (id_bien_ref)  REFERENCES bien_material(id_bien),
  FOREIGN KEY (id_politica_ref) REFERENCES politica_prestamo(id_politica)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS devolucion (
  id_devolucion     INT AUTO_INCREMENT PRIMARY KEY,
  id_detalle_ref    INT NOT NULL UNIQUE,
  dni_encargado  VARCHAR(8) NOT NULL,
  fecha             DATETIME NOT NULL,
  observaciones     VARCHAR(255),
  FOREIGN KEY (id_detalle_ref)   REFERENCES detalle_prestamo(id_detalle) ON DELETE CASCADE,
  FOREIGN KEY (dni_encargado) REFERENCES persona(dni) ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS reserva (
  id_reserva        INT AUTO_INCREMENT PRIMARY KEY,
  dni_persona    VARCHAR(8) NOT NULL,
  id_recurso_ref    INT NOT NULL,
  fecha_solicitud   DATETIME NOT NULL,
  fecha_requerida   DATETIME NOT NULL,
  fecha_preparacion DATETIME NULL,
  fecha_limite_vencimiento DATETIME NULL,
  posicion_en_cola  INT NOT NULL CHECK (posicion_en_cola > 0),
  tipo_gestion      ENUM('PRESTAMO','RESERVA') NOT NULL DEFAULT 'RESERVA',
  observaciones     VARCHAR(220) NOT NULL DEFAULT '',
  salida_solicitada BOOLEAN NOT NULL DEFAULT FALSE,
  id_bien_ref       INT NULL,
  id_prestamo_ref   INT NULL,
  estado            ENUM('EN_ESPERA','LISTA_PARA_RETIRO','ATENDIDA','CANCELADA','EXPIRADA','RECHAZADA') NOT NULL DEFAULT 'EN_ESPERA',
  INDEX idx_reserva_cola (id_recurso_ref,estado,fecha_solicitud,id_reserva),
  INDEX idx_reserva_persona_estado (dni_persona,estado),
  INDEX idx_reserva_vencimiento (estado,fecha_limite_vencimiento,id_reserva),
  FOREIGN KEY (dni_persona) REFERENCES persona(dni) ON UPDATE CASCADE,
  FOREIGN KEY (id_recurso_ref) REFERENCES recurso(id_recurso),
  CONSTRAINT fk_reserva_bien FOREIGN KEY (id_bien_ref) REFERENCES bien_material(id_bien),
  CONSTRAINT fk_reserva_prestamo FOREIGN KEY (id_prestamo_ref) REFERENCES prestamo(id_prestamo)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ampliacion_prestamo (
  id_ampliacion          INT AUTO_INCREMENT PRIMARY KEY,
  dni_solicitante     VARCHAR(8) NOT NULL,
  id_detalle_ref         INT NOT NULL,
  fecha_solicitud        DATETIME NOT NULL,
  fecha_limite_anterior  DATETIME NOT NULL,
  fecha_limite_nueva     DATETIME NOT NULL,
  motivo                 VARCHAR(255),
  estado                 ENUM('PENDIENTE','APROBADA','RECHAZADA') NOT NULL DEFAULT 'PENDIENTE',
  FOREIGN KEY (dni_solicitante) REFERENCES persona(dni) ON UPDATE CASCADE,
  FOREIGN KEY (id_detalle_ref)     REFERENCES detalle_prestamo(id_detalle) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS historial_prestamo (
  id_historial        INT AUTO_INCREMENT PRIMARY KEY,
  id_prestamo         INT NOT NULL,
  estado_anterior     ENUM('ACTIVO','VENCIDO','DEVUELTO','PARCIALMENTE_DEVUELTO'),
  estado_nuevo        ENUM('ACTIVO','VENCIDO','DEVUELTO','PARCIALMENTE_DEVUELTO') NOT NULL,
  fecha               DATETIME NOT NULL,
  observacion         VARCHAR(255),
  dni_responsable  VARCHAR(8) NOT NULL,
  FOREIGN KEY (id_prestamo)        REFERENCES prestamo(id_prestamo) ON DELETE CASCADE,
  FOREIGN KEY (dni_responsable) REFERENCES persona(dni) ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS participante_prestamo (
  id_participante   INT AUTO_INCREMENT PRIMARY KEY,
  id_prestamo       INT NOT NULL,
  dni_persona    VARCHAR(8) NOT NULL,
  rol_participacion VARCHAR(60),
  responsable       BOOLEAN NOT NULL DEFAULT FALSE,
  UNIQUE (id_prestamo, dni_persona),
  INDEX idx_participante_persona_prestamo (dni_persona, id_prestamo),
  FOREIGN KEY (id_prestamo)     REFERENCES prestamo(id_prestamo) ON DELETE CASCADE,
  FOREIGN KEY (dni_persona)  REFERENCES persona(dni) ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notificacion (
  id_notificacion  INT AUTO_INCREMENT PRIMARY KEY,
  id_detalle_ref   INT,
  id_bien_ref      INT,
  dni_persona   VARCHAR(8) NOT NULL,
  fecha_programada DATETIME NOT NULL,
  fecha_envio      DATETIME,
  mensaje          VARCHAR(255) NOT NULL,
  estado           ENUM('PENDIENTE','ENVIADA','LEIDA') NOT NULL DEFAULT 'PENDIENTE',
  FOREIGN KEY (id_detalle_ref) REFERENCES detalle_prestamo(id_detalle) ON DELETE CASCADE,
  FOREIGN KEY (id_bien_ref)    REFERENCES bien_material(id_bien),
  FOREIGN KEY (dni_persona) REFERENCES persona(dni) ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS incidencia (
  id_incidencia   INT AUTO_INCREMENT PRIMARY KEY,
  id_detalle_ref  INT NOT NULL,
  descripcion     VARCHAR(255),
  fecha           DATETIME NOT NULL,
  estado          ENUM('REGISTRADA','EN_REVISION','RESUELTA') NOT NULL DEFAULT 'REGISTRADA',
  FOREIGN KEY (id_detalle_ref) REFERENCES detalle_prestamo(id_detalle) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS sancion (
  id_sancion         INT AUTO_INCREMENT PRIMARY KEY,
  dni_persona     VARCHAR(8) NOT NULL,
  id_incidencia_ref  INT NOT NULL UNIQUE,
  motivo             VARCHAR(255) NOT NULL,
  fecha              DATETIME NOT NULL,
  descripcion        VARCHAR(255),
  estado             ENUM('ACTIVA','CUMPLIDA','LEVANTADA','ANULADA') NOT NULL DEFAULT 'ACTIVA',
  id_detalle_vencido_ref       INT NULL UNIQUE,
  fecha_levantamiento          DATETIME NULL,
  dni_levantamiento            VARCHAR(8) NULL,
  justificacion_levantamiento  VARCHAR(255) NULL,
  FOREIGN KEY (id_detalle_vencido_ref) REFERENCES detalle_prestamo(id_detalle),
  FOREIGN KEY (dni_levantamiento) REFERENCES persona(dni) ON UPDATE CASCADE,
  FOREIGN KEY (dni_persona)    REFERENCES persona(dni) ON UPDATE CASCADE,
  FOREIGN KEY (id_incidencia_ref) REFERENCES incidencia(id_incidencia)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS historial_estado (
  id_historial_estado  INT AUTO_INCREMENT PRIMARY KEY,
  entidad              ENUM('BIEN_MATERIAL','RESERVA','SANCION') NOT NULL,
  id_entidad           INT NOT NULL,
  estado_anterior      VARCHAR(30),
  estado_nuevo         VARCHAR(30) NOT NULL,
  fecha                DATETIME NOT NULL,
  observacion          VARCHAR(255),
  dni_responsable   VARCHAR(8),
  INDEX (entidad, id_entidad),
  FOREIGN KEY (dni_responsable) REFERENCES persona(dni) ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Datos ficticios de demostración.
SET FOREIGN_KEY_CHECKS=0;

INSERT INTO `administrativo` (`codigo_empleado`, `area`, `dni`) VALUES
('ADM-PRUEBA-01', 'Administración', '98000001'),
('ADM-PRUEBA-02', 'Préstamos', '98000002'),
('ADM-PRB-03', 'Préstamos', '99000015');

INSERT INTO `bien_material` (`id_bien`, `id_recurso_ref`, `codigo_inventario`, `numero_serie`, `fecha_adquisicion`, `estado`, `ubicacion`, `descripcion_bien`) VALUES
(1, 1, 'PR-LAP-001', 'SER-LAP-001', '2026-07-02', 'PRESTADO', 'Laboratorio 1', ''),
(2, 1, 'PR-LAP-002', 'SER-LAP-002', '2026-07-02', 'DISPONIBLE', 'Laboratorio 1', ''),
(3, 2, 'PR-LIB-001', '', '2026-07-02', 'DISPONIBLE', 'Biblioteca', ''),
(4, 2, 'PR-LIB-002', '', '2026-07-02', 'DISPONIBLE', 'Biblioteca', ''),
(5, 2, 'PR-LIB-003', '', '2026-07-02', 'MANTENIMIENTO', 'Biblioteca', ''),
(6, 3, 'PR-PRO-001', 'SER-PRO-001', '2026-07-02', 'DISPONIBLE', 'Almacén', ''),
(7, 18, 'PR-DEP-MESA-001', NULL, '2026-08-01', 'DISPONIBLE', 'Coliseo', ''),
(8, 23, 'PR-DEP-PALETA-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(9, 23, 'PR-DEP-PALETA-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(10, 23, 'PR-DEP-PALETA-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(11, 23, 'PR-DEP-PALETA-004', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(12, 25, 'PR-DEP-BASQ-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(13, 25, 'PR-DEP-BASQ-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(14, 25, 'PR-DEP-BASQ-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(15, 25, 'PR-DEP-BASQ-004', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(16, 25, 'PR-DEP-BASQ-005', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(17, 25, 'PR-DEP-BASQ-006', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(18, 26, 'PR-DEP-PING-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(19, 26, 'PR-DEP-PING-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(20, 26, 'PR-DEP-PING-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(21, 26, 'PR-DEP-PING-004', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(22, 26, 'PR-DEP-PING-005', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(23, 26, 'PR-DEP-PING-006', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(24, 26, 'PR-DEP-PING-007', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(25, 26, 'PR-DEP-PING-008', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(26, 26, 'PR-DEP-PING-009', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(27, 26, 'PR-DEP-PING-010', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(28, 26, 'PR-DEP-PING-011', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(29, 26, 'PR-DEP-PING-012', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(30, 26, 'PR-DEP-PING-013', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(31, 26, 'PR-DEP-PING-014', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(32, 26, 'PR-DEP-PING-015', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(33, 26, 'PR-DEP-PING-016', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(34, 26, 'PR-DEP-PING-017', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(35, 26, 'PR-DEP-PING-018', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(36, 26, 'PR-DEP-PING-019', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(37, 26, 'PR-DEP-PING-020', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(38, 26, 'PR-DEP-PING-021', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(39, 26, 'PR-DEP-PING-022', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(40, 26, 'PR-DEP-PING-023', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(41, 26, 'PR-DEP-PING-024', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', ''),
(42, 4, 'PR-JUE-AJEDREZ-001', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', ''),
(43, 4, 'PR-JUE-AJEDREZ-002', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', ''),
(44, 4, 'PR-JUE-AJEDREZ-003', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', ''),
(45, 10, 'PR-JUE-CATAN-001', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', ''),
(46, 10, 'PR-JUE-CATAN-002', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', ''),
(47, 12, 'PR-JUE-DOMINO-001', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', ''),
(48, 12, 'PR-JUE-DOMINO-002', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', ''),
(49, 12, 'PR-JUE-DOMINO-003', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', ''),
(50, 16, 'PR-JUE-JENGA-001', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', ''),
(51, 16, 'PR-JUE-JENGA-002', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', ''),
(52, 21, 'PR-JUE-MONOPOLY-001', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', ''),
(53, 21, 'PR-JUE-MONOPOLY-002', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', ''),
(54, 2, 'PR-LIB-004', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(55, 2, 'PR-LIB-005', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(56, 5, 'PR-LIB-AC-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(57, 5, 'PR-LIB-AC-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(58, 5, 'PR-LIB-AC-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(59, 5, 'PR-LIB-AC-004', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(60, 5, 'PR-LIB-AC-005', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(61, 13, 'PR-LIB-ED-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(62, 13, 'PR-LIB-ED-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(63, 13, 'PR-LIB-ED-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(64, 13, 'PR-LIB-ED-004', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(65, 13, 'PR-LIB-ED-005', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(66, 14, 'PR-LIB-BD-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(67, 14, 'PR-LIB-BD-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(68, 14, 'PR-LIB-BD-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(69, 14, 'PR-LIB-BD-004', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(70, 14, 'PR-LIB-BD-005', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(71, 15, 'PR-LIB-IS-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(72, 15, 'PR-LIB-IS-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(73, 15, 'PR-LIB-IS-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(74, 15, 'PR-LIB-IS-004', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(75, 15, 'PR-LIB-IS-005', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(76, 17, 'PR-LIB-MD-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(77, 17, 'PR-LIB-MD-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(78, 17, 'PR-LIB-MD-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(79, 17, 'PR-LIB-MD-004', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(80, 17, 'PR-LIB-MD-005', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(81, 27, 'PR-LIB-PY-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(82, 27, 'PR-LIB-PY-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(83, 27, 'PR-LIB-PY-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(84, 27, 'PR-LIB-PY-004', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(85, 27, 'PR-LIB-PY-005', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(86, 28, 'PR-LIB-RC-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(87, 28, 'PR-LIB-RC-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(88, 28, 'PR-LIB-RC-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(89, 28, 'PR-LIB-RC-004', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(90, 28, 'PR-LIB-RC-005', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(91, 29, 'PR-LIB-SI-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(92, 29, 'PR-LIB-SI-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(93, 29, 'PR-LIB-SI-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(94, 29, 'PR-LIB-SI-004', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(95, 29, 'PR-LIB-SI-005', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(96, 31, 'PR-LIB-SO-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(97, 31, 'PR-LIB-SO-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(98, 31, 'PR-LIB-SO-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(99, 31, 'PR-LIB-SO-004', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(100, 31, 'PR-LIB-SO-005', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', ''),
(101, 19, 'PR-MOB-MESA-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(102, 19, 'PR-MOB-MESA-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(103, 19, 'PR-MOB-MESA-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(104, 19, 'PR-MOB-MESA-004', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(105, 19, 'PR-MOB-MESA-005', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(106, 19, 'PR-MOB-MESA-006', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(107, 30, 'PR-MOB-SILLA-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(108, 30, 'PR-MOB-SILLA-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(109, 30, 'PR-MOB-SILLA-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(110, 30, 'PR-MOB-SILLA-004', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(111, 30, 'PR-MOB-SILLA-005', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(112, 30, 'PR-MOB-SILLA-006', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(113, 30, 'PR-MOB-SILLA-007', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(114, 30, 'PR-MOB-SILLA-008', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(115, 30, 'PR-MOB-SILLA-009', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(116, 30, 'PR-MOB-SILLA-010', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(117, 30, 'PR-MOB-SILLA-011', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(118, 30, 'PR-MOB-SILLA-012', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(119, 30, 'PR-MOB-SILLA-013', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(120, 30, 'PR-MOB-SILLA-014', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(121, 30, 'PR-MOB-SILLA-015', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(122, 30, 'PR-MOB-SILLA-016', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(123, 30, 'PR-MOB-SILLA-017', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(124, 30, 'PR-MOB-SILLA-018', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(125, 30, 'PR-MOB-SILLA-019', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(126, 30, 'PR-MOB-SILLA-020', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(127, 6, 'PR-TEC-HDMI-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(128, 6, 'PR-TEC-HDMI-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(129, 6, 'PR-TEC-HDMI-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(130, 6, 'PR-TEC-HDMI-004', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(131, 6, 'PR-TEC-HDMI-005', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(132, 6, 'PR-TEC-HDMI-006', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(133, 6, 'PR-TEC-HDMI-007', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(134, 6, 'PR-TEC-HDMI-008', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(135, 6, 'PR-TEC-HDMI-009', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(136, 6, 'PR-TEC-HDMI-010', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(137, 7, 'PR-TEC-CALC-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(138, 7, 'PR-TEC-CALC-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(139, 7, 'PR-TEC-CALC-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(140, 7, 'PR-TEC-CALC-004', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(141, 7, 'PR-TEC-CALC-005', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(142, 7, 'PR-TEC-CALC-006', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(143, 7, 'PR-TEC-CALC-007', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(144, 7, 'PR-TEC-CALC-008', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(145, 8, 'PR-TEC-WEBCAM-001', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(146, 8, 'PR-TEC-WEBCAM-002', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(147, 8, 'PR-TEC-WEBCAM-003', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(148, 9, 'PR-ACC-CARGADOR-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(149, 9, 'PR-ACC-CARGADOR-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(150, 9, 'PR-ACC-CARGADOR-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(151, 9, 'PR-ACC-CARGADOR-004', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(152, 9, 'PR-ACC-CARGADOR-005', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(153, 9, 'PR-ACC-CARGADOR-006', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(154, 9, 'PR-ACC-CARGADOR-007', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(155, 9, 'PR-ACC-CARGADOR-008', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(156, 11, 'PR-TEC-PC-001', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(157, 11, 'PR-TEC-PC-002', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(158, 11, 'PR-TEC-PC-003', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(159, 11, 'PR-TEC-PC-004', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(160, 20, 'PR-TEC-MONITOR-001', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(161, 20, 'PR-TEC-MONITOR-002', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(162, 20, 'PR-TEC-MONITOR-003', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(163, 20, 'PR-TEC-MONITOR-004', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(164, 22, 'PR-ACC-MOUSE-001', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(165, 22, 'PR-ACC-MOUSE-002', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(166, 22, 'PR-ACC-MOUSE-003', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(167, 22, 'PR-ACC-MOUSE-004', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(168, 22, 'PR-ACC-MOUSE-005', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(169, 22, 'PR-ACC-MOUSE-006', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(170, 22, 'PR-ACC-MOUSE-007', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(171, 22, 'PR-ACC-MOUSE-008', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(172, 22, 'PR-ACC-MOUSE-009', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(173, 22, 'PR-ACC-MOUSE-010', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(174, 24, 'PR-TEC-PARLANTE-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(175, 24, 'PR-TEC-PARLANTE-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', ''),
(176, 32, 'PR-TAB-SAMSUNG-001', 'SER-PR-TAB-SAMSUNG-001', '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(177, 32, 'PR-TAB-SAMSUNG-002', 'SER-PR-TAB-SAMSUNG-002', '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(178, 32, 'PR-TAB-SAMSUNG-003', 'SER-PR-TAB-SAMSUNG-003', '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', ''),
(179, 32, 'PR-TAB-SAMSUNG-004', 'SER-PR-TAB-SAMSUNG-004', '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', '');

INSERT INTO `categoria_recurso` (`id_categoria`, `nombre`, `descripcion`) VALUES
(1, 'Equipos', 'Equipos de cómputo y audiovisuales'),
(2, 'Libros', 'Bibliografía de la escuela'),
(3, 'Deportes', 'Implementos deportivos y recreativos'),
(4, 'Mobiliario', 'Mesas, sillas y mobiliario de uso común'),
(5, 'Juegos de mesa', 'Juegos para actividades y préstamo'),
(6, 'Tecnología y accesorios', 'Periféricos y equipos complementarios');

INSERT INTO `detalle_prestamo` (`id_detalle`, `id_prestamo`, `id_bien_ref`, `id_politica_ref`, `fecha_limite_devolucion`, `estado_entrega`, `estado_devolucion`, `observaciones`) VALUES
(1, 1, 1, 24, '2026-10-31 00:38:04', 'PRESTADO', NULL, ''),
(2, 2, 3, 26, '2026-11-06 18:38:04', 'PRESTADO', 'DISPONIBLE', '');

INSERT INTO `devolucion` (`id_devolucion`, `id_detalle_ref`, `fecha`, `observaciones`, `dni_encargado`) VALUES
(1, 2, '2026-10-29 18:38:04', 'Ejemplar recibido sin daños', '98000002');

INSERT INTO `docente` (`codigo_docente`, `departamento_academico`, `facultad`, `escuela_profesional`, `dni`) VALUES
('DOC-PRUEBA-01', 'Ciencia de la Computación', 'Producción y Servicios', 'Ciencia de la Computación', '98000004'),
('DOC-PRB-02', 'Ciencia de la Computación', 'Producción y Servicios', 'Ciencia de la Computación', '99000013'),
('DOC-PRB-03', 'Ciencia de la Computación', 'Producción y Servicios', 'Ciencia de la Computación', '99000014');

INSERT INTO `estudiante` (`ciclo`, `semestre_academico`, `estado_matricula`, `dni`, `cui`) VALUES
(4, '2026-II', 'vigente', '02167885', '20245555'),
(2, '2026-II', 'vigente', '99000001', '20260001'),
(4, '2026-II', 'vigente', '99000002', '20260002'),
(6, '2026-II', 'vigente', '99000003', '20260003'),
(3, '2026-II', 'vigente', '99000004', '20260004'),
(5, '2026-II', 'vigente', '99000005', '20260005'),
(7, '2026-II', 'vigente', '99000006', '20260006'),
(2, '2026-II', 'vigente', '99000007', '20260007'),
(8, '2026-II', 'vigente', '99000008', '20260008'),
(4, '2026-II', 'vigente', '99000009', '20260009'),
(NULL, NULL, 'vigente', '99000010', '20260010'),
(3, '2026-II', 'vigente', '99000011', '20260011'),
(5, '2026-II', 'no_vigente', '99000012', '20260012');

INSERT INTO `historial_estado` (`id_historial_estado`, `entidad`, `id_entidad`, `estado_anterior`, `estado_nuevo`, `fecha`, `observacion`, `dni_responsable`) VALUES
(1, 'BIEN_MATERIAL', 1, 'DISPONIBLE', 'PRESTADO', '2026-10-30 16:38:04', 'Entrega del préstamo #1', '98000002'),
(2, 'BIEN_MATERIAL', 3, 'DISPONIBLE', 'PRESTADO', '2026-10-23 18:38:04', 'Entrega del préstamo #2', '98000002'),
(3, 'BIEN_MATERIAL', 3, 'PRESTADO', 'DISPONIBLE', '2026-10-29 18:38:04', 'Recepción del préstamo #2', '98000002'),
(4, 'BIEN_MATERIAL', 5, 'DISPONIBLE', 'MANTENIMIENTO', '2026-10-28 18:38:04', 'Reparación de encuadernación', '98000001'),
(5, 'RESERVA', 1, NULL, 'EN_ESPERA', '2026-10-30 18:38:04', 'Solicitud registrada', '99000001'),
(6, 'RESERVA', 2, NULL, 'EN_ESPERA', '2026-10-30 18:38:04', 'Solicitud registrada', '99000002');

INSERT INTO `historial_prestamo` (`id_historial`, `id_prestamo`, `estado_anterior`, `estado_nuevo`, `fecha`, `observacion`, `dni_responsable`) VALUES
(1, 1, NULL, 'ACTIVO', '2026-10-30 16:38:04', 'Entrega registrada', '98000002'),
(2, 2, NULL, 'ACTIVO', '2026-10-23 18:38:04', 'Entrega registrada', '98000002'),
(3, 2, 'ACTIVO', 'DEVUELTO', '2026-10-29 18:38:04', 'Devolución completa', '98000002');

INSERT INTO `permiso` (`id_permiso`, `codigo`, `descripcion`) VALUES
(1, 'PERSONAS_CONSULTAR', 'Consultar el directorio de personas'),
(2, 'PERSONAS_GESTIONAR', 'Registrar, editar y desactivar personas'),
(3, 'USUARIOS_GESTIONAR', 'Crear cuentas y asignar roles'),
(4, 'ROLES_CONSULTAR', 'Consultar los roles y sus permisos'),
(5, 'ROLES_GESTIONAR', 'Asignar y revocar permisos de los roles'),
(6, 'CATALOGO_CONSULTAR', 'Consultar el catálogo de recursos'),
(7, 'PRESTAMOS_PROPIOS_CONSULTAR', 'Consultar préstamos propios'),
(8, 'RESERVAS_PROPIAS_GESTIONAR', 'Solicitar préstamos y gestionar reservas propias'),
(9, 'PRESTAMOS_GESTIONAR', 'Registrar entregas y devoluciones'),
(10, 'RECURSOS_GESTIONAR', 'Gestionar recursos y bienes'),
(11, 'POLITICAS_GESTIONAR', 'Gestionar políticas de préstamo');

INSERT INTO `persona` (`nombres`, `apellidos`, `dni`, `telefono`, `correo`, `estado`) VALUES
('Ana', 'Torres', '02167885', '', 'ana@ejemplo.gmail', 'ACTIVA'),
('Administrador', 'Prueba', '98000001', '', 'admin@ejemplo.gmail', 'ACTIVA'),
('Carlos', 'Rojas', '98000002', '', 'encargado@ejemplo.gmail', 'ACTIVA'),
('Lucía', 'Vargas', '98000004', '', 'lucia@ejemplo.gmail', 'ACTIVA'),
('Diego', 'Huamán Quispe', '99000001', '999000001', 'diego.huaman@ejemplo.gmail', 'ACTIVA'),
('Camila', 'Rojas Medina', '99000002', '999000002', 'camila.rojas@ejemplo.gmail', 'ACTIVA'),
('Jorge', 'Mamani Apaza', '99000003', '999000003', 'jorge.mamani@ejemplo.gmail', 'ACTIVA'),
('Valeria', 'Condori Paredes', '99000004', '999000004', 'valeria.condori@ejemplo.gmail', 'ACTIVA'),
('Mateo', 'Chávez Flores', '99000005', '999000005', 'mateo.chavez@ejemplo.gmail', 'ACTIVA'),
('Andrea', 'Quispe Salas', '99000006', '999000006', 'andrea.quispe@ejemplo.gmail', 'ACTIVA'),
('Bruno', 'Vargas Cárdenas', '99000007', '999000007', 'bruno.vargas@ejemplo.gmail', 'ACTIVA'),
('Fernanda', 'Paredes Soto', '99000008', '999000008', 'fernanda.paredes@ejemplo.gmail', 'ACTIVA'),
('Renato', 'Arias López', '99000009', '999000009', 'renato.arias@ejemplo.gmail', 'ACTIVA'),
('Micaela', 'Sánchez Ríos', '99000010', '999000010', 'micaela.sanchez@ejemplo.gmail', 'ACTIVA'),
('Gabriel', 'Medina Torres', '99000011', '999000011', 'gabriel.medina@ejemplo.gmail', 'ACTIVA'),
('Luciana', 'Salas Núñez', '99000012', '999000012', 'luciana.salas@ejemplo.gmail', 'ACTIVA'),
('Patricia', 'Lazo Cuentas', '99000013', '999000013', 'patricia.lazo@ejemplo.gmail', 'ACTIVA'),
('Roberto', 'Núñez Poma', '99000014', '999000014', 'roberto.nunez@ejemplo.gmail', 'ACTIVA'),
('Mariana', 'Peña Salazar', '99000015', '999000015', 'mariana.pena@ejemplo.gmail', 'ACTIVA');

INSERT INTO `politica_prestamo` (`id_politica`, `tipo_persona`, `plazo_maximo`, `unidad_plazo`, `permite_salida`, `id_categoria_ref`, `vigente`) VALUES
(22, 'ADMINISTRATIVO', 8, 'HORAS', 0, 1, 0),
(23, 'DOCENTE', 5, 'DIAS', 1, 1, 0),
(24, 'ESTUDIANTE', 8, 'HORAS', 0, 1, 0),
(25, 'ADMINISTRATIVO', 7, 'DIAS', 1, 2, 0),
(26, 'DOCENTE', 14, 'DIAS', 1, 2, 0),
(27, 'ESTUDIANTE', 7, 'DIAS', 1, 2, 0),
(28, 'ADMINISTRATIVO', 4, 'HORAS', 0, 1, 0),
(29, 'DOCENTE', 4, 'HORAS', 0, 1, 0),
(30, 'ESTUDIANTE', 4, 'HORAS', 0, 1, 0),
(31, 'ADMINISTRATIVO', 3, 'HORAS', 0, 5, 0),
(32, 'DOCENTE', 3, 'HORAS', 0, 5, 0),
(33, 'ESTUDIANTE', 3, 'HORAS', 0, 5, 0),
(34, 'ADMINISTRATIVO', 7, 'DIAS', 1, 2, 0),
(35, 'DOCENTE', 14, 'DIAS', 1, 2, 0),
(36, 'ESTUDIANTE', 7, 'DIAS', 1, 2, 0),
(37, 'ADMINISTRATIVO', 3, 'HORAS', 0, 6, 0),
(38, 'DOCENTE', 3, 'HORAS', 0, 6, 0),
(39, 'ESTUDIANTE', 3, 'HORAS', 0, 6, 0),
(40, 'ADMINISTRATIVO', 3, 'HORAS', 0, 6, 0),
(41, 'DOCENTE', 3, 'HORAS', 0, 6, 0),
(42, 'ESTUDIANTE', 3, 'HORAS', 0, 6, 0),
(43, 'ADMINISTRATIVO', 3, 'HORAS', 0, 6, 0),
(44, 'DOCENTE', 3, 'HORAS', 0, 6, 0),
(45, 'ESTUDIANTE', 3, 'HORAS', 0, 6, 0),
(46, 'ADMINISTRATIVO', 4, 'HORAS', 0, 6, 0),
(47, 'DOCENTE', 4, 'HORAS', 0, 6, 0),
(48, 'ESTUDIANTE', 4, 'HORAS', 0, 6, 0),
(49, 'ADMINISTRATIVO', 3, 'HORAS', 0, 5, 0),
(50, 'DOCENTE', 3, 'HORAS', 0, 5, 0),
(51, 'ESTUDIANTE', 3, 'HORAS', 0, 5, 0),
(52, 'ADMINISTRATIVO', 3, 'HORAS', 0, 6, 0),
(53, 'DOCENTE', 3, 'HORAS', 0, 6, 0),
(54, 'ESTUDIANTE', 3, 'HORAS', 0, 6, 0),
(55, 'ADMINISTRATIVO', 3, 'HORAS', 0, 5, 0),
(56, 'DOCENTE', 3, 'HORAS', 0, 5, 0),
(57, 'ESTUDIANTE', 3, 'HORAS', 0, 5, 0),
(58, 'ADMINISTRATIVO', 7, 'DIAS', 1, 2, 0),
(59, 'DOCENTE', 14, 'DIAS', 1, 2, 0),
(60, 'ESTUDIANTE', 7, 'DIAS', 1, 2, 0),
(61, 'ADMINISTRATIVO', 7, 'DIAS', 1, 2, 0),
(62, 'DOCENTE', 14, 'DIAS', 1, 2, 0),
(63, 'ESTUDIANTE', 7, 'DIAS', 1, 2, 0),
(64, 'ADMINISTRATIVO', 7, 'DIAS', 1, 2, 0),
(65, 'DOCENTE', 14, 'DIAS', 1, 2, 0),
(66, 'ESTUDIANTE', 7, 'DIAS', 1, 2, 0),
(67, 'ADMINISTRATIVO', 3, 'HORAS', 0, 5, 0),
(68, 'DOCENTE', 3, 'HORAS', 0, 5, 0),
(69, 'ESTUDIANTE', 3, 'HORAS', 0, 5, 0),
(70, 'ADMINISTRATIVO', 7, 'DIAS', 1, 2, 0),
(71, 'DOCENTE', 14, 'DIAS', 1, 2, 0),
(72, 'ESTUDIANTE', 7, 'DIAS', 1, 2, 0),
(73, 'ADMINISTRATIVO', 3, 'HORAS', 0, 3, 0),
(74, 'DOCENTE', 3, 'HORAS', 0, 3, 0),
(75, 'ESTUDIANTE', 3, 'HORAS', 0, 3, 0),
(76, 'ADMINISTRATIVO', 3, 'HORAS', 0, 4, 0),
(77, 'DOCENTE', 3, 'HORAS', 0, 4, 0),
(78, 'ESTUDIANTE', 3, 'HORAS', 0, 4, 0),
(79, 'ADMINISTRATIVO', 3, 'HORAS', 0, 6, 0),
(80, 'DOCENTE', 3, 'HORAS', 0, 6, 0),
(81, 'ESTUDIANTE', 3, 'HORAS', 0, 6, 0),
(82, 'ADMINISTRATIVO', 3, 'HORAS', 0, 5, 0),
(83, 'DOCENTE', 3, 'HORAS', 0, 5, 0),
(84, 'ESTUDIANTE', 3, 'HORAS', 0, 5, 0),
(85, 'ADMINISTRATIVO', 4, 'HORAS', 0, 6, 0),
(86, 'DOCENTE', 4, 'HORAS', 0, 6, 0),
(87, 'ESTUDIANTE', 4, 'HORAS', 0, 6, 0),
(88, 'ADMINISTRATIVO', 3, 'HORAS', 0, 3, 0),
(89, 'DOCENTE', 3, 'HORAS', 0, 3, 0),
(90, 'ESTUDIANTE', 3, 'HORAS', 0, 3, 0),
(91, 'ADMINISTRATIVO', 3, 'HORAS', 0, 6, 0),
(92, 'DOCENTE', 3, 'HORAS', 0, 6, 0),
(93, 'ESTUDIANTE', 3, 'HORAS', 0, 6, 0),
(94, 'ADMINISTRATIVO', 3, 'HORAS', 0, 3, 0),
(95, 'DOCENTE', 3, 'HORAS', 0, 3, 0),
(96, 'ESTUDIANTE', 3, 'HORAS', 0, 3, 0),
(97, 'ADMINISTRATIVO', 3, 'HORAS', 0, 3, 0),
(98, 'DOCENTE', 3, 'HORAS', 0, 3, 0),
(99, 'ESTUDIANTE', 3, 'HORAS', 0, 3, 0),
(100, 'ADMINISTRATIVO', 7, 'DIAS', 1, 2, 0),
(101, 'DOCENTE', 14, 'DIAS', 1, 2, 0),
(102, 'ESTUDIANTE', 7, 'DIAS', 1, 2, 0),
(103, 'ADMINISTRATIVO', 7, 'DIAS', 1, 2, 0),
(104, 'DOCENTE', 14, 'DIAS', 1, 2, 0),
(105, 'ESTUDIANTE', 7, 'DIAS', 1, 2, 0),
(106, 'ADMINISTRATIVO', 7, 'DIAS', 1, 2, 0),
(107, 'DOCENTE', 14, 'DIAS', 1, 2, 0),
(108, 'ESTUDIANTE', 7, 'DIAS', 1, 2, 0),
(109, 'ADMINISTRATIVO', 3, 'HORAS', 0, 4, 0),
(110, 'DOCENTE', 3, 'HORAS', 0, 4, 0),
(111, 'ESTUDIANTE', 3, 'HORAS', 0, 4, 0),
(112, 'ADMINISTRATIVO', 7, 'DIAS', 1, 2, 0),
(113, 'DOCENTE', 14, 'DIAS', 1, 2, 0),
(114, 'ESTUDIANTE', 7, 'DIAS', 1, 2, 0),
(115, 'ADMINISTRATIVO', 8, 'HORAS', 0, 6, 0),
(116, 'DOCENTE', 5, 'DIAS', 1, 6, 0),
(117, 'ESTUDIANTE', 8, 'HORAS', 0, 6, 0),
(118, 'ADMINISTRATIVO', 7, 'DIAS', 1, 2, 1),
(119, 'ADMINISTRATIVO', 3, 'HORAS', 0, 3, 1),
(120, 'ADMINISTRATIVO', 3, 'HORAS', 0, 4, 1),
(121, 'ADMINISTRATIVO', 3, 'HORAS', 0, 5, 1),
(122, 'DOCENTE', 14, 'DIAS', 1, 2, 1),
(123, 'DOCENTE', 3, 'HORAS', 0, 3, 1),
(124, 'DOCENTE', 3, 'HORAS', 0, 4, 1),
(125, 'DOCENTE', 3, 'HORAS', 0, 5, 1),
(126, 'ESTUDIANTE', 7, 'DIAS', 1, 2, 1),
(127, 'ESTUDIANTE', 3, 'HORAS', 0, 3, 1),
(128, 'ESTUDIANTE', 3, 'HORAS', 0, 4, 1),
(129, 'ESTUDIANTE', 3, 'HORAS', 0, 5, 1);

INSERT INTO `prestamo` (`id_prestamo`, `tipo_prestamo`, `fecha_solicitud`, `fecha_entrega`, `estado`, `observaciones`, `dni_encargado`, `dni_persona`) VALUES
(1, 'INDIVIDUAL', '2026-10-30 16:38:04', '2026-10-30 16:38:04', 'ACTIVO', 'Uso dentro de la institución. Préstamo de prueba', '98000002', '02167885'),
(2, 'INDIVIDUAL', '2026-10-23 18:38:04', '2026-10-23 18:38:04', 'DEVUELTO', 'Préstamo de prueba ya recibido', '98000002', '98000004');

INSERT INTO `recurso` (`id_recurso`, `id_categoria_ref`, `nombre`, `marca`, `modelo`, `descripcion`) VALUES
(1, 1, 'Laptop Lenovo ThinkPad', 'Lenovo', 'T14', 'Laptop de laboratorio'),
(2, 2, 'Introducción a los algoritmos', 'MIT Press', 'Cuarta edición', 'Libro de consulta'),
(3, 1, 'Proyector Epson', 'Epson', 'PowerLite', 'Proyector para clases'),
(4, 5, 'Ajedrez', 'Genérico', 'Estándar', 'Juego de ajedrez completo'),
(5, 2, 'Arquitectura de computadores', 'Morgan Kaufmann', 'Sexta edición', 'Texto de arquitectura de computadoras'),
(6, 6, 'Cable HDMI', 'Ugreen', '2 metros', 'Cable para conexión audiovisual'),
(7, 6, 'Calculadora científica', 'Casio', 'fx-991', 'Calculadora para uso académico'),
(8, 6, 'Cámara web', 'Logitech', 'C920', 'Cámara para clases virtuales'),
(9, 6, 'Cargador USB-C', 'Anker', '65 W', 'Cargador para equipos compatibles'),
(10, 5, 'Catan', 'Devir', 'Básico', 'Juego de estrategia y recursos'),
(11, 6, 'Computadora de escritorio', 'HP', 'ProDesk', 'Equipo para laboratorio'),
(12, 5, 'Dominó', 'Genérico', '28 fichas', 'Juego de dominó'),
(13, 2, 'Estructuras de datos', 'Pearson', 'Tercera edición', 'Texto de estructuras y algoritmos'),
(14, 2, 'Fundamentos de bases de datos', 'Pearson', 'Séptima edición', 'Texto de diseño y gestión de bases de datos'),
(15, 2, 'Ingeniería de software', 'McGraw-Hill', 'Novena edición', 'Texto de procesos de software'),
(16, 5, 'Jenga', 'Hasbro', 'Clásico', 'Juego de bloques de madera'),
(17, 2, 'Matemática discreta', 'McGraw-Hill', 'Octava edición', 'Texto de matemática discreta'),
(18, 3, 'Mesa de ping pong', 'Sport', 'Tournament', 'Mesa recreativa con red'),
(19, 4, 'Mesa de trabajo', 'Muebles Sur', '120 cm', 'Mesa de trabajo multiuso'),
(20, 6, 'Monitor LED', 'Dell', '24 pulgadas', 'Monitor para estación de trabajo'),
(21, 5, 'Monopoly', 'Hasbro', 'Clásico', 'Juego de estrategia familiar'),
(22, 6, 'Mouse óptico', 'Logitech', 'M90', 'Mouse USB para equipos de cómputo'),
(23, 3, 'Paleta de ping pong', 'Butterfly', 'Entrenamiento', 'Paleta para tenis de mesa'),
(24, 6, 'Parlante portátil', 'JBL', 'Go 3', 'Parlante para actividades académicas'),
(25, 3, 'Pelota de baloncesto', 'Molten', 'BG3800', 'Balón para básquet'),
(26, 3, 'Pelota de ping pong', 'DHS', '40 mm', 'Pelota individual de tenis de mesa'),
(27, 2, 'Python para todos', 'No Starch Press', 'Tercera edición', 'Introducción práctica a Python'),
(28, 2, 'Redes de computadoras', 'Pearson', 'Quinta edición', 'Texto de redes y comunicaciones'),
(29, 2, 'Seguridad informática', 'Pearson', 'Octava edición', 'Texto de seguridad de sistemas'),
(30, 4, 'Silla apilable', 'Muebles Sur', 'Aula', 'Silla para actividades y aulas'),
(31, 2, 'Sistemas operativos modernos', 'Pearson', 'Cuarta edición', 'Texto de sistemas operativos'),
(32, 6, 'Tablet Samsung Galaxy Tab', 'Samsung', 'Tab A8', 'Tablet para actividades académicas');

INSERT INTO `registro_fuera_servicio` (`id_registro`, `id_bien_ref`, `motivo`, `fecha_inicio`, `fecha_fin_estimada`, `fecha_fin_real`, `descripcion`, `estado`) VALUES
(1, 5, 'Reparación de encuadernación', '2026-10-28 18:38:04', '2026-11-02 18:38:04', NULL, 'Ejemplar en reparación', 'ACTIVO');

INSERT INTO `reserva` (`id_reserva`, `id_recurso_ref`, `fecha_solicitud`, `fecha_requerida`, `posicion_en_cola`, `tipo_gestion`, `observaciones`, `salida_solicitada`, `id_bien_ref`, `id_prestamo_ref`, `estado`, `dni_persona`) VALUES
(1, 2, '2026-10-30 18:38:04', '2026-10-30 18:38:04', 1, 'PRESTAMO', 'Solicitud ficticia para atención actual', 0, NULL, NULL, 'EN_ESPERA', '99000001'),
(2, 3, '2026-10-30 18:38:04', '2026-11-01 18:38:04', 1, 'RESERVA', 'Reserva ficticia para una fecha futura', 0, NULL, NULL, 'EN_ESPERA', '99000002');

-- Al crear datos de prueba, asignar el vencimiento a las solicitudes abiertas.
UPDATE reserva
SET fecha_limite_vencimiento = DATE_ADD(fecha_requerida, INTERVAL 2 DAY)
WHERE estado='EN_ESPERA' AND fecha_limite_vencimiento IS NULL;

INSERT INTO `rol` (`id_rol`, `nombre`, `descripcion`, `activo`) VALUES
(1, 'USUARIO', 'Solicita y consulta sus préstamos', 1),
(2, 'ENCARGADO_PRESTAMOS', 'Registra y corrige personas; entrega y recibe recursos', 1),
(3, 'ADMINISTRADOR', 'Gestiona recursos, personas, roles y políticas', 1);

INSERT INTO `rol_permiso` (`id_rol`, `id_permiso`) VALUES
(2, 1),
(3, 1),
(2, 2),
(3, 2),
(3, 3),
(3, 4),
(3, 5),
(1, 6),
(2, 6),
(3, 6),
(1, 7),
(2, 7),
(3, 7),
(1, 8),
(2, 8),
(3, 8),
(2, 9),
(3, 9),
(3, 10),
(3, 11);

INSERT INTO `usuario_sistema` (`id_usuario`, `id_rol_ref`, `nombre_usuario`, `contrasena_hash`, `ultimo_acceso`, `activo`, `estado_cuenta`, `dni_persona`) VALUES
(1, 3, 'admin', 'scrypt:32768:8:1$jhqyz5zQhHnufRRc$41187f6bf98ae78e7e0221856d29d8e17bf60a32e34552c7e5734f08ff017bee8d977ab06153ca966a08f70e634e4e0c83cfc4ca52e51b330b7602831af3c5a4', NULL, 1, 'ACTIVA', '98000001'),
(2, 2, 'encargado1', 'scrypt:32768:8:1$OSOfhtGAzkHFLfsT$b235f4c09cda8e8c25a44e0ffbf449f506a08cfe3a468af259a11f0ebb9b92dbae9305530e6175a88655984a0601b50e9a64fc34eab21f52964d68f65803fdd9', NULL, 1, 'ACTIVA', '98000002'),
(3, 1, 'usuario1', 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460', NULL, 1, 'ACTIVA', '02167885'),
(4, 1, 'estudiante01', 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460', NULL, 1, 'ACTIVA', '99000001'),
(5, 1, 'estudiante02', 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460', NULL, 1, 'ACTIVA', '99000002'),
(6, 1, 'estudiante03', 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460', NULL, 1, 'ACTIVA', '99000003'),
(7, 1, 'estudiante04', 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460', NULL, 1, 'ACTIVA', '99000004'),
(8, 1, 'estudiante05', 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460', NULL, 1, 'ACTIVA', '99000005'),
(9, 1, 'estudiante06', 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460', NULL, 1, 'ACTIVA', '99000006'),
(10, 1, 'estudiante07', 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460', NULL, 1, 'ACTIVA', '99000007'),
(11, 1, 'estudiante08', 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460', NULL, 1, 'ACTIVA', '99000008'),
(19, 2, 'encargado2', 'scrypt:32768:8:1$OSOfhtGAzkHFLfsT$b235f4c09cda8e8c25a44e0ffbf449f506a08cfe3a468af259a11f0ebb9b92dbae9305530e6175a88655984a0601b50e9a64fc34eab21f52964d68f65803fdd9', NULL, 1, 'ACTIVA', '99000015');

SET FOREIGN_KEY_CHECKS=1;

-- Retirar reglas anteriores sin préstamos asociados: ya no se revisan en la interfaz.
DELETE FROM politica_prestamo WHERE vigente=FALSE AND NOT EXISTS (
  SELECT 1 FROM detalle_prestamo d WHERE d.id_politica_ref=politica_prestamo.id_politica);
