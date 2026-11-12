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
  dni_solicitante     VARCHAR(8) NOT NULL,
  id_detalle         INT NOT NULL,
  fecha_solicitud        DATETIME NOT NULL,
  fecha_limite_anterior  DATETIME NOT NULL,
  fecha_limite_nueva     DATETIME NOT NULL,
  motivo                 VARCHAR(255),
  estado                 ENUM('PENDIENTE','APROBADA','RECHAZADA') NOT NULL DEFAULT 'PENDIENTE',
  FOREIGN KEY (dni_solicitante) REFERENCES persona(dni) ON UPDATE CASCADE,
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
  dni_persona     VARCHAR(8) NOT NULL,
  id_incidencia_ref  INT NOT NULL UNIQUE,
  motivo             VARCHAR(255) NOT NULL,
  fecha              DATETIME NOT NULL,
  descripcion        VARCHAR(255),
  estado             ENUM('ACTIVA','CUMPLIDA','LEVANTADA','ANULADA') NOT NULL DEFAULT 'ACTIVA',
  fecha_levantamiento          DATETIME NULL,
  dni_levantamiento            VARCHAR(8) NULL,
  justificacion_levantamiento  VARCHAR(255) NULL,
  FOREIGN KEY (dni_levantamiento) REFERENCES persona(dni) ON UPDATE CASCADE,
  FOREIGN KEY (dni_persona)    REFERENCES persona(dni) ON UPDATE CASCADE,
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

-- DATOS DE PRUEBA: MISMO ORDEN QUE LAS TABLAS

SET FOREIGN_KEY_CHECKS=0;

-- 1. PERSONAS Y USUARIOS

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

INSERT INTO `estudiante` (`ciclo`, `estado_matricula`, `dni`, `cui`) VALUES
(4, 'VIGENTE', '02167885', '20245555'),
(2, 'VIGENTE', '99000001', '20260001'),
(4, 'VIGENTE', '99000002', '20260002'),
(6, 'VIGENTE', '99000003', '20260003'),
(3, 'VIGENTE', '99000004', '20260004'),
(5, 'VIGENTE', '99000005', '20260005'),
(7, 'VIGENTE', '99000006', '20260006'),
(2, 'VIGENTE', '99000007', '20260007'),
(8, 'VIGENTE', '99000008', '20260008'),
(4, 'VIGENTE', '99000009', '20260009'),
(NULL, 'VIGENTE', '99000010', '20260010'),
(3, 'VIGENTE', '99000011', '20260011'),
(5, 'NO_VIGENTE', '99000012', '20260012');

INSERT INTO `docente` (`codigo_docente`, `departamento_academico`, `facultad`, `escuela_profesional`, `dni`) VALUES
('DOC-PRUEBA-01', 'Ciencia de la Computación', 'Producción y Servicios', 'Ciencia de la Computación', '98000004'),
('DOC-PRB-02', 'Ciencia de la Computación', 'Producción y Servicios', 'Ciencia de la Computación', '99000013'),
('DOC-PRB-03', 'Ciencia de la Computación', 'Producción y Servicios', 'Ciencia de la Computación', '99000014');

INSERT INTO `administrativo` (`codigo_empleado`, `area`, `dni`) VALUES
('ADM-PRUEBA-01', 'Administración', '98000001'),
('ADM-PRUEBA-02', 'Préstamos', '98000002'),
('ADM-PRB-03', 'Préstamos', '99000015');

