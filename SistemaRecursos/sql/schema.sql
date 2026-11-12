-- Estructura del sistema de prestamos de recursos para MySQL 8.
-- Crea prestamos_escuela sin registros: personas, cuentas y catalogo vacios.
SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS prestamos_escuela
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE prestamos_escuela;

-- ESTRUCTURA DE TABLAS

-- 1. PERSONAS Y USUARIOS

CREATE TABLE IF NOT EXISTS persona (
  dni        VARCHAR(8) PRIMARY KEY CHECK (dni REGEXP '^[0-9]{8}$'),
  nombres    VARCHAR(100) NOT NULL,
  apellidos  VARCHAR(100) NOT NULL,
  telefono   VARCHAR(20),
  correo     VARCHAR(120) NOT NULL,
  estado     ENUM('ACTIVA','INACTIVA') NOT NULL DEFAULT 'ACTIVA',
  CONSTRAINT uq_persona_correo UNIQUE (correo),
  INDEX idx_persona_apellidos_nombres (apellidos, nombres)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS estudiante (
  dni               VARCHAR(8) PRIMARY KEY,
  cui               VARCHAR(8) NOT NULL CHECK (cui REGEXP '^[0-9]{8}$'),
  ciclo             INT CHECK (ciclo > 0),
  estado_matricula  ENUM('VIGENTE','NO_VIGENTE') NOT NULL DEFAULT 'VIGENTE',
  CONSTRAINT uq_estudiante_cui UNIQUE (cui),
  FOREIGN KEY (dni) REFERENCES persona(dni) ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS docente (
  dni                     VARCHAR(8) PRIMARY KEY,
  codigo_docente          VARCHAR(20) NOT NULL UNIQUE,
  departamento_academico  VARCHAR(100) NOT NULL,
  facultad                VARCHAR(100) NOT NULL,
  escuela_profesional     VARCHAR(100) NOT NULL,
  FOREIGN KEY (dni) REFERENCES persona(dni) ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS administrativo (
  dni              VARCHAR(8) PRIMARY KEY,
  codigo_empleado  VARCHAR(20) NOT NULL UNIQUE,
  area             VARCHAR(100) NOT NULL,
  FOREIGN KEY (dni) REFERENCES persona(dni) ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS rol_permiso (
  rol      ENUM('USUARIO','ENCARGADO_PRESTAMOS','ADMINISTRADOR') NOT NULL,
  permiso  VARCHAR(60) NOT NULL,
  PRIMARY KEY (rol, permiso)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS usuario_sistema (
  id_usuario      INT AUTO_INCREMENT PRIMARY KEY,
  dni_persona     VARCHAR(8) NOT NULL UNIQUE,
  nombre_usuario  VARCHAR(50) NOT NULL UNIQUE,
  contrasena_hash VARCHAR(255) NOT NULL,
  rol             ENUM('USUARIO','ENCARGADO_PRESTAMOS','ADMINISTRADOR') NOT NULL DEFAULT 'USUARIO',
  estado_cuenta   ENUM('ACTIVA','INACTIVA','BLOQUEADA') NOT NULL DEFAULT 'ACTIVA',
  ultimo_acceso   DATETIME,
  FOREIGN KEY (dni_persona) REFERENCES persona(dni) ON UPDATE CASCADE
) ENGINE=InnoDB;

-- 2. RECURSOS Y BIENES

CREATE TABLE IF NOT EXISTS categoria_recurso (
  id_categoria  INT AUTO_INCREMENT PRIMARY KEY,
  nombre        VARCHAR(80) NOT NULL UNIQUE,
  descripcion   VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS recurso (
  id_recurso        INT AUTO_INCREMENT PRIMARY KEY,
  id_categoria  INT NOT NULL,
  nombre            VARCHAR(120) NOT NULL,
  marca             VARCHAR(80),
  modelo            VARCHAR(80),
  descripcion       VARCHAR(255),
  INDEX idx_recurso_nombre (nombre),
  FOREIGN KEY (id_categoria) REFERENCES categoria_recurso(id_categoria)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bien_material (
  id_bien            INT AUTO_INCREMENT PRIMARY KEY,
  id_recurso     INT NOT NULL,
  codigo_inventario  VARCHAR(40) NOT NULL UNIQUE,
  numero_serie       VARCHAR(60),
  fecha_adquisicion  DATE NULL,
  estado             ENUM('DISPONIBLE','PRESTADO','RESERVADO','DANADO','MANTENIMIENTO','PERDIDO')
                     NOT NULL DEFAULT 'DISPONIBLE',
  ubicacion          VARCHAR(120),
  descripcion_bien   VARCHAR(255) NULL,
  INDEX idx_bien_estado_recurso_codigo (estado, id_recurso, codigo_inventario),
  INDEX idx_bien_recurso_codigo (id_recurso, codigo_inventario),
  FOREIGN KEY (id_recurso) REFERENCES recurso(id_recurso)
) ENGINE=InnoDB;



-- 3. CONTROL: REGLAS DEL SERVICIO

CREATE TABLE IF NOT EXISTS configuracion_general (
  id_configuracion TINYINT PRIMARY KEY CHECK (id_configuracion=1),
  hora_apertura TIME NOT NULL,
  hora_cierre TIME NOT NULL,
  plazo_espera INT NOT NULL,
  unidad_espera ENUM('HORAS','DIAS') NOT NULL DEFAULT 'DIAS',
  plazo_retiro INT NOT NULL,
  unidad_retiro ENUM('HORAS','DIAS') NOT NULL DEFAULT 'HORAS',
  CHECK (hora_apertura >= '00:00:00' AND hora_apertura < hora_cierre AND hora_cierre < '24:00:00'),
  CHECK (plazo_espera BETWEEN 1 AND CASE WHEN unidad_espera='HORAS' THEN 720 ELSE 30 END),
  CHECK (plazo_retiro BETWEEN 1 AND CASE WHEN unidad_retiro='HORAS' THEN 720 ELSE 30 END)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS limite_articulos_prestamo (
  tipo_persona      ENUM('ESTUDIANTE','DOCENTE','ADMINISTRATIVO') PRIMARY KEY,
  maximo_articulos  INT NULL CHECK (maximo_articulos > 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS politica_prestamo (
  id_politica               INT AUTO_INCREMENT PRIMARY KEY,
  tipo_persona              ENUM('ESTUDIANTE','DOCENTE','ADMINISTRATIVO') NOT NULL,
  id_categoria            INT NOT NULL,
  plazo_maximo              INT NOT NULL CHECK (plazo_maximo > 0),
  unidad_plazo              ENUM('HORAS','DIAS') NOT NULL,
  permite_salida            BOOLEAN NOT NULL DEFAULT FALSE,
  vigente                   BOOLEAN NOT NULL DEFAULT TRUE,
  categoria_vigente         INT GENERATED ALWAYS AS (CASE WHEN vigente THEN id_categoria ELSE NULL END) STORED,
  UNIQUE KEY uq_politica_persona_categoria_vigente (tipo_persona, categoria_vigente),
  FOREIGN KEY (id_categoria) REFERENCES categoria_recurso(id_categoria)
) ENGINE=InnoDB;

-- 4. PRESTAMOS, RESERVAS Y DEVOLUCIONES

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
  id_detalle INT AUTO_INCREMENT PRIMARY KEY,
  id_prestamo INT NOT NULL,
  id_bien INT NOT NULL,
  id_politica INT NOT NULL,
  fecha_limite_devolucion DATETIME NOT NULL,
  condicion_entrega ENUM('BUENO','DANADO') NOT NULL DEFAULT 'BUENO',
  observaciones_entrega VARCHAR(255),
  fecha_devolucion DATETIME NULL,
  dni_encargado_devolucion VARCHAR(8) NULL,
  condicion_devolucion ENUM('BUENO','DANADO') NULL,
  observaciones_devolucion VARCHAR(255) NULL,
  UNIQUE (id_prestamo,id_bien),
  INDEX idx_detalle_vencimiento(fecha_devolucion,fecha_limite_devolucion,id_prestamo),
  CHECK (
    (fecha_devolucion IS NULL AND condicion_devolucion IS NULL
      AND observaciones_devolucion IS NULL)
    OR (fecha_devolucion IS NOT NULL AND condicion_devolucion IS NOT NULL)
  ),
  FOREIGN KEY (id_prestamo) REFERENCES prestamo(id_prestamo) ON DELETE CASCADE,
  FOREIGN KEY (id_bien) REFERENCES bien_material(id_bien),
  FOREIGN KEY (id_politica) REFERENCES politica_prestamo(id_politica),
  FOREIGN KEY (dni_encargado_devolucion) REFERENCES persona(dni) ON UPDATE CASCADE
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

CREATE TABLE IF NOT EXISTS reserva (
  id_reserva        INT AUTO_INCREMENT PRIMARY KEY,
  dni_persona    VARCHAR(8) NOT NULL,
  id_recurso    INT NOT NULL,
  fecha_solicitud   DATETIME NOT NULL,
  fecha_requerida   DATETIME NOT NULL,
  fecha_preparacion DATETIME NULL,
  fecha_limite_vencimiento DATETIME NULL,
  tipo_gestion      ENUM('PRESTAMO','RESERVA') NOT NULL DEFAULT 'RESERVA',
  observaciones     VARCHAR(220) NOT NULL DEFAULT '',
  salida_solicitada BOOLEAN NOT NULL DEFAULT FALSE,
  id_bien       INT NULL,
  id_prestamo_ref   INT NULL,
  estado            ENUM('EN_ESPERA','LISTA_PARA_RETIRO','ATENDIDA','CANCELADA','EXPIRADA','RECHAZADA') NOT NULL DEFAULT 'EN_ESPERA',
  INDEX idx_reserva_cola (id_recurso,estado,fecha_solicitud,id_reserva),
  INDEX idx_reserva_persona_estado (dni_persona,estado),
  INDEX idx_reserva_vencimiento (estado,fecha_limite_vencimiento,id_reserva),
  FOREIGN KEY (dni_persona) REFERENCES persona(dni) ON UPDATE CASCADE,
  FOREIGN KEY (id_recurso) REFERENCES recurso(id_recurso),
  CONSTRAINT fk_reserva_bien FOREIGN KEY (id_bien) REFERENCES bien_material(id_bien),
  CONSTRAINT fk_reserva_prestamo FOREIGN KEY (id_prestamo_ref) REFERENCES prestamo(id_prestamo)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ampliacion_prestamo (
  id_ampliacion          INT AUTO_INCREMENT PRIMARY KEY,
  id_detalle         INT NOT NULL,
  fecha_solicitud        DATETIME NOT NULL,
  fecha_limite_anterior  DATETIME NOT NULL,
  fecha_limite_nueva     DATETIME NOT NULL,
  motivo                 VARCHAR(255),
  estado                 ENUM('PENDIENTE','APROBADA','RECHAZADA') NOT NULL DEFAULT 'PENDIENTE',
  fecha_resolucion       DATETIME NULL,
  id_usuario_resolucion   INT NULL,
  observacion_resolucion  VARCHAR(255) NULL,
  INDEX idx_ampliacion_detalle_estado (id_detalle, estado),
  CHECK (fecha_limite_nueva > fecha_limite_anterior),
  FOREIGN KEY (id_usuario_resolucion) REFERENCES usuario_sistema(id_usuario),
  FOREIGN KEY (id_detalle)     REFERENCES detalle_prestamo(id_detalle) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 5. CONTROL: INCIDENCIAS Y SANCIONES

CREATE TABLE IF NOT EXISTS incidencia (
  id_incidencia   INT AUTO_INCREMENT PRIMARY KEY,
  id_detalle  INT NOT NULL,
  tipo ENUM('RETRASO','DANIO','PERDIDA') NOT NULL,
  dni_registrador VARCHAR(8) NULL,
  retraso_unico TINYINT GENERATED ALWAYS AS (CASE WHEN tipo='RETRASO' THEN 1 ELSE NULL END) STORED,
  UNIQUE (id_detalle,retraso_unico),
  descripcion     VARCHAR(255),
  fecha           DATETIME NOT NULL,
  estado          ENUM('REGISTRADA','EN_REVISION','RESUELTA') NOT NULL DEFAULT 'REGISTRADA',
  FOREIGN KEY (id_detalle) REFERENCES detalle_prestamo(id_detalle) ON DELETE CASCADE,
  FOREIGN KEY (dni_registrador) REFERENCES persona(dni) ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS sancion (
  id_sancion         INT AUTO_INCREMENT PRIMARY KEY,
  id_incidencia_ref  INT NOT NULL UNIQUE,
  motivo             VARCHAR(255) NOT NULL,
  fecha              DATETIME NOT NULL,
  descripcion        VARCHAR(255),
  estado             ENUM('ACTIVA','CUMPLIDA','LEVANTADA','ANULADA') NOT NULL DEFAULT 'ACTIVA',
  fecha_levantamiento          DATETIME NULL,
  dni_levantamiento            VARCHAR(8) NULL,
  justificacion_levantamiento  VARCHAR(255) NULL,
  FOREIGN KEY (dni_levantamiento) REFERENCES persona(dni) ON UPDATE CASCADE,
  FOREIGN KEY (id_incidencia_ref) REFERENCES incidencia(id_incidencia)
) ENGINE=InnoDB;

-- 6. HISTORIALES

CREATE TABLE IF NOT EXISTS historial_estado (
  id_historial_estado  INT AUTO_INCREMENT PRIMARY KEY,
  entidad              ENUM('BIEN_MATERIAL','RESERVA','SANCION','PRESTAMO') NOT NULL,
  id_entidad           INT NOT NULL,
  estado_anterior      VARCHAR(30),
  estado_nuevo         VARCHAR(30) NOT NULL,
  fecha                DATETIME NOT NULL,
  observacion          VARCHAR(255),
  dni_responsable   VARCHAR(8),
  INDEX (entidad, id_entidad),
  FOREIGN KEY (dni_responsable) REFERENCES persona(dni) ON UPDATE CASCADE
) ENGINE=InnoDB;
