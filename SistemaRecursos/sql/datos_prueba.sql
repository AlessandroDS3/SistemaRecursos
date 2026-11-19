-- Datos ficticios para probar el sistema de recursos con MySQL 8.
-- Crea una base de demostracion aislada y carga escenarios consistentes al 12-11-2026.
-- Ejecutar SOLO en una instalacion nueva; NO ejecutar sobre una base con datos.
-- Incluye correo opcional y debe_cambiar_clave; no requiere migracion al crear la base.
-- Las cuentas de demostracion usan debe_cambiar_clave=FALSE y las claves indicadas abajo.
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
  correo     VARCHAR(120) NULL,
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
CREATE TABLE IF NOT EXISTS usuario_sistema (
  id_usuario      INT AUTO_INCREMENT PRIMARY KEY,
  dni_persona     VARCHAR(8) NOT NULL UNIQUE,
  nombre_usuario  VARCHAR(50) NOT NULL UNIQUE,
  contrasena_hash VARCHAR(255) NOT NULL,
  debe_cambiar_clave BOOLEAN NOT NULL DEFAULT FALSE,
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

-- DATOS FICTICIOS. EJECUTAR SOLO EN UNA BASE NUEVA/VACIA.
-- Fotografia de escenarios: 12 de noviembre de 2026.
START TRANSACTION;

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

-- CATALOGO: NUEVE CATEGORIAS Y EQUIPOS DE LABORATORIO MODERNOS.
INSERT INTO `categoria_recurso` (`id_categoria`, `nombre`, `descripcion`) VALUES
(1, 'Equipos informáticos', 'Laptops, computadoras, tablets y calculadoras científicas'),
(2, 'Libros', 'Bibliografía y material de consulta'),
(3, 'Deportes', 'Balones, paletas y otros implementos deportivos'),
(4, 'Mobiliario', 'Mesas, sillas y muebles de uso común'),
(5, 'Juegos de mesa', 'Ajedrez, Catan, dominó y otros juegos'),
(6, 'Accesorios tecnológicos', 'Periféricos, monitores, cables y cargadores'),
(7, 'Equipos audiovisuales', 'Proyectores, cámaras y parlantes'),
(8, 'Robótica y prototipado', 'Drones, robots, sensores, placas e impresoras 3D'),
(9, 'Realidad virtual y simulación', 'Visores y controladores de realidad virtual');

INSERT INTO `recurso` (`id_recurso`, `id_categoria`, `nombre`, `marca`, `modelo`, `descripcion`) VALUES
(1, 1, 'Laptop Lenovo ThinkPad', 'Lenovo', 'T14', 'Laptop de laboratorio'),
(2, 2, 'Introducción a los algoritmos', 'MIT Press', 'Cuarta edición', 'Libro de consulta'),
(3, 7, 'Proyector Epson', 'Epson', 'PowerLite', 'Proyector para clases'),
(4, 5, 'Ajedrez', 'Genérico', 'Estándar', 'Juego de ajedrez completo'),
(5, 2, 'Arquitectura de computadores', 'Morgan Kaufmann', 'Sexta edición', 'Texto de arquitectura de computadoras'),
(6, 6, 'Cable HDMI', 'Ugreen', '2 metros', 'Cable para conexión audiovisual'),
(7, 1, 'Calculadora científica', 'Casio', 'fx-991', 'Calculadora para uso académico'),
(8, 7, 'Cámara web', 'Logitech', 'C920', 'Cámara para clases virtuales'),
(9, 6, 'Cargador USB-C', 'Anker', '65 W', 'Cargador para equipos compatibles'),
(10, 5, 'Catan', 'Devir', 'Básico', 'Juego de estrategia y recursos'),
(11, 1, 'Computadora de escritorio', 'HP', 'ProDesk', 'Equipo para laboratorio'),
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
(24, 7, 'Parlante portátil', 'JBL', 'Go 3', 'Parlante para actividades académicas'),
(25, 3, 'Pelota de baloncesto', 'Molten', 'BG3800', 'Balón para básquet'),
(26, 3, 'Pelota de ping pong', 'DHS', '40 mm', 'Pelota individual de tenis de mesa'),
(27, 2, 'Python para todos', 'No Starch Press', 'Tercera edición', 'Introducción práctica a Python'),
(28, 2, 'Redes de computadoras', 'Pearson', 'Quinta edición', 'Texto de redes y comunicaciones'),
(29, 2, 'Seguridad informática', 'Pearson', 'Octava edición', 'Texto de seguridad de sistemas'),
(30, 4, 'Silla apilable', 'Muebles Sur', 'Aula', 'Silla para actividades y aulas'),
(31, 2, 'Sistemas operativos modernos', 'Pearson', 'Cuarta edición', 'Texto de sistemas operativos'),
(32, 1, 'Tablet Samsung Galaxy Tab', 'Samsung', 'Tab A8', 'Tablet para actividades académicas'),
(33, 8, 'Dron DJI Mini 4 Pro', 'DJI', 'Mini 4 Pro', 'Dron para prácticas de robótica y fotografía aérea supervisada'),
(34, 9, 'Visor de realidad virtual Meta Quest 3', 'Meta', 'Quest 3', 'Visor de realidad virtual para prácticas de simulación'),
(35, 8, 'Robot educativo LEGO SPIKE Prime', 'LEGO Education', 'SPIKE Prime', 'Kit para programación y robótica educativa'),
(36, 8, 'Brazo robótico Dobot Magician', 'Dobot', 'Magician', 'Brazo robótico de laboratorio'),
(37, 8, 'Kit Arduino Uno', 'Arduino', 'Uno R3', 'Kit de microcontrolador para proyectos'),
(38, 8, 'Impresora 3D Creality Ender-3 V3', 'Creality', 'Ender-3 V3', 'Impresora 3D para prototipos supervisados'),
(39, 8, 'Raspberry Pi 5', 'Raspberry Pi', '5', 'Miniordenador para proyectos de electrónica'),
(40, 7, 'Cámara de acción GoPro', 'GoPro', 'HERO', 'Equipo de registro audiovisual'),
(41, 8, 'Kit de sensores para robótica', 'Genérico', 'Sensores STEM', 'Sensores para prácticas de laboratorio'),
(42, 9, 'Controladores de realidad virtual', 'Meta', 'Touch Plus', 'Par de controladores compatible con el visor');

-- INVENTARIO MODERADO: UNA FILA POR UNIDAD FISICA.
INSERT INTO `bien_material` (`id_bien`, `id_recurso`, `codigo_inventario`, `numero_serie`, `fecha_adquisicion`, `estado`, `ubicacion`, `descripcion_bien`) VALUES
(1, 1, 'PR-LAP-001', 'SER-LAP-001', '2026-07-02', 'PRESTADO', 'Laboratorio 1', NULL),
(2, 1, 'PR-LAP-002', 'SER-LAP-002', '2026-07-02', 'PRESTADO', 'Laboratorio 1', NULL),
(3, 2, 'PR-LIB-001', NULL, '2026-07-02', 'DISPONIBLE', 'Biblioteca', NULL),
(5, 2, 'PR-LIB-003', NULL, '2026-07-02', 'MANTENIMIENTO', 'Biblioteca', NULL),
(6, 3, 'PR-PRO-001', 'SER-PRO-001', '2026-07-02', 'DISPONIBLE', 'Almacén', NULL),
(7, 18, 'PR-DEP-MESA-001', NULL, '2026-08-01', 'PRESTADO', 'Coliseo', NULL),
(8, 23, 'PR-DEP-PALETA-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(9, 23, 'PR-DEP-PALETA-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(12, 25, 'PR-DEP-BASQ-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(13, 25, 'PR-DEP-BASQ-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(14, 25, 'PR-DEP-BASQ-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(18, 26, 'PR-DEP-PING-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(19, 26, 'PR-DEP-PING-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(20, 26, 'PR-DEP-PING-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(21, 26, 'PR-DEP-PING-004', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(22, 26, 'PR-DEP-PING-005', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
(23, 26, 'PR-DEP-PING-006', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén deportivo', NULL),
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
(56, 5, 'PR-LIB-AC-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(57, 5, 'PR-LIB-AC-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(58, 5, 'PR-LIB-AC-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(61, 13, 'PR-LIB-ED-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(62, 13, 'PR-LIB-ED-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(63, 13, 'PR-LIB-ED-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(66, 14, 'PR-LIB-BD-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(67, 14, 'PR-LIB-BD-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(70, 14, 'PR-LIB-BD-005', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(71, 15, 'PR-LIB-IS-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(72, 15, 'PR-LIB-IS-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(73, 15, 'PR-LIB-IS-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(76, 17, 'PR-LIB-MD-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(77, 17, 'PR-LIB-MD-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(78, 17, 'PR-LIB-MD-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(81, 27, 'PR-LIB-PY-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(82, 27, 'PR-LIB-PY-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(83, 27, 'PR-LIB-PY-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(86, 28, 'PR-LIB-RC-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(87, 28, 'PR-LIB-RC-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(88, 28, 'PR-LIB-RC-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(91, 29, 'PR-LIB-SI-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(92, 29, 'PR-LIB-SI-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(93, 29, 'PR-LIB-SI-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(96, 31, 'PR-LIB-SO-001', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(97, 31, 'PR-LIB-SO-002', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(98, 31, 'PR-LIB-SO-003', NULL, '2026-08-01', 'DISPONIBLE', 'Biblioteca', NULL),
(101, 19, 'PR-MOB-MESA-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(102, 19, 'PR-MOB-MESA-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(103, 19, 'PR-MOB-MESA-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(107, 30, 'PR-MOB-SILLA-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(108, 30, 'PR-MOB-SILLA-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(109, 30, 'PR-MOB-SILLA-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(110, 30, 'PR-MOB-SILLA-004', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(111, 30, 'PR-MOB-SILLA-005', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(112, 30, 'PR-MOB-SILLA-006', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(127, 6, 'PR-TEC-HDMI-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(128, 6, 'PR-TEC-HDMI-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(129, 6, 'PR-TEC-HDMI-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(130, 6, 'PR-TEC-HDMI-004', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(137, 7, 'PR-TEC-CALC-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(138, 7, 'PR-TEC-CALC-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(139, 7, 'PR-TEC-CALC-003', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(140, 7, 'PR-TEC-CALC-004', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(145, 8, 'PR-TEC-WEBCAM-001', NULL, '2026-08-01', 'PRESTADO', 'Laboratorio 1', NULL),
(146, 8, 'PR-TEC-WEBCAM-002', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(147, 8, 'PR-TEC-WEBCAM-003', NULL, '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(148, 9, 'PR-ACC-CARGADOR-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(149, 9, 'PR-ACC-CARGADOR-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(151, 9, 'PR-ACC-CARGADOR-004', NULL, '2026-08-01', 'DANADO', 'Almacén', NULL),
(152, 9, 'PR-ACC-CARGADOR-005', NULL, '2026-08-01', 'PERDIDO', 'Almacén', NULL),
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
(174, 24, 'PR-TEC-PARLANTE-001', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(175, 24, 'PR-TEC-PARLANTE-002', NULL, '2026-08-01', 'DISPONIBLE', 'Almacén', NULL),
(176, 32, 'PR-TAB-SAMSUNG-001', 'SER-PR-TAB-SAMSUNG-001', '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(177, 32, 'PR-TAB-SAMSUNG-002', 'SER-PR-TAB-SAMSUNG-002', '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(178, 32, 'PR-TAB-SAMSUNG-003', 'SER-PR-TAB-SAMSUNG-003', '2026-08-01', 'PRESTADO', 'Laboratorio 1', NULL),
(179, 32, 'PR-TAB-SAMSUNG-004', 'SER-PR-TAB-SAMSUNG-004', '2026-08-01', 'DISPONIBLE', 'Laboratorio 1', NULL),
(180, 34, 'PR-VR-QUEST-001', 'VR-QUEST-001', '2026-09-01', 'DANADO', 'Laboratorio de simulación', 'Lente derecho dañado en una devolución'),
(181, 34, 'PR-VR-QUEST-002', 'VR-QUEST-002', '2026-09-01', 'RESERVADO', 'Laboratorio de simulación', 'Separado para retiro de Camila'),
(182, 33, 'PR-ROB-DRON-001', 'DJI-DRON-001', '2026-09-02', 'PRESTADO', 'Laboratorio de robótica', 'En préstamo de Jorge'),
(183, 33, 'PR-ROB-DRON-002', 'DJI-DRON-002', '2026-09-02', 'DISPONIBLE', 'Laboratorio de robótica', NULL),
(184, 35, 'PR-ROB-SPIKE-001', 'LEGO-SPIKE-001', '2026-09-02', 'PRESTADO', 'Laboratorio de robótica', 'En préstamo de Camila'),
(185, 35, 'PR-ROB-SPIKE-002', 'LEGO-SPIKE-002', '2026-09-02', 'DISPONIBLE', 'Laboratorio de robótica', NULL),
(186, 35, 'PR-ROB-SPIKE-003', 'LEGO-SPIKE-003', '2026-09-02', 'DISPONIBLE', 'Laboratorio de robótica', NULL),
(187, 36, 'PR-ROB-BRAZO-001', 'DOBOT-001', '2026-09-02', 'PRESTADO', 'Laboratorio de robótica', 'En préstamo de Mateo'),
(188, 37, 'PR-ROB-ARDUINO-001', NULL, '2026-09-03', 'PRESTADO', 'Laboratorio de robótica', 'Préstamo grupal'),
(189, 37, 'PR-ROB-ARDUINO-002', NULL, '2026-09-03', 'DISPONIBLE', 'Laboratorio de robótica', NULL),
(190, 38, 'PR-ROB-IMP3D-001', 'ENDER-3-001', '2026-09-03', 'DISPONIBLE', 'Laboratorio de fabricación', 'Uso supervisado dentro del campus'),
(191, 39, 'PR-ROB-RPI-001', 'RPI-5-001', '2026-09-03', 'DISPONIBLE', 'Laboratorio de robótica', NULL),
(192, 39, 'PR-ROB-RPI-002', 'RPI-5-002', '2026-09-03', 'DISPONIBLE', 'Laboratorio de robótica', NULL),
(193, 40, 'PR-AV-GOPRO-001', 'GOPRO-001', '2026-09-04', 'DISPONIBLE', 'Laboratorio audiovisual', NULL),
(194, 40, 'PR-AV-GOPRO-002', 'GOPRO-002', '2026-09-04', 'DISPONIBLE', 'Laboratorio audiovisual', NULL),
(195, 41, 'PR-ROB-SENSOR-001', NULL, '2026-09-04', 'PRESTADO', 'Laboratorio de robótica', 'Préstamo grupal'),
(196, 41, 'PR-ROB-SENSOR-002', NULL, '2026-09-04', 'DISPONIBLE', 'Laboratorio de robótica', NULL),
(197, 41, 'PR-ROB-SENSOR-003', NULL, '2026-09-04', 'DISPONIBLE', 'Laboratorio de robótica', NULL),
(198, 42, 'PR-VR-CONTROL-001', NULL, '2026-09-04', 'DISPONIBLE', 'Laboratorio de simulación', NULL),
(199, 42, 'PR-VR-CONTROL-002', NULL, '2026-09-04', 'DISPONIBLE', 'Laboratorio de simulación', NULL);

-- REGLAS GENERALES Y LIMITES DEMOSTRATIVOS.
INSERT INTO `configuracion_general` (`id_configuracion`, `hora_apertura`, `hora_cierre`, `plazo_espera`, `unidad_espera`, `plazo_retiro`, `unidad_retiro`) VALUES
(1, '08:00:00', '16:00:00', 2, 'DIAS', 24, 'HORAS');

INSERT INTO `limite_articulos_prestamo` (`tipo_persona`, `maximo_articulos`) VALUES
('ESTUDIANTE', 3),
('DOCENTE', 5),
('ADMINISTRATIVO', 4);

-- POLITICAS VIGENTES POR CATEGORIA Y TIPO DE PERSONA; DOS HISTORICAS.
INSERT INTO `politica_prestamo` (`id_politica`, `tipo_persona`, `plazo_maximo`, `unidad_plazo`, `permite_salida`, `id_categoria`, `vigente`) VALUES
(24, 'ESTUDIANTE', 8, 'HORAS', 0, 1, 0),
(26, 'DOCENTE', 14, 'DIAS', 1, 2, 0),
(130, 'ESTUDIANTE', 8, 'HORAS', 0, 1, 1),
(131, 'DOCENTE', 5, 'DIAS', 1, 1, 1),
(132, 'ADMINISTRATIVO', 8, 'HORAS', 0, 1, 1),
(133, 'ESTUDIANTE', 7, 'DIAS', 1, 2, 1),
(134, 'DOCENTE', 14, 'DIAS', 1, 2, 1),
(135, 'ADMINISTRATIVO', 7, 'DIAS', 1, 2, 1),
(136, 'ESTUDIANTE', 3, 'HORAS', 0, 3, 1),
(137, 'DOCENTE', 3, 'HORAS', 0, 3, 1),
(138, 'ADMINISTRATIVO', 3, 'HORAS', 0, 3, 1),
(139, 'ESTUDIANTE', 3, 'HORAS', 0, 4, 1),
(140, 'DOCENTE', 3, 'HORAS', 0, 4, 1),
(141, 'ADMINISTRATIVO', 3, 'HORAS', 0, 4, 1),
(142, 'ESTUDIANTE', 3, 'HORAS', 0, 5, 1),
(143, 'DOCENTE', 3, 'HORAS', 0, 5, 1),
(144, 'ADMINISTRATIVO', 3, 'HORAS', 0, 5, 1),
(145, 'ESTUDIANTE', 4, 'HORAS', 0, 6, 1),
(146, 'DOCENTE', 8, 'HORAS', 0, 6, 1),
(147, 'ADMINISTRATIVO', 8, 'HORAS', 0, 6, 1),
(148, 'ESTUDIANTE', 4, 'HORAS', 0, 7, 1),
(149, 'DOCENTE', 8, 'HORAS', 0, 7, 1),
(150, 'ADMINISTRATIVO', 8, 'HORAS', 0, 7, 1),
(151, 'ESTUDIANTE', 3, 'DIAS', 0, 8, 1),
(152, 'DOCENTE', 7, 'DIAS', 0, 8, 1),
(153, 'ADMINISTRATIVO', 5, 'DIAS', 0, 8, 1),
(154, 'ESTUDIANTE', 2, 'DIAS', 0, 9, 1),
(155, 'DOCENTE', 3, 'DIAS', 0, 9, 1),
(156, 'ADMINISTRATIVO', 3, 'DIAS', 0, 9, 1);

-- OPERACIONES: PRESTAMOS CON HISTORIALES DIVERSOS.
INSERT INTO `prestamo` (`id_prestamo`, `tipo_prestamo`, `fecha_solicitud`, `fecha_entrega`, `estado`, `observaciones`, `dni_encargado`, `dni_persona`) VALUES
(1, 'INDIVIDUAL', '2026-10-30 08:00:00', '2026-10-30 08:00:00', 'VENCIDO', 'Préstamo original de laptop, vencido', '98000002', '02167885'),
(2, 'INDIVIDUAL', '2026-10-23 13:45:00', '2026-10-23 14:00:00', 'DEVUELTO', 'Préstamo original devuelto de un libro', '98000002', '98000004'),
(3, 'INDIVIDUAL', '2026-10-27 08:45:00', '2026-10-27 09:00:00', 'DEVUELTO', 'Diego: libro devuelto a tiempo', '98000002', '99000001'),
(4, 'INDIVIDUAL', '2026-11-09 08:00:00', '2026-11-09 08:00:00', 'VENCIDO', 'Diego: laptop no devuelta y sanción activa', '98000002', '99000001'),
(5, 'INDIVIDUAL', '2026-10-31 08:45:00', '2026-10-31 09:00:00', 'DEVUELTO', 'Camila: préstamo antiguo sin observaciones', '98000002', '99000002'),
(6, 'INDIVIDUAL', '2026-11-11 08:45:00', '2026-11-11 09:00:00', 'ACTIVO', 'Camila: robot educativo con ampliación pendiente', '98000002', '99000002'),
(7, 'INDIVIDUAL', '2026-11-10 08:00:00', '2026-11-10 08:00:00', 'PARCIALMENTE_DEVUELTO', 'Jorge: visor devuelto con daño, dron pendiente', '98000002', '99000003'),
(8, 'INDIVIDUAL', '2026-10-29 08:45:00', '2026-10-29 09:00:00', 'DEVUELTO', 'Jorge: devolución tardía de ajedrez, sanción levantada', '98000002', '99000003'),
(9, 'INDIVIDUAL', '2026-11-01 08:45:00', '2026-11-01 09:00:00', 'DEVUELTO', 'Valeria: libro devuelto a tiempo', '98000002', '99000004'),
(10, 'INDIVIDUAL', '2026-11-08 09:45:00', '2026-11-08 10:00:00', 'VENCIDO', 'Valeria: cámara web vencida sin devolución', '98000002', '99000004'),
(11, 'INDIVIDUAL', '2026-11-11 08:45:00', '2026-11-11 09:00:00', 'ACTIVO', 'Mateo: brazo robótico, uso supervisado', '98000002', '99000005'),
(12, 'INDIVIDUAL', '2026-11-05 08:45:00', '2026-11-05 09:00:00', 'DEVUELTO', 'Andrea: balón devuelto y reserva atendida', '98000002', '99000006'),
(13, 'INDIVIDUAL', '2026-11-06 08:00:00', '2026-11-06 08:00:00', 'DEVUELTO', 'Bruno: cargador devuelto dañado', '98000002', '99000007'),
(14, 'INDIVIDUAL', '2026-11-12 11:45:00', '2026-11-12 12:00:00', 'ACTIVO', 'Fernanda: mesa ping pong prestada hasta las 15 h', '98000002', '99000008'),
(15, 'INDIVIDUAL', '2026-11-10 08:45:00', '2026-11-10 09:00:00', 'ACTIVO', 'Docente: tablet en préstamo', '98000002', '99000013'),
(16, 'GRUPAL', '2026-11-11 09:45:00', '2026-11-11 10:00:00', 'ACTIVO', 'Andrea: préstamo grupal, dos bienes y tres participantes', '98000002', '99000006'),
(17, 'INDIVIDUAL', '2026-10-29 08:45:00', '2026-10-29 09:00:00', 'DEVUELTO', 'Camila: libro con ampliación aprobada', '98000002', '99000002'),
(18, 'INDIVIDUAL', '2026-10-19 08:45:00', '2026-10-19 09:00:00', 'DEVUELTO', 'Docente: libro devuelto', '98000002', '99000014'),
(19, 'INDIVIDUAL', '2026-11-07 08:45:00', '2026-11-07 09:00:00', 'VENCIDO', 'Bruno: cargador extraviado, sanción activa', '98000002', '99000007'),
(20, 'INDIVIDUAL', '2026-11-05 08:45:00', '2026-11-05 09:00:00', 'DEVUELTO', 'Renato: devolución normal de ajedrez', '98000002', '99000009');

INSERT INTO `detalle_prestamo` (`id_detalle`, `id_prestamo`, `id_bien`, `id_politica`, `fecha_limite_devolucion`, `condicion_entrega`, `observaciones_entrega`, `fecha_devolucion`, `dni_encargado_devolucion`, `condicion_devolucion`, `observaciones_devolucion`) VALUES
(1, 1, 1, 24, '2026-10-30 16:00:00', 'BUENO', 'Entrega con ficha de control', NULL, NULL, NULL, NULL),
(2, 2, 3, 26, '2026-11-06 14:00:00', 'BUENO', 'Entrega con ficha de control', '2026-10-29 14:00:00', '98000002', 'BUENO', 'Ejemplar recibido sin daños'),
(3, 3, 61, 133, '2026-11-03 09:00:00', 'BUENO', 'Entrega con ficha de control', '2026-10-30 10:00:00', '98000002', 'BUENO', 'Libro completo'),
(4, 4, 2, 130, '2026-11-09 16:00:00', 'BUENO', 'Entrega con ficha de control', NULL, NULL, NULL, NULL),
(5, 5, 66, 133, '2026-11-07 09:00:00', 'BUENO', 'Entrega con ficha de control', '2026-11-02 11:00:00', '98000002', 'BUENO', 'Libro completo'),
(6, 6, 184, 151, '2026-11-14 09:00:00', 'BUENO', 'Entrega con ficha de control', NULL, NULL, NULL, NULL),
(7, 7, 180, 154, '2026-11-12 08:00:00', 'BUENO', 'Entrega con ficha de control', '2026-11-11 10:00:00', '98000002', 'DANADO', 'Lente derecho dañado, informe de daño'),
(8, 7, 182, 151, '2026-11-13 08:00:00', 'BUENO', 'Entrega con ficha de control', NULL, NULL, NULL, NULL),
(9, 8, 42, 142, '2026-10-29 12:00:00', 'BUENO', 'Entrega con ficha de control', '2026-10-30 10:00:00', '98000002', 'BUENO', 'Un día después del plazo'),
(10, 9, 54, 133, '2026-11-08 09:00:00', 'BUENO', 'Entrega con ficha de control', '2026-11-03 10:00:00', '98000002', 'BUENO', 'Sin observaciones'),
(11, 10, 145, 148, '2026-11-08 14:00:00', 'BUENO', 'Entrega con ficha de control', NULL, NULL, NULL, NULL),
(12, 11, 187, 151, '2026-11-14 09:00:00', 'BUENO', 'Entrega con ficha de control', NULL, NULL, NULL, NULL),
(13, 12, 12, 136, '2026-11-05 12:00:00', 'BUENO', 'Entrega con ficha de control', '2026-11-05 11:00:00', '98000002', 'BUENO', 'Balón sin daños'),
(14, 13, 151, 145, '2026-11-06 12:00:00', 'BUENO', 'Entrega con ficha de control', '2026-11-06 11:00:00', '98000002', 'DANADO', 'Conector del cargador dañado'),
(15, 14, 7, 136, '2026-11-12 15:00:00', 'BUENO', 'Entrega con ficha de control', NULL, NULL, NULL, NULL),
(16, 15, 178, 131, '2026-11-15 09:00:00', 'BUENO', 'Entrega con ficha de control', NULL, NULL, NULL, NULL),
(17, 16, 188, 151, '2026-11-14 10:00:00', 'BUENO', 'Entrega con ficha de control', NULL, NULL, NULL, NULL),
(18, 16, 195, 151, '2026-11-14 10:00:00', 'BUENO', 'Entrega con ficha de control', NULL, NULL, NULL, NULL),
(19, 17, 70, 133, '2026-11-07 09:00:00', 'BUENO', 'Entrega con ficha de control', '2026-11-06 11:00:00', '98000002', 'BUENO', 'Devolución dentro del plazo ampliado'),
(20, 18, 86, 134, '2026-11-02 09:00:00', 'BUENO', 'Entrega con ficha de control', '2026-10-26 12:00:00', '98000002', 'BUENO', 'Ejemplar bien conservado'),
(21, 19, 152, 145, '2026-11-07 13:00:00', 'BUENO', 'Entrega con ficha de control', NULL, NULL, NULL, NULL),
(22, 20, 43, 142, '2026-11-05 12:00:00', 'BUENO', 'Entrega con ficha de control', '2026-11-05 11:00:00', '98000002', 'BUENO', 'Juego completo');

-- PRESTAMO GRUPAL: UNA RESPONSABLE Y DOS PARTICIPANTES ADICIONALES.
INSERT INTO `participante_prestamo` (`id_participante`, `id_prestamo`, `dni_persona`, `rol_participacion`, `responsable`) VALUES
(1, 16, '99000006', 'Responsable del equipo', 1),
(2, 16, '99000007', 'Integrante', 0),
(3, 16, '99000008', 'Integrante', 0);

-- SOLICITUDES Y RESERVAS: TODOS LOS ESTADOS REPRESENTADOS.
INSERT INTO `reserva` (`id_reserva`, `id_recurso`, `fecha_solicitud`, `fecha_requerida`, `fecha_preparacion`, `fecha_limite_vencimiento`, `tipo_gestion`, `observaciones`, `salida_solicitada`, `id_bien`, `id_prestamo_ref`, `estado`, `dni_persona`) VALUES
(1, 2, '2026-10-30 18:38:04', '2026-10-30 18:38:04', NULL, '2026-11-01 18:38:04', 'PRESTAMO', 'Solicitud sin atender, expirada', 0, NULL, NULL, 'EXPIRADA', '99000001'),
(2, 3, '2026-10-30 18:38:04', '2026-11-01 10:00:00', NULL, '2026-11-01 18:38:04', 'RESERVA', 'Cancelada por la estudiante', 0, NULL, NULL, 'CANCELADA', '99000002'),
(3, 33, '2026-11-11 09:00:00', '2026-11-13 09:00:00', NULL, '2026-11-13 09:00:00', 'PRESTAMO', 'Rechazada por sanción activa', 0, NULL, NULL, 'RECHAZADA', '99000001'),
(4, 34, '2026-11-11 11:00:00', '2026-11-12 10:00:00', '2026-11-12 10:00:00', '2026-11-13 10:00:00', 'RESERVA', 'Visor preparado para retirar; plazo de 24 h', 0, 181, NULL, 'LISTA_PARA_RETIRO', '99000002'),
(5, 4, '2026-11-09 12:00:00', '2026-11-10 10:00:00', NULL, '2026-11-11 12:00:00', 'RESERVA', 'Cancelada antes de preparación', 0, NULL, NULL, 'CANCELADA', '99000003'),
(6, 38, '2026-11-12 10:00:00', '2026-11-13 10:00:00', NULL, '2026-11-14 10:00:00', 'RESERVA', 'Pendiente de revisar disponibilidad y autorización', 0, NULL, NULL, 'EN_ESPERA', '99000003'),
(7, 2, '2026-11-03 09:00:00', '2026-11-05 09:00:00', '2026-11-05 09:00:00', '2026-11-06 09:00:00', 'RESERVA', 'No retiró libro antes del vencimiento', 1, 54, NULL, 'EXPIRADA', '99000005'),
(8, 25, '2026-11-04 09:00:00', '2026-11-05 09:00:00', '2026-11-05 08:30:00', '2026-11-06 08:30:00', 'PRESTAMO', 'Solicitud atendida mediante préstamo 12', 0, 12, 12, 'ATENDIDA', '99000006'),
(9, 34, '2026-11-12 11:00:00', '2026-11-14 10:00:00', NULL, '2026-11-14 11:00:00', 'RESERVA', 'En cola; los visores están reservado y dañado', 0, NULL, NULL, 'EN_ESPERA', '99000008'),
(10, 9, '2026-11-05 09:00:00', '2026-11-06 08:00:00', '2026-11-06 08:00:00', '2026-11-07 08:00:00', 'PRESTAMO', 'Solicitud atendida mediante préstamo 13', 0, 151, 13, 'ATENDIDA', '99000007'),
(11, 32, '2026-11-11 10:00:00', '2026-11-13 10:00:00', NULL, '2026-11-13 10:00:00', 'PRESTAMO', 'Rechazada: matrícula no vigente', 0, NULL, NULL, 'RECHAZADA', '99000012'),
(12, 33, '2026-11-12 09:00:00', '2026-11-12 09:00:00', NULL, '2026-11-14 09:00:00', 'PRESTAMO', 'Solicitud de dron pendiente de entrega', 0, NULL, NULL, 'EN_ESPERA', '99000005');


-- INCIDENCIAS Y SANCIONES CON ESTADOS REALISTAS.
INSERT INTO `incidencia` (`id_incidencia`, `id_detalle`, `tipo`, `dni_registrador`, `descripcion`, `fecha`, `estado`) VALUES
(1, 1, 'RETRASO', '98000002', 'Préstamo #1 vencido sin devolución', '2026-11-01 09:00:00', 'EN_REVISION'),
(2, 4, 'RETRASO', '98000002', 'Diego no devolvió laptop dentro del plazo', '2026-11-10 09:00:00', 'RESUELTA'),
(3, 7, 'DANIO', '98000002', 'Jorge devolvió visor con el lente derecho dañado', '2026-11-11 10:15:00', 'RESUELTA'),
(4, 9, 'RETRASO', '98000002', 'Jorge devolvió juego después del horario previsto', '2026-10-30 10:05:00', 'RESUELTA'),
(5, 11, 'RETRASO', '98000002', 'Valeria no devolvió cámara web a tiempo', '2026-11-09 09:00:00', 'REGISTRADA'),
(6, 14, 'DANIO', '98000002', 'Bruno devolvió cargador con conector dañado', '2026-11-06 11:15:00', 'RESUELTA'),
(7, 21, 'PERDIDA', '98000002', 'Pérdida confirmada del cargador prestado a Bruno', '2026-11-10 09:00:00', 'RESUELTA');

INSERT INTO `sancion` (`id_sancion`, `id_incidencia_ref`, `motivo`, `fecha`, `descripcion`, `estado`, `fecha_levantamiento`, `dni_levantamiento`, `justificacion_levantamiento`) VALUES
(1, 2, 'Mora de laptop', '2026-11-10 10:00:00', 'Debe regularizar la devolución', 'ACTIVA', NULL, NULL, NULL),
(2, 3, 'Daño en visor de realidad virtual', '2026-11-11 11:00:00', 'Compensación acreditada', 'CUMPLIDA', NULL, NULL, NULL),
(3, 4, 'Retraso de ajedrez', '2026-10-30 11:00:00', 'Medida levantada tras revisión', 'LEVANTADA', '2026-11-08 11:00:00', '98000002', 'Se revocó tras evaluar circunstancias'),
(4, 6, 'Daño en cargador', '2026-11-06 12:00:00', 'Acta anulada por defecto de fábrica', 'ANULADA', '2026-11-09 10:00:00', '98000002', 'El daño ya existía antes del préstamo'),
(5, 7, 'Pérdida de cargador', '2026-11-10 10:00:00', 'Pendiente de reposición del bien', 'ACTIVA', NULL, NULL, NULL);

-- AUDITORIA DE TRANSICIONES (ESTADOS ANTERIOR Y NUEVO).
INSERT INTO `historial_estado` (`id_historial_estado`, `entidad`, `id_entidad`, `estado_anterior`, `estado_nuevo`, `fecha`, `observacion`, `dni_responsable`) VALUES
(1, 'BIEN_MATERIAL', 86, 'DISPONIBLE', 'PRESTADO', '2026-10-19 09:00:00', 'Entrega en préstamo #18', '98000002'),
(2, 'PRESTAMO', 18, NULL, 'ACTIVO', '2026-10-19 09:00:00', 'Entrega registrada', '98000002'),
(3, 'BIEN_MATERIAL', 3, 'DISPONIBLE', 'PRESTADO', '2026-10-23 14:00:00', 'Entrega en préstamo #2', '98000002'),
(4, 'PRESTAMO', 2, NULL, 'ACTIVO', '2026-10-23 14:00:00', 'Entrega registrada', '98000002'),
(5, 'BIEN_MATERIAL', 86, 'PRESTADO', 'DISPONIBLE', '2026-10-26 12:00:00', 'Devolución de préstamo #18; condición BUENO', '98000002'),
(6, 'PRESTAMO', 18, 'ACTIVO', 'DEVUELTO', '2026-10-26 12:00:00', 'Devolución completa', '98000002'),
(7, 'BIEN_MATERIAL', 61, 'DISPONIBLE', 'PRESTADO', '2026-10-27 09:00:00', 'Entrega en préstamo #3', '98000002'),
(8, 'PRESTAMO', 3, NULL, 'ACTIVO', '2026-10-27 09:00:00', 'Entrega registrada', '98000002'),
(9, 'BIEN_MATERIAL', 5, 'DISPONIBLE', 'MANTENIMIENTO', '2026-10-28 18:38:04', 'Reparación de encuadernación', '98000001'),
(10, 'BIEN_MATERIAL', 42, 'DISPONIBLE', 'PRESTADO', '2026-10-29 09:00:00', 'Entrega en préstamo #8', '98000002'),
(11, 'BIEN_MATERIAL', 70, 'DISPONIBLE', 'PRESTADO', '2026-10-29 09:00:00', 'Entrega en préstamo #17', '98000002'),
(12, 'PRESTAMO', 8, NULL, 'ACTIVO', '2026-10-29 09:00:00', 'Entrega registrada', '98000002'),
(13, 'PRESTAMO', 17, NULL, 'ACTIVO', '2026-10-29 09:00:00', 'Entrega registrada', '98000002'),
(14, 'BIEN_MATERIAL', 3, 'PRESTADO', 'DISPONIBLE', '2026-10-29 14:00:00', 'Devolución de préstamo #2; condición BUENO', '98000002'),
(15, 'PRESTAMO', 2, 'ACTIVO', 'DEVUELTO', '2026-10-29 14:00:00', 'Devolución completa', '98000002'),
(16, 'BIEN_MATERIAL', 1, 'DISPONIBLE', 'PRESTADO', '2026-10-30 08:00:00', 'Entrega en préstamo #1', '98000002'),
(17, 'PRESTAMO', 1, NULL, 'ACTIVO', '2026-10-30 08:00:00', 'Entrega registrada', '98000002'),
(18, 'BIEN_MATERIAL', 42, 'PRESTADO', 'DISPONIBLE', '2026-10-30 10:00:00', 'Devolución de préstamo #8; condición BUENO', '98000002'),
(19, 'BIEN_MATERIAL', 61, 'PRESTADO', 'DISPONIBLE', '2026-10-30 10:00:00', 'Devolución de préstamo #3; condición BUENO', '98000002'),
(20, 'PRESTAMO', 3, 'ACTIVO', 'DEVUELTO', '2026-10-30 10:00:00', 'Devolución completa', '98000002'),
(21, 'PRESTAMO', 8, 'ACTIVO', 'DEVUELTO', '2026-10-30 10:00:00', 'Devolución completa', '98000002'),
(22, 'SANCION', 3, NULL, 'ACTIVA', '2026-10-30 11:00:00', 'Sanción por Retraso de ajedrez', '98000002'),
(23, 'PRESTAMO', 1, 'ACTIVO', 'VENCIDO', '2026-10-30 16:01:00', 'Plazo vencido y devolución pendiente', '98000002'),
(24, 'RESERVA', 1, NULL, 'EN_ESPERA', '2026-10-30 18:38:04', 'Solicitud registrada', '99000001'),
(25, 'RESERVA', 2, NULL, 'EN_ESPERA', '2026-10-30 18:38:04', 'Solicitud registrada', '99000002'),
(26, 'RESERVA', 2, 'EN_ESPERA', 'CANCELADA', '2026-10-30 23:38:04', 'Cancelada por la estudiante', '99000002'),
(27, 'BIEN_MATERIAL', 66, 'DISPONIBLE', 'PRESTADO', '2026-10-31 09:00:00', 'Entrega en préstamo #5', '98000002'),
(28, 'PRESTAMO', 5, NULL, 'ACTIVO', '2026-10-31 09:00:00', 'Entrega registrada', '98000002'),
(29, 'BIEN_MATERIAL', 54, 'DISPONIBLE', 'PRESTADO', '2026-11-01 09:00:00', 'Entrega en préstamo #9', '98000002'),
(30, 'PRESTAMO', 9, NULL, 'ACTIVO', '2026-11-01 09:00:00', 'Entrega registrada', '98000002'),
(31, 'RESERVA', 1, 'EN_ESPERA', 'EXPIRADA', '2026-11-01 18:38:04', 'Solicitud sin atender, expirada', '98000002'),
(32, 'BIEN_MATERIAL', 66, 'PRESTADO', 'DISPONIBLE', '2026-11-02 11:00:00', 'Devolución de préstamo #5; condición BUENO', '98000002'),
(33, 'PRESTAMO', 5, 'ACTIVO', 'DEVUELTO', '2026-11-02 11:00:00', 'Devolución completa', '98000002'),
(34, 'RESERVA', 7, NULL, 'EN_ESPERA', '2026-11-03 09:00:00', 'Solicitud registrada', '99000005'),
(35, 'BIEN_MATERIAL', 54, 'PRESTADO', 'DISPONIBLE', '2026-11-03 10:00:00', 'Devolución de préstamo #9; condición BUENO', '98000002'),
(36, 'PRESTAMO', 9, 'ACTIVO', 'DEVUELTO', '2026-11-03 10:00:00', 'Devolución completa', '98000002'),
(37, 'RESERVA', 8, NULL, 'EN_ESPERA', '2026-11-04 09:00:00', 'Solicitud registrada', '99000006'),
(38, 'BIEN_MATERIAL', 12, 'DISPONIBLE', 'RESERVADO', '2026-11-05 08:30:00', 'Reserva #8 preparada', '98000002'),
(39, 'BIEN_MATERIAL', 12, 'RESERVADO', 'PRESTADO', '2026-11-05 09:00:00', 'Entrega en préstamo #12', '98000002'),
(40, 'BIEN_MATERIAL', 43, 'DISPONIBLE', 'PRESTADO', '2026-11-05 09:00:00', 'Entrega en préstamo #20', '98000002'),
(41, 'BIEN_MATERIAL', 54, 'DISPONIBLE', 'RESERVADO', '2026-11-05 09:00:00', 'Reserva #7 preparada', '98000002'),
(42, 'PRESTAMO', 12, NULL, 'ACTIVO', '2026-11-05 09:00:00', 'Entrega registrada', '98000002'),
(43, 'PRESTAMO', 20, NULL, 'ACTIVO', '2026-11-05 09:00:00', 'Entrega registrada', '98000002'),
(44, 'RESERVA', 8, 'EN_ESPERA', 'ATENDIDA', '2026-11-05 09:00:00', 'Solicitud atendida mediante préstamo 12', '98000002'),
(45, 'RESERVA', 10, NULL, 'EN_ESPERA', '2026-11-05 09:00:00', 'Solicitud registrada', '99000007'),
(46, 'BIEN_MATERIAL', 12, 'PRESTADO', 'DISPONIBLE', '2026-11-05 11:00:00', 'Devolución de préstamo #12; condición BUENO', '98000002'),
(47, 'BIEN_MATERIAL', 43, 'PRESTADO', 'DISPONIBLE', '2026-11-05 11:00:00', 'Devolución de préstamo #20; condición BUENO', '98000002'),
(48, 'PRESTAMO', 12, 'ACTIVO', 'DEVUELTO', '2026-11-05 11:00:00', 'Devolución completa', '98000002'),
(49, 'PRESTAMO', 20, 'ACTIVO', 'DEVUELTO', '2026-11-05 11:00:00', 'Devolución completa', '98000002'),
(50, 'BIEN_MATERIAL', 151, 'RESERVADO', 'PRESTADO', '2026-11-06 08:00:00', 'Entrega en préstamo #13', '98000002'),
(51, 'BIEN_MATERIAL', 151, 'DISPONIBLE', 'RESERVADO', '2026-11-06 08:00:00', 'Reserva #10 preparada', '98000002'),
(52, 'PRESTAMO', 13, NULL, 'ACTIVO', '2026-11-06 08:00:00', 'Entrega registrada', '98000002'),
(53, 'RESERVA', 10, 'EN_ESPERA', 'ATENDIDA', '2026-11-06 08:00:00', 'Solicitud atendida mediante préstamo 13', '98000002'),
(54, 'BIEN_MATERIAL', 54, 'RESERVADO', 'DISPONIBLE', '2026-11-06 09:00:00', 'Reserva #7 expirada; bien liberado', '98000002'),
(55, 'RESERVA', 7, 'EN_ESPERA', 'EXPIRADA', '2026-11-06 09:00:00', 'No retiró libro antes del vencimiento', '98000002'),
(56, 'BIEN_MATERIAL', 70, 'PRESTADO', 'DISPONIBLE', '2026-11-06 11:00:00', 'Devolución de préstamo #17; condición BUENO', '98000002'),
(57, 'BIEN_MATERIAL', 151, 'PRESTADO', 'DANADO', '2026-11-06 11:00:00', 'Devolución de préstamo #13; condición DANADO', '98000002'),
(58, 'PRESTAMO', 13, 'ACTIVO', 'DEVUELTO', '2026-11-06 11:00:00', 'Devolución completa', '98000002'),
(59, 'PRESTAMO', 17, 'ACTIVO', 'DEVUELTO', '2026-11-06 11:00:00', 'Devolución completa', '98000002'),
(60, 'SANCION', 4, NULL, 'ACTIVA', '2026-11-06 12:00:00', 'Sanción por Daño en cargador', '98000002'),
(61, 'BIEN_MATERIAL', 152, 'DISPONIBLE', 'PRESTADO', '2026-11-07 09:00:00', 'Entrega en préstamo #19', '98000002'),
(62, 'PRESTAMO', 19, NULL, 'ACTIVO', '2026-11-07 09:00:00', 'Entrega registrada', '98000002'),
(63, 'PRESTAMO', 19, 'ACTIVO', 'VENCIDO', '2026-11-07 13:01:00', 'Plazo vencido y devolución pendiente', '98000002'),
(64, 'BIEN_MATERIAL', 145, 'DISPONIBLE', 'PRESTADO', '2026-11-08 10:00:00', 'Entrega en préstamo #10', '98000002'),
(65, 'PRESTAMO', 10, NULL, 'ACTIVO', '2026-11-08 10:00:00', 'Entrega registrada', '98000002'),
(66, 'SANCION', 3, 'ACTIVA', 'LEVANTADA', '2026-11-08 11:00:00', 'Medida levantada tras revisión', '98000002'),
(67, 'PRESTAMO', 10, 'ACTIVO', 'VENCIDO', '2026-11-08 14:01:00', 'Plazo vencido y devolución pendiente', '98000002'),
(68, 'BIEN_MATERIAL', 2, 'DISPONIBLE', 'PRESTADO', '2026-11-09 08:00:00', 'Entrega en préstamo #4', '98000002'),
(69, 'PRESTAMO', 4, NULL, 'ACTIVO', '2026-11-09 08:00:00', 'Entrega registrada', '98000002'),
(70, 'SANCION', 4, 'ACTIVA', 'ANULADA', '2026-11-09 10:00:00', 'Acta anulada por defecto de fábrica', '98000002'),
(71, 'RESERVA', 5, NULL, 'EN_ESPERA', '2026-11-09 12:00:00', 'Solicitud registrada', '99000003'),
(72, 'PRESTAMO', 4, 'ACTIVO', 'VENCIDO', '2026-11-09 16:01:00', 'Plazo vencido y devolución pendiente', '98000002'),
(73, 'RESERVA', 5, 'EN_ESPERA', 'CANCELADA', '2026-11-09 17:00:00', 'Cancelada antes de preparación', '99000003'),
(74, 'BIEN_MATERIAL', 180, 'DISPONIBLE', 'PRESTADO', '2026-11-10 08:00:00', 'Entrega en préstamo #7', '98000002'),
(75, 'BIEN_MATERIAL', 182, 'DISPONIBLE', 'PRESTADO', '2026-11-10 08:00:00', 'Entrega en préstamo #7', '98000002'),
(76, 'PRESTAMO', 7, NULL, 'ACTIVO', '2026-11-10 08:00:00', 'Entrega registrada', '98000002'),
(77, 'BIEN_MATERIAL', 152, 'PRESTADO', 'PERDIDO', '2026-11-10 09:00:00', 'Pérdida confirmada en préstamo #19', '98000002'),
(78, 'BIEN_MATERIAL', 178, 'DISPONIBLE', 'PRESTADO', '2026-11-10 09:00:00', 'Entrega en préstamo #15', '98000002'),
(79, 'PRESTAMO', 15, NULL, 'ACTIVO', '2026-11-10 09:00:00', 'Entrega registrada', '98000002'),
(80, 'SANCION', 1, NULL, 'ACTIVA', '2026-11-10 10:00:00', 'Sanción por Mora de laptop', '98000002'),
(81, 'SANCION', 5, NULL, 'ACTIVA', '2026-11-10 10:00:00', 'Sanción por Pérdida de cargador', '98000002'),
(82, 'BIEN_MATERIAL', 184, 'DISPONIBLE', 'PRESTADO', '2026-11-11 09:00:00', 'Entrega en préstamo #6', '98000002'),
(83, 'BIEN_MATERIAL', 187, 'DISPONIBLE', 'PRESTADO', '2026-11-11 09:00:00', 'Entrega en préstamo #11', '98000002'),
(84, 'PRESTAMO', 6, NULL, 'ACTIVO', '2026-11-11 09:00:00', 'Entrega registrada', '98000002'),
(85, 'PRESTAMO', 11, NULL, 'ACTIVO', '2026-11-11 09:00:00', 'Entrega registrada', '98000002'),
(86, 'RESERVA', 3, NULL, 'EN_ESPERA', '2026-11-11 09:00:00', 'Solicitud registrada', '99000001'),
(87, 'RESERVA', 3, 'EN_ESPERA', 'RECHAZADA', '2026-11-11 09:15:00', 'Rechazada por sanción activa', '98000002'),
(88, 'BIEN_MATERIAL', 180, 'PRESTADO', 'DANADO', '2026-11-11 10:00:00', 'Devolución de préstamo #7; condición DANADO', '98000002'),
(89, 'BIEN_MATERIAL', 188, 'DISPONIBLE', 'PRESTADO', '2026-11-11 10:00:00', 'Entrega en préstamo #16', '98000002'),
(90, 'BIEN_MATERIAL', 195, 'DISPONIBLE', 'PRESTADO', '2026-11-11 10:00:00', 'Entrega en préstamo #16', '98000002'),
(91, 'PRESTAMO', 7, 'ACTIVO', 'PARCIALMENTE_DEVUELTO', '2026-11-11 10:00:00', 'Recepción parcial; restan bienes por devolver', '98000002'),
(92, 'PRESTAMO', 16, NULL, 'ACTIVO', '2026-11-11 10:00:00', 'Entrega registrada', '98000002'),
(93, 'RESERVA', 11, NULL, 'EN_ESPERA', '2026-11-11 10:00:00', 'Solicitud registrada', '99000012'),
(94, 'RESERVA', 11, 'EN_ESPERA', 'RECHAZADA', '2026-11-11 10:15:00', 'Rechazada: matrícula no vigente', '98000002'),
(95, 'RESERVA', 4, NULL, 'EN_ESPERA', '2026-11-11 11:00:00', 'Solicitud registrada', '99000002'),
(96, 'SANCION', 2, NULL, 'ACTIVA', '2026-11-11 11:00:00', 'Sanción por Daño en visor de realidad virtual', '98000002'),
(97, 'RESERVA', 12, NULL, 'EN_ESPERA', '2026-11-12 09:00:00', 'Solicitud registrada', '99000005'),
(98, 'SANCION', 2, 'ACTIVA', 'CUMPLIDA', '2026-11-12 09:00:00', 'Compensación acreditada', '98000002'),
(99, 'BIEN_MATERIAL', 181, 'DISPONIBLE', 'RESERVADO', '2026-11-12 10:00:00', 'Reserva #4 preparada', '98000002'),
(100, 'RESERVA', 4, 'EN_ESPERA', 'LISTA_PARA_RETIRO', '2026-11-12 10:00:00', 'Visor preparado para retirar; plazo de 24 h', '98000002'),
(101, 'RESERVA', 6, NULL, 'EN_ESPERA', '2026-11-12 10:00:00', 'Solicitud registrada', '99000003'),
(102, 'RESERVA', 9, NULL, 'EN_ESPERA', '2026-11-12 11:00:00', 'Solicitud registrada', '99000008'),
(103, 'BIEN_MATERIAL', 7, 'DISPONIBLE', 'PRESTADO', '2026-11-12 12:00:00', 'Entrega en préstamo #14', '98000002'),
(104, 'PRESTAMO', 14, NULL, 'ACTIVO', '2026-11-12 12:00:00', 'Entrega registrada', '98000002');

COMMIT;

-- CONSULTAS DE CONTROL (NO ALTERAN DATOS)
-- Categorias y cantidad de tipos de recursos / unidades inventariadas.
SELECT c.id_categoria, c.nombre, COUNT(DISTINCT r.id_recurso) AS tipos_recurso,
       COUNT(b.id_bien) AS unidades
FROM categoria_recurso c
LEFT JOIN recurso r ON r.id_categoria=c.id_categoria
LEFT JOIN bien_material b ON b.id_recurso=r.id_recurso
GROUP BY c.id_categoria,c.nombre ORDER BY c.id_categoria;

-- Los tres estudiantes con casos diferenciados.
SELECT u.nombre_usuario, p.nombres, p.apellidos, p.dni
FROM usuario_sistema u JOIN persona p ON p.dni=u.dni_persona
WHERE u.nombre_usuario IN ('estudiante01','estudiante02','estudiante03')
ORDER BY u.nombre_usuario;

-- Comprobar que no hay un bien en dos prestamos abiertos.
SELECT d.id_bien, COUNT(*) AS abiertos FROM detalle_prestamo d
WHERE d.fecha_devolucion IS NULL
GROUP BY d.id_bien HAVING COUNT(*)>1;

-- Comprobar que toda reserva con bien asignado corresponde al recurso.
SELECT rv.id_reserva,rv.id_recurso,b.id_recurso AS recurso_del_bien
FROM reserva rv JOIN bien_material b ON b.id_bien=rv.id_bien
WHERE rv.id_recurso<>b.id_recurso;