INSERT INTO rol_permiso (rol, permiso) VALUES
('ENCARGADO_PRESTAMOS', 'PERSONAS_CONSULTAR'),
('ADMINISTRADOR', 'PERSONAS_CONSULTAR'),
('ENCARGADO_PRESTAMOS', 'PERSONAS_GESTIONAR'),
('ADMINISTRADOR', 'PERSONAS_GESTIONAR'),
('ADMINISTRADOR', 'USUARIOS_GESTIONAR'),
('ADMINISTRADOR', 'ROLES_CONSULTAR'),
('ADMINISTRADOR', 'ROLES_GESTIONAR'),
('USUARIO', 'CATALOGO_CONSULTAR'),
('ENCARGADO_PRESTAMOS', 'CATALOGO_CONSULTAR'),
('ADMINISTRADOR', 'CATALOGO_CONSULTAR'),
('USUARIO', 'PRESTAMOS_PROPIOS_CONSULTAR'),
('ENCARGADO_PRESTAMOS', 'PRESTAMOS_PROPIOS_CONSULTAR'),
('ADMINISTRADOR', 'PRESTAMOS_PROPIOS_CONSULTAR'),
('USUARIO', 'RESERVAS_PROPIAS_GESTIONAR'),
('ENCARGADO_PRESTAMOS', 'RESERVAS_PROPIAS_GESTIONAR'),
('ADMINISTRADOR', 'RESERVAS_PROPIAS_GESTIONAR'),
('ENCARGADO_PRESTAMOS', 'PRESTAMOS_GESTIONAR'),
('ADMINISTRADOR', 'PRESTAMOS_GESTIONAR'),
('ADMINISTRADOR', 'RECURSOS_GESTIONAR'),
('ADMINISTRADOR', 'POLITICAS_GESTIONAR');

