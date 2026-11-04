-- Estructura del sistema de prestamos de recursos para MySQL 8.
-- Crea prestamos_escuela sin registros: personas, cuentas y catalogo vacios.
SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS prestamos_escuela
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE prestamos_escuela;

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