INSERT INTO `usuario_sistema` (`id_usuario`, `rol`, `nombre_usuario`, `contrasena_hash`, `ultimo_acceso`, `estado_cuenta`, `dni_persona`) VALUES
(1, 'ADMINISTRADOR', 'admin', 'scrypt:32768:8:1$jhqyz5zQhHnufRRc$41187f6bf98ae78e7e0221856d29d8e17bf60a32e34552c7e5734f08ff017bee8d977ab06153ca966a08f70e634e4e0c83cfc4ca52e51b330b7602831af3c5a4', NULL, 'ACTIVA', '98000001'),
(2, 'ENCARGADO_PRESTAMOS', 'encargado1', 'scrypt:32768:8:1$OSOfhtGAzkHFLfsT$b235f4c09cda8e8c25a44e0ffbf449f506a08cfe3a468af259a11f0ebb9b92dbae9305530e6175a88655984a0601b50e9a64fc34eab21f52964d68f65803fdd9', NULL, 'ACTIVA', '98000002'),
(3, 'USUARIO', 'usuario1', 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460', NULL, 'ACTIVA', '02167885'),
(4, 'USUARIO', 'estudiante01', 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460', NULL, 'ACTIVA', '99000001'),
(5, 'USUARIO', 'estudiante02', 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460', NULL, 'ACTIVA', '99000002'),
(6, 'USUARIO', 'estudiante03', 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460', NULL, 'ACTIVA', '99000003'),
(7, 'USUARIO', 'estudiante04', 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460', NULL, 'ACTIVA', '99000004'),
(8, 'USUARIO', 'estudiante05', 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460', NULL, 'ACTIVA', '99000005'),
(9, 'USUARIO', 'estudiante06', 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460', NULL, 'ACTIVA', '99000006'),
(10, 'USUARIO', 'estudiante07', 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460', NULL, 'ACTIVA', '99000007'),
(11, 'USUARIO', 'estudiante08', 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460', NULL, 'ACTIVA', '99000008'),
(19, 'ENCARGADO_PRESTAMOS', 'encargado2', 'scrypt:32768:8:1$OSOfhtGAzkHFLfsT$b235f4c09cda8e8c25a44e0ffbf449f506a08cfe3a468af259a11f0ebb9b92dbae9305530e6175a88655984a0601b50e9a64fc34eab21f52964d68f65803fdd9', NULL, 'ACTIVA', '99000015');

-- 2. RECURSOS Y BIENES

INSERT INTO `categoria_recurso` (`id_categoria`, `nombre`, `descripcion`) VALUES
(1, 'Equipos', 'Equipos de cómputo y audiovisuales'),
(2, 'Libros', 'Bibliografía de la escuela'),
(3, 'Deportes', 'Implementos deportivos y recreativos'),
(4, 'Mobiliario', 'Mesas, sillas y mobiliario de uso común'),
(5, 'Juegos de mesa', 'Juegos para actividades y préstamo'),
(6, 'Tecnología y accesorios', 'Periféricos y equipos complementarios');

INSERT INTO `recurso` (`id_recurso`, `id_categoria`, `nombre`, `marca`, `modelo`, `descripcion`) VALUES
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

INSERT INTO `bien_material` (`id_bien`, `id_recurso`, `codigo_inventario`, `numero_serie`, `fecha_adquisicion`, `estado`, `ubicacion`, `descripcion_bien`) VALUES
(1, 1, 'PR-LAP-001', 'SER-LAP-001', '2026-07-02', 'PRESTADO', 'Laboratorio 1', NULL),
(2, 1, 'PR-LAP-002', 'SER-LAP-002', '2026-07-02', 'DISPONIBLE', 'Laboratorio 1', NULL),
(3, 2, 'PR-LIB-001', '', '2026-07-02', 'DISPONIBLE', 'Biblioteca', NULL),
(4, 2, 'PR-LIB-002', '', '2026-07-02', 'DISPONIBLE', 'Biblioteca', NULL),
(5, 2, 'PR-LIB-003', '', '2026-07-02', 'MANTENIMIENTO', 'Biblioteca', NULL),
(6, 3, 'PR-PRO-001', 'SER-PRO-001', '2026-07-02', 'DISPONIBLE', 'Almacén', NULL),
(7, 18, 'PR-DEP-MESA-001', NULL, '2026-08-01', 'DISPONIBLE', 'Coliseo', NULL),
(8, 23, 'PR-DEP-PALETA-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(9, 23, 'PR-DEP-PALETA-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(10, 23, 'PR-DEP-PALETA-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(11, 23, 'PR-DEP-PALETA-004', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(12, 25, 'PR-DEP-BASQ-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(13, 25, 'PR-DEP-BASQ-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(14, 25, 'PR-DEP-BASQ-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(15, 25, 'PR-DEP-BASQ-004', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(16, 25, 'PR-DEP-BASQ-005', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(17, 25, 'PR-DEP-BASQ-006', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(18, 26, 'PR-DEP-PING-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(19, 26, 'PR-DEP-PING-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(20, 26, 'PR-DEP-PING-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(21, 26, 'PR-DEP-PING-004', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(22, 26, 'PR-DEP-PING-005', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(23, 26, 'PR-DEP-PING-006', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(24, 26, 'PR-DEP-PING-007', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(25, 26, 'PR-DEP-PING-008', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(26, 26, 'PR-DEP-PING-009', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(27, 26, 'PR-DEP-PING-010', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(28, 26, 'PR-DEP-PING-011', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(29, 26, 'PR-DEP-PING-012', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(30, 26, 'PR-DEP-PING-013', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(31, 26, 'PR-DEP-PING-014', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(32, 26, 'PR-DEP-PING-015', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(33, 26, 'PR-DEP-PING-016', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(34, 26, 'PR-DEP-PING-017', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(35, 26, 'PR-DEP-PING-018', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(36, 26, 'PR-DEP-PING-019', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(37, 26, 'PR-DEP-PING-020', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(38, 26, 'PR-DEP-PING-021', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(39, 26, 'PR-DEP-PING-022', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(40, 26, 'PR-DEP-PING-023', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(41, 26, 'PR-DEP-PING-024', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(42, 4, 'PR-JUE-AJEDREZ-001', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', NULL),
(43, 4, 'PR-JUE-AJEDREZ-002', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', NULL),
(44, 4, 'PR-JUE-AJEDREZ-003', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', NULL),
(45, 10, 'PR-JUE-CATAN-001', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', NULL),
(46, 10, 'PR-JUE-CATAN-002', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', NULL),
(47, 12, 'PR-JUE-DOMINO-001', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', NULL),
(48, 12, 'PR-JUE-DOMINO-002', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', NULL),
(49, 12, 'PR-JUE-DOMINO-003', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', NULL),
(50, 16, 'PR-JUE-JENGA-001', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', NULL),
(51, 16, 'PR-JUE-JENGA-002', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', NULL),
(52, 21, 'PR-JUE-MONOPOLY-001', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', NULL),
(53, 21, 'PR-JUE-MONOPOLY-002', NULL, '2026-08-01', 'DISPONIBLE', 'Sala de estudio', NULL),
(54, 2, 'PR-LIB-004', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(55, 2, 'PR-LIB-005', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(56, 5, 'PR-LIB-AC-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(57, 5, 'PR-LIB-AC-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(58, 5, 'PR-LIB-AC-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(59, 5, 'PR-LIB-AC-004', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(60, 5, 'PR-LIB-AC-005', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(61, 13, 'PR-LIB-ED-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(62, 13, 'PR-LIB-ED-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(63, 13, 'PR-LIB-ED-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(64, 13, 'PR-LIB-ED-004', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(65, 13, 'PR-LIB-ED-005', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(66, 14, 'PR-LIB-BD-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(67, 14, 'PR-LIB-BD-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(68, 14, 'PR-LIB-BD-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(69, 14, 'PR-LIB-BD-004', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(70, 14, 'PR-LIB-BD-005', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(71, 15, 'PR-LIB-IS-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(72, 15, 'PR-LIB-IS-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(73, 15, 'PR-LIB-IS-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(74, 15, 'PR-LIB-IS-004', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(75, 15, 'PR-LIB-IS-005', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(76, 17, 'PR-LIB-MD-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(77, 17, 'PR-LIB-MD-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(78, 17, 'PR-LIB-MD-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(79, 17, 'PR-LIB-MD-004', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(80, 17, 'PR-LIB-MD-005', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(81, 27, 'PR-LIB-PY-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(82, 27, 'PR-LIB-PY-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(83, 27, 'PR-LIB-PY-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(84, 27, 'PR-LIB-PY-004', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(85, 27, 'PR-LIB-PY-005', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(86, 28, 'PR-LIB-RC-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(87, 28, 'PR-LIB-RC-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(88, 28, 'PR-LIB-RC-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(89, 28, 'PR-LIB-RC-004', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(90, 28, 'PR-LIB-RC-005', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(91, 29, 'PR-LIB-SI-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(92, 29, 'PR-LIB-SI-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(93, 29, 'PR-LIB-SI-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(94, 29, 'PR-LIB-SI-004', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(95, 29, 'PR-LIB-SI-005', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(96, 31, 'PR-LIB-SO-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(97, 31, 'PR-LIB-SO-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(98, 31, 'PR-LIB-SO-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(99, 31, 'PR-LIB-SO-004', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(100, 31, 'PR-LIB-SO-005', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(101, 19, 'PR-MOB-MESA-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(102, 19, 'PR-MOB-MESA-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(103, 19, 'PR-MOB-MESA-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(104, 19, 'PR-MOB-MESA-004', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(105, 19, 'PR-MOB-MESA-005', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(106, 19, 'PR-MOB-MESA-006', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(107, 30, 'PR-MOB-SILLA-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(108, 30, 'PR-MOB-SILLA-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(109, 30, 'PR-MOB-SILLA-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(110, 30, 'PR-MOB-SILLA-004', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(111, 30, 'PR-MOB-SILLA-005', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(112, 30, 'PR-MOB-SILLA-006', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(113, 30, 'PR-MOB-SILLA-007', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(114, 30, 'PR-MOB-SILLA-008', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(115, 30, 'PR-MOB-SILLA-009', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(116, 30, 'PR-MOB-SILLA-010', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(117, 30, 'PR-MOB-SILLA-011', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(118, 30, 'PR-MOB-SILLA-012', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(119, 30, 'PR-MOB-SILLA-013', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(120, 30, 'PR-MOB-SILLA-014', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(121, 30, 'PR-MOB-SILLA-015', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(122, 30, 'PR-MOB-SILLA-016', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(123, 30, 'PR-MOB-SILLA-017', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(124, 30, 'PR-MOB-SILLA-018', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(125, 30, 'PR-MOB-SILLA-019', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(126, 30, 'PR-MOB-SILLA-020', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(127, 6, 'PR-TEC-HDMI-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(128, 6, 'PR-TEC-HDMI-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(129, 6, 'PR-TEC-HDMI-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(130, 6, 'PR-TEC-HDMI-004', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(131, 6, 'PR-TEC-HDMI-005', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(132, 6, 'PR-TEC-HDMI-006', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(133, 6, 'PR-TEC-HDMI-007', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(134, 6, 'PR-TEC-HDMI-008', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(135, 6, 'PR-TEC-HDMI-009', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(136, 6, 'PR-TEC-HDMI-010', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(137, 7, 'PR-TEC-CALC-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(138, 7, 'PR-TEC-CALC-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(139, 7, 'PR-TEC-CALC-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(140, 7, 'PR-TEC-CALC-004', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(141, 7, 'PR-TEC-CALC-005', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(142, 7, 'PR-TEC-CALC-006', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(143, 7, 'PR-TEC-CALC-007', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(144, 7, 'PR-TEC-CALC-008', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(145, 8, 'PR-TEC-WEBCAM-001', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(146, 8, 'PR-TEC-WEBCAM-002', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(147, 8, 'PR-TEC-WEBCAM-003', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(148, 9, 'PR-ACC-CARGADOR-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(149, 9, 'PR-ACC-CARGADOR-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(150, 9, 'PR-ACC-CARGADOR-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(151, 9, 'PR-ACC-CARGADOR-004', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(152, 9, 'PR-ACC-CARGADOR-005', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(153, 9, 'PR-ACC-CARGADOR-006', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(154, 9, 'PR-ACC-CARGADOR-007', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(155, 9, 'PR-ACC-CARGADOR-008', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(156, 11, 'PR-TEC-PC-001', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(157, 11, 'PR-TEC-PC-002', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(158, 11, 'PR-TEC-PC-003', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(159, 11, 'PR-TEC-PC-004', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(160, 20, 'PR-TEC-MONITOR-001', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(161, 20, 'PR-TEC-MONITOR-002', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(162, 20, 'PR-TEC-MONITOR-003', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(163, 20, 'PR-TEC-MONITOR-004', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(164, 22, 'PR-ACC-MOUSE-001', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(165, 22, 'PR-ACC-MOUSE-002', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(166, 22, 'PR-ACC-MOUSE-003', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(167, 22, 'PR-ACC-MOUSE-004', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(168, 22, 'PR-ACC-MOUSE-005', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(169, 22, 'PR-ACC-MOUSE-006', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(170, 22, 'PR-ACC-MOUSE-007', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(171, 22, 'PR-ACC-MOUSE-008', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(172, 22, 'PR-ACC-MOUSE-009', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(173, 22, 'PR-ACC-MOUSE-010', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(174, 24, 'PR-TEC-PARLANTE-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(175, 24, 'PR-TEC-PARLANTE-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(176, 32, 'PR-TAB-SAMSUNG-001', 'SER-PR-TAB-SAMSUNG-001', '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(177, 32, 'PR-TAB-SAMSUNG-002', 'SER-PR-TAB-SAMSUNG-002', '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(178, 32, 'PR-TAB-SAMSUNG-003', 'SER-PR-TAB-SAMSUNG-003', '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(179, 32, 'PR-TAB-SAMSUNG-004', 'SER-PR-TAB-SAMSUNG-004', '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL);

-- 3. CONTROL: REGLAS DEL SERVICIO

INSERT INTO configuracion_general
(id_configuracion,hora_apertura,hora_cierre,plazo_espera,unidad_espera,plazo_retiro,unidad_retiro)
VALUES(1,'08:00:00','16:00:00',2,'DIAS',24,'HORAS')
ON DUPLICATE KEY UPDATE id_configuracion=id_configuracion;

INSERT INTO limite_articulos_prestamo(tipo_persona,maximo_articulos)
VALUES('ESTUDIANTE',NULL),('DOCENTE',NULL),('ADMINISTRATIVO',NULL)
ON DUPLICATE KEY UPDATE tipo_persona=VALUES(tipo_persona);

INSERT INTO `politica_prestamo` (`id_politica`, `tipo_persona`, `plazo_maximo`, `unidad_plazo`, `permite_salida`, `id_categoria`, `vigente`) VALUES
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

-- 4. PRESTAMOS, RESERVAS Y DEVOLUCIONES

INSERT INTO `prestamo` (`id_prestamo`, `tipo_prestamo`, `fecha_solicitud`, `fecha_entrega`, `estado`, `observaciones`, `dni_encargado`, `dni_persona`) VALUES
(1, 'INDIVIDUAL', '2026-10-30 16:38:04', '2026-10-30 16:38:04', 'ACTIVO', 'Uso dentro de la institución. Préstamo de prueba', '98000002', '02167885'),
(2, 'INDIVIDUAL', '2026-10-23 18:38:04', '2026-10-23 18:38:04', 'DEVUELTO', 'Préstamo de prueba ya recibido', '98000002', '98000004');

INSERT INTO detalle_prestamo
(id_detalle,id_prestamo,id_bien,id_politica,fecha_limite_devolucion,condicion_entrega,observaciones_entrega,
 fecha_devolucion,dni_encargado_devolucion,condicion_devolucion,observaciones_devolucion) VALUES
(1,1,1,24,'2026-10-31 00:38:04','BUENO','',NULL,NULL,NULL,NULL),
(2,2,3,26,'2026-11-06 18:38:04','BUENO','','2026-10-29 18:38:04','98000002','BUENO','Ejemplar recibido sin daños');

INSERT INTO `reserva` (`id_reserva`, `id_recurso`, `fecha_solicitud`, `fecha_requerida`, `tipo_gestion`, `observaciones`, `salida_solicitada`, `id_bien`, `id_prestamo_ref`, `estado`, `dni_persona`) VALUES
(1, 2, '2026-10-30 18:38:04', '2026-10-30 18:38:04', 'PRESTAMO', 'Solicitud ficticia para atención actual', 0, NULL, NULL, 'EN_ESPERA', '99000001'),
(2, 3, '2026-10-30 18:38:04', '2026-11-01 18:38:04', 'RESERVA', 'Reserva ficticia para una fecha futura', 0, NULL, NULL, 'EN_ESPERA', '99000002');

-- 6. HISTORIALES

INSERT INTO `historial_estado` (`id_historial_estado`, `entidad`, `id_entidad`, `estado_anterior`, `estado_nuevo`, `fecha`, `observacion`, `dni_responsable`) VALUES
(1, 'BIEN_MATERIAL', 1, 'DISPONIBLE', 'PRESTADO', '2026-10-30 16:38:04', 'Entrega del préstamo #1', '98000002'),
(2, 'BIEN_MATERIAL', 3, 'DISPONIBLE', 'PRESTADO', '2026-10-23 18:38:04', 'Entrega del préstamo #2', '98000002'),
(3, 'BIEN_MATERIAL', 3, 'PRESTADO', 'DISPONIBLE', '2026-10-29 18:38:04', 'Recepción del préstamo #2', '98000002'),
(4, 'BIEN_MATERIAL', 5, 'DISPONIBLE', 'MANTENIMIENTO', '2026-10-28 18:38:04', 'Reparación de encuadernación', '98000001'),
(5, 'RESERVA', 1, NULL, 'EN_ESPERA', '2026-10-30 18:38:04', 'Solicitud registrada', '99000001'),
(6, 'RESERVA', 2, NULL, 'EN_ESPERA', '2026-10-30 18:38:04', 'Solicitud registrada', '99000002'),
(7, 'PRESTAMO', 1, NULL, 'ACTIVO', '2026-10-30 16:38:04', 'Entrega registrada', '98000002'),
(8, 'PRESTAMO', 2, NULL, 'ACTIVO', '2026-10-23 18:38:04', 'Entrega registrada', '98000002'),
(9, 'PRESTAMO', 2, 'ACTIVO', 'DEVUELTO', '2026-10-29 18:38:04', 'Devolución completa', '98000002');

SET FOREIGN_KEY_CHECKS=1;

-- AJUSTES FINALES DE LOS DATOS DE PRUEBA

UPDATE reserva
SET fecha_limite_vencimiento = DATE_ADD(fecha_requerida, INTERVAL 2 DAY)
WHERE estado='EN_ESPERA' AND fecha_limite_vencimiento IS NULL;

DELETE FROM politica_prestamo WHERE vigente=FALSE AND NOT EXISTS (
  SELECT 1 FROM detalle_prestamo d WHERE d.id_politica=politica_prestamo.id_politica);
