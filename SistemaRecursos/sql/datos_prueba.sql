-- Datos ficticios para probar el sistema de recursos con MySQL 8.
-- Crea una base de demostracion aislada. Los casos abiertos se fechan al importar.
-- Ejecutar el archivo completo sobre una base vacía. Si no existe, el archivo la crea.
-- No ejecutar la carga completa sobre una base que ya contiene datos.
-- Si una carga falló, ejecuta ROLLBACK; en la misma pestaña de Workbench.
-- Para reconstruir desde cero, ejecuta esta sentencia por separado solo si
-- quieres borrar todo el contenido de la base de demostración:
-- DROP DATABASE IF EXISTS `prestamos_escuela_pruebas`;
-- Luego ejecuta este archivo completo, desde la primera línea.
-- Las cuentas de demostracion usan debe_cambiar_clave=FALSE y las claves indicadas abajo.
-- Cuentas locales de demostracion (no usar en produccion):
-- admin / AdminPrueba2026!
-- encargado1 y encargado2 / EncargadoPrueba2026!
-- usuario1 y estudiante01 a estudiante08 / UsuarioPrueba2026!
-- Incluye el esquema vigente para instalar el sistema desde cero.
-- Es una carga autónoma de estructura y datos. Importar este archivo de principio a fin.
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
  identificador_sistema VARCHAR(20) NULL,
  numero_serie       VARCHAR(60),
  fecha_adquisicion  DATE NULL,
  fecha_registro     DATETIME NOT NULL DEFAULT (UTC_TIMESTAMP()),
  estado             ENUM('DISPONIBLE','PRESTADO','RESERVADO','DANADO','MANTENIMIENTO','PERDIDO')
                     NOT NULL DEFAULT 'DISPONIBLE',
  ubicacion          VARCHAR(120),
  descripcion_bien   VARCHAR(255) NULL,
  INDEX idx_bien_estado_recurso_codigo (estado, id_recurso, codigo_inventario),
  INDEX idx_bien_recurso_codigo (id_recurso, codigo_inventario),
  UNIQUE KEY uq_bien_identificador_sistema (identificador_sistema),
  FOREIGN KEY (id_recurso) REFERENCES recurso(id_recurso)
) ENGINE=InnoDB;
-- 3. CONTROL: REGLAS DEL SERVICIO
CREATE TABLE IF NOT EXISTS configuracion_general (
  id_configuracion TINYINT PRIMARY KEY CHECK (id_configuracion=1),
  hora_apertura TIME NOT NULL,
  hora_cierre TIME NOT NULL,
  dias_atencion TINYINT UNSIGNED NOT NULL DEFAULT 31 CHECK (dias_atencion BETWEEN 1 AND 127),
  plazo_espera INT NOT NULL,
  unidad_espera ENUM('HORAS','DIAS') NOT NULL DEFAULT 'DIAS',
  plazo_retiro INT NOT NULL,
  unidad_retiro ENUM('HORAS','DIAS') NOT NULL DEFAULT 'HORAS',
  dias_leve INT NOT NULL DEFAULT 14 CHECK (dias_leve BETWEEN 1 AND 3650),
  dias_grave INT NOT NULL DEFAULT 180 CHECK (dias_grave BETWEEN 1 AND 3650),
  dias_espera_perdida INT NOT NULL DEFAULT 7 CHECK (dias_espera_perdida BETWEEN 1 AND 365),
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
  estado            ENUM('ACTIVO','VENCIDO','DEVUELTO','PARCIALMENTE_DEVUELTO','REGULARIZADO') NOT NULL DEFAULT 'ACTIVO',
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
  ampliado BOOLEAN NOT NULL DEFAULT FALSE,
  condicion_entrega ENUM('BUENO','DANADO') NOT NULL DEFAULT 'BUENO',
  observaciones_entrega VARCHAR(255),
  fecha_devolucion DATETIME NULL,
  fecha_regularizacion DATETIME NULL,
  CHECK (fecha_regularizacion IS NULL OR fecha_devolucion IS NULL),
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
  id_reserva_principal INT NULL,
  participantes JSON NULL,
  estado            ENUM('EN_ESPERA','LISTA_PARA_RETIRO','ATENDIDA','CANCELADA','EXPIRADA','RECHAZADA') NOT NULL DEFAULT 'EN_ESPERA',
  INDEX idx_reserva_cola (id_recurso,estado,fecha_solicitud,id_reserva),
  INDEX idx_reserva_persona_estado (dni_persona,estado),
  INDEX idx_reserva_vencimiento (estado,fecha_limite_vencimiento,id_reserva),
  FOREIGN KEY (dni_persona) REFERENCES persona(dni) ON UPDATE CASCADE,
  FOREIGN KEY (id_recurso) REFERENCES recurso(id_recurso),
  CONSTRAINT fk_reserva_bien FOREIGN KEY (id_bien) REFERENCES bien_material(id_bien),
  CONSTRAINT fk_reserva_principal FOREIGN KEY (id_reserva_principal) REFERENCES reserva(id_reserva),
  CONSTRAINT fk_reserva_prestamo FOREIGN KEY (id_prestamo_ref) REFERENCES prestamo(id_prestamo)
) ENGINE=InnoDB;
-- 5. CONTROL: INCIDENCIAS Y SANCIONES
CREATE TABLE IF NOT EXISTS incidencia (
  id_incidencia   INT AUTO_INCREMENT PRIMARY KEY,
  id_detalle  INT NOT NULL,
  tipo ENUM('RETRASO','DANIO','PERDIDA','SALIDA_NO_AUTORIZADA','CUSTODIA') NOT NULL,
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
  gravedad ENUM('LEVE','GRAVE','MUY_GRAVE') NOT NULL DEFAULT 'LEVE',
  dias_leve INT NOT NULL DEFAULT 14,
  dias_grave INT NOT NULL DEFAULT 180,
  dias_espera_perdida INT NOT NULL DEFAULT 7,
  fecha_inicio_nivel DATETIME NULL,
  fecha_fin DATETIME NULL,
  fecha_revision DATETIME NULL,
  fecha_regularizacion DATETIME NULL,
  tipo_regularizacion ENUM('DEVOLUCION','RECUPERACION','REPARACION','REPOSICION','VERIFICACION') NULL,
  dni_regularizacion VARCHAR(8) NULL,
  observacion_regularizacion VARCHAR(255) NULL,
  id_bien_reposicion INT NULL,
  fecha_recuperacion_original DATETIME NULL,
  FOREIGN KEY (dni_regularizacion) REFERENCES persona(dni) ON UPDATE CASCADE,
  FOREIGN KEY (id_bien_reposicion) REFERENCES bien_material(id_bien),
  FOREIGN KEY (dni_levantamiento) REFERENCES persona(dni) ON UPDATE CASCADE,
  FOREIGN KEY (id_incidencia_ref) REFERENCES incidencia(id_incidencia)
) ENGINE=InnoDB;
-- 6. HISTORIALES
CREATE TABLE IF NOT EXISTS historial_estado (
  id_historial_estado  INT AUTO_INCREMENT PRIMARY KEY,
  entidad              ENUM('BIEN_MATERIAL','RESERVA','SANCION','PRESTAMO','CONFIGURACION_SANCIONES','TIPO_PERSONA','AUTORIZACION_PROPIA','RECTIFICACION_DEVOLUCION','CUENTA') NOT NULL,
  id_entidad           INT NULL,
  estado_anterior      VARCHAR(30),
  estado_nuevo         VARCHAR(30) NOT NULL,
  fecha                DATETIME NOT NULL,
  observacion          VARCHAR(255),
  dni_responsable   VARCHAR(8),
  dni_objetivo        VARCHAR(8) NULL,
  datos               JSON NULL,
  INDEX (entidad, id_entidad),
  INDEX idx_historial_dni_objetivo (entidad, dni_objetivo),
  FOREIGN KEY (dni_responsable) REFERENCES persona(dni) ON UPDATE CASCADE,
  CONSTRAINT fk_historial_dni_objetivo FOREIGN KEY (dni_objetivo) REFERENCES persona(dni) ON UPDATE CASCADE
) ENGINE=InnoDB;

-- 7. SESIONES, MANTENIMIENTOS, SOLICITUDES DE AMPLIACION Y PROCESADOR

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

-- DATOS FICTICIOS. EJECUTAR SOLO EN UNA BASE NUEVA/VACIA.
START TRANSACTION;

-- Fechas UTC para que la primera revisión no venza los ejemplos recién cargados.
SET @ahora_prueba = UTC_TIMESTAMP();
SET @ayer_lima = DATE(@ahora_prueba - INTERVAL 5 HOUR) - INTERVAL 1 DAY;
SET @entrega_activa = TIMESTAMP(@ayer_lima, '14:00:00'); -- 09:00 en Lima
SET @entrega_grupal = @entrega_activa + INTERVAL 1 HOUR;
SET @entrega_parcial = @entrega_activa - INTERVAL 25 HOUR;
SET @devolucion_visor = @entrega_parcial + INTERVAL 1 DAY + INTERVAL 2 HOUR;
SET @incidencia_visor = @devolucion_visor + INTERVAL 15 MINUTE;
SET @solicitud_visor = @ahora_prueba - INTERVAL 1 DAY;
SET @preparacion_visor = @ahora_prueba - INTERVAL 1 HOUR;
SET @solicitud_reserva = @ahora_prueba - INTERVAL 30 MINUTE;
SET @dia_retiro = @ayer_lima + INTERVAL 2 DAY;
SET @dia_retiro = @dia_retiro + INTERVAL (CASE WEEKDAY(@dia_retiro) WHEN 5 THEN 2 WHEN 6 THEN 1 ELSE 0 END) DAY;
SET @fecha_reserva = TIMESTAMP(@dia_retiro, '14:00:00'); -- 09:00 en Lima
SET @inicio_sancion_reposicion = TIMESTAMP('2026-05-05', '14:00:00');
SET @fin_sancion_reposicion = @inicio_sancion_reposicion + INTERVAL 180 DAY;
SET @fecha_reposicion = TIMESTAMP('2026-05-06', '15:00:00');
SET @fecha_recuperacion_original = TIMESTAMP('2026-05-07', '14:00:00');

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

-- Para recuperar cuentas en una base de pruebas existente, selecciona y ejecuta solo el INSERT siguiente.
INSERT INTO usuario_sistema (dni_persona, nombre_usuario, rol, contrasena_hash)
SELECT d.dni, d.usuario, d.rol, d.clave
FROM (
    SELECT '98000001' AS dni, 'admin' AS usuario, 'ADMINISTRADOR' AS rol, 'scrypt:32768:8:1$jhqyz5zQhHnufRRc$41187f6bf98ae78e7e0221856d29d8e17bf60a32e34552c7e5734f08ff017bee8d977ab06153ca966a08f70e634e4e0c83cfc4ca52e51b330b7602831af3c5a4' AS clave
    UNION ALL
    SELECT '98000002' AS dni, 'encargado1' AS usuario, 'ENCARGADO_PRESTAMOS' AS rol, 'scrypt:32768:8:1$OSOfhtGAzkHFLfsT$b235f4c09cda8e8c25a44e0ffbf449f506a08cfe3a468af259a11f0ebb9b92dbae9305530e6175a88655984a0601b50e9a64fc34eab21f52964d68f65803fdd9' AS clave
    UNION ALL
    SELECT '02167885' AS dni, 'usuario1' AS usuario, 'USUARIO' AS rol, 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460' AS clave
    UNION ALL
    SELECT '99000001' AS dni, 'estudiante01' AS usuario, 'USUARIO' AS rol, 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460' AS clave
    UNION ALL
    SELECT '99000002' AS dni, 'estudiante02' AS usuario, 'USUARIO' AS rol, 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460' AS clave
    UNION ALL
    SELECT '99000003' AS dni, 'estudiante03' AS usuario, 'USUARIO' AS rol, 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460' AS clave
    UNION ALL
    SELECT '99000004' AS dni, 'estudiante04' AS usuario, 'USUARIO' AS rol, 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460' AS clave
    UNION ALL
    SELECT '99000005' AS dni, 'estudiante05' AS usuario, 'USUARIO' AS rol, 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460' AS clave
    UNION ALL
    SELECT '99000006' AS dni, 'estudiante06' AS usuario, 'USUARIO' AS rol, 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460' AS clave
    UNION ALL
    SELECT '99000007' AS dni, 'estudiante07' AS usuario, 'USUARIO' AS rol, 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460' AS clave
    UNION ALL
    SELECT '99000008' AS dni, 'estudiante08' AS usuario, 'USUARIO' AS rol, 'scrypt:32768:8:1$GLlTvRZr6Kin4Gkx$65ce4a9c7ef057d3a4429b1297f7f5d2ffddb87b7068e46dd92bde33c7220b2ec3dcbced49863d234a8118b664ce836d8c77c724ca9f55336547e1b457002460' AS clave
    UNION ALL
    SELECT '99000015' AS dni, 'encargado2' AS usuario, 'ENCARGADO_PRESTAMOS' AS rol, 'scrypt:32768:8:1$OSOfhtGAzkHFLfsT$b235f4c09cda8e8c25a44e0ffbf449f506a08cfe3a468af259a11f0ebb9b92dbae9305530e6175a88655984a0601b50e9a64fc34eab21f52964d68f65803fdd9' AS clave
) AS d
JOIN persona p ON p.dni = d.dni AND p.estado = 'ACTIVA'
LEFT JOIN usuario_sistema por_dni ON por_dni.dni_persona = d.dni
LEFT JOIN usuario_sistema por_nombre ON por_nombre.nombre_usuario = d.usuario
WHERE por_dni.id_usuario IS NULL AND por_nombre.id_usuario IS NULL;

-- Sesión de demostración cerrada. Cada ingreso crea su propia sesión.
INSERT INTO sesion_usuario (id_sesion, id_usuario, fecha_inicio, ultima_actividad, fecha_cierre)
SELECT SHA2('sesion-cerrada-de-demostracion', 256), id_usuario,
       '2026-11-04 14:00:00', '2026-11-04 14:10:00', '2026-11-04 14:11:00'
FROM usuario_sistema WHERE nombre_usuario='encargado2';

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
(7, 18, 'PR-DEP-MESA-001', NULL, '2026-08-01', 'DISPONIBLE', 'Coliseo', NULL),
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
(199, 42, 'PR-VR-CONTROL-002', NULL, '2026-09-04', 'DISPONIBLE', 'Laboratorio de simulación', NULL),
(200, 9, 'PR-ACC-CARGADOR-REC-001', NULL, '2026-04-27', 'DISPONIBLE', 'Almacén', 'Original recuperado después de la reposición y revisado en mantenimiento.'),
(201, 9, 'PR-ACC-CARGADOR-REP-001', NULL, '2026-05-06', 'DISPONIBLE', 'Almacén', 'Ejemplar recibido como reposición del préstamo #21.');

-- Identificador del sistema y fecha de registro de los bienes de demostracion.
UPDATE bien_material SET fecha_registro=COALESCE(TIMESTAMP(fecha_adquisicion,'12:00:00'),'2026-11-01 12:00:00'),
  identificador_sistema=CONCAT('SR-',DATE_FORMAT(COALESCE(fecha_adquisicion,'2026-11-01'),'%Y'),'-',
  LPAD(UPPER(CONV(id_bien*7919+104729,10,36)),6,'0'))
WHERE id_bien BETWEEN 1 AND 201
LIMIT 201;

INSERT IGNORE INTO estado_procesador(id_procesador) VALUES (1);

-- REGLAS GENERALES Y LIMITES DEMOSTRATIVOS.
INSERT INTO `configuracion_general` (`id_configuracion`, `hora_apertura`, `hora_cierre`, `dias_atencion`, `plazo_espera`, `unidad_espera`, `plazo_retiro`, `unidad_retiro`, `dias_leve`, `dias_grave`, `dias_espera_perdida`) VALUES
(1, '08:00:00', '16:00:00', 31, 2, 'DIAS', 24, 'HORAS', 14, 180, 7);

INSERT INTO `limite_articulos_prestamo` (`tipo_persona`, `maximo_articulos`) VALUES
('ESTUDIANTE', 3),
('DOCENTE', 5),
('ADMINISTRATIVO', 4);

-- POLITICAS VIGENTES POR CATEGORIA Y TIPO DE PERSONA, Y POLITICAS HISTORICAS.
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
(156, 'ADMINISTRATIVO', 3, 'DIAS', 0, 9, 1),
(157, 'ESTUDIANTE', 2, 'DIAS', 1, 2, 0);

-- OPERACIONES: PRESTAMOS CON HISTORIALES DIVERSOS.
INSERT INTO `prestamo` (`id_prestamo`, `tipo_prestamo`, `fecha_solicitud`, `fecha_entrega`, `estado`, `observaciones`, `dni_encargado`, `dni_persona`) VALUES
(1, 'INDIVIDUAL', '2026-10-30 08:00:00', '2026-10-30 08:00:00', 'VENCIDO', 'Préstamo original de laptop, vencido', '98000002', '02167885'),
(2, 'INDIVIDUAL', '2026-10-23 13:45:00', '2026-10-23 14:00:00', 'DEVUELTO', 'Préstamo original devuelto de un libro', '98000002', '98000004'),
(3, 'INDIVIDUAL', '2026-10-27 08:45:00', '2026-10-27 09:00:00', 'DEVUELTO', 'Diego: libro devuelto con retraso y sanción cumplida', '98000002', '99000001'),
(4, 'INDIVIDUAL', '2026-11-09 08:00:00', '2026-11-09 08:00:00', 'VENCIDO', 'Diego: laptop no devuelta y sanción activa', '98000002', '99000001'),
(5, 'INDIVIDUAL', '2026-10-31 08:45:00', '2026-10-31 09:00:00', 'DEVUELTO', 'Camila: préstamo antiguo sin observaciones', '98000002', '99000002'),
(6, 'INDIVIDUAL', @entrega_activa - INTERVAL 15 MINUTE, @entrega_activa, 'ACTIVO', 'Camila: robot educativo con ampliación pendiente', '98000002', '99000002'),
(7, 'INDIVIDUAL', @entrega_parcial, @entrega_parcial, 'PARCIALMENTE_DEVUELTO', 'Jorge: visor devuelto con daño, dron pendiente', '98000002', '99000003'),
(8, 'INDIVIDUAL', '2026-10-29 08:45:00', '2026-10-29 09:00:00', 'DEVUELTO', 'Jorge: devolución tardía de ajedrez, sanción levantada', '98000002', '99000003'),
(9, 'INDIVIDUAL', '2026-11-01 08:45:00', '2026-11-01 09:00:00', 'DEVUELTO', 'Valeria: libro devuelto a tiempo', '98000002', '99000004'),
(10, 'INDIVIDUAL', '2026-11-08 09:45:00', '2026-11-08 10:00:00', 'VENCIDO', 'Valeria: cámara web vencida sin devolución', '98000002', '99000004'),
(11, 'INDIVIDUAL', @entrega_activa - INTERVAL 15 MINUTE, @entrega_activa, 'ACTIVO', 'Mateo: brazo robótico, uso supervisado', '98000002', '99000005'),
(12, 'INDIVIDUAL', '2026-11-05 08:45:00', '2026-11-05 09:00:00', 'DEVUELTO', 'Andrea: balón devuelto y reserva atendida', '98000002', '99000006'),
(13, 'INDIVIDUAL', '2026-11-06 08:00:00', '2026-11-06 08:00:00', 'DEVUELTO', 'Bruno: cargador devuelto dañado', '98000002', '99000007'),
(14, 'INDIVIDUAL', '2026-11-12 16:45:00', '2026-11-12 17:00:00', 'DEVUELTO', 'Fernanda: mesa de ping pong devuelta dentro del plazo', '98000002', '99000008'),
(15, 'INDIVIDUAL', @entrega_activa - INTERVAL 15 MINUTE, @entrega_activa, 'ACTIVO', 'Docente: tablet en préstamo', '98000002', '99000013'),
(16, 'GRUPAL', @entrega_grupal - INTERVAL 15 MINUTE, @entrega_grupal, 'ACTIVO', 'Andrea: préstamo grupal, dos bienes y tres participantes', '98000002', '99000006'),
(17, 'INDIVIDUAL', '2026-10-29 08:45:00', '2026-10-29 09:00:00', 'DEVUELTO', 'Camila: libro con ampliación aprobada', '98000002', '99000002'),
(18, 'INDIVIDUAL', '2026-10-19 08:45:00', '2026-10-19 09:00:00', 'DEVUELTO', 'Docente: libro devuelto', '98000002', '99000014'),
(19, 'INDIVIDUAL', '2026-11-07 08:45:00', '2026-11-07 09:00:00', 'VENCIDO', 'Bruno: cargador extraviado, sanción activa', '98000002', '99000007'),
(20, 'INDIVIDUAL', '2026-11-05 08:45:00', '2026-11-05 09:00:00', 'DEVUELTO', 'Renato: devolución de ajedrez registrada tras una rectificación', '98000002', '99000009'),
(21, 'INDIVIDUAL', '2026-05-04 13:55:00', '2026-05-04 14:00:00', 'REGULARIZADO', 'Entrega propia autorizada. Cargador repuesto y original recuperado posteriormente.', '98000002', '98000002');

INSERT INTO `detalle_prestamo` (`id_detalle`, `id_prestamo`, `id_bien`, `id_politica`, `fecha_limite_devolucion`, `condicion_entrega`, `observaciones_entrega`, `fecha_devolucion`, `dni_encargado_devolucion`, `condicion_devolucion`, `observaciones_devolucion`) VALUES
(1, 1, 1, 24, '2026-10-30 16:00:00', 'BUENO', 'Entrega con ficha de control', NULL, NULL, NULL, NULL),
(2, 2, 3, 26, '2026-11-06 14:00:00', 'BUENO', 'Entrega con ficha de control', '2026-10-29 14:00:00', '98000002', 'BUENO', 'Ejemplar recibido sin daños'),
(3, 3, 61, 157, '2026-10-29 09:00:00', 'BUENO', 'Entrega con ficha de control', '2026-10-30 10:00:00', '98000002', 'BUENO', 'Libro completo, recibido fuera de plazo'),
(4, 4, 2, 130, '2026-11-09 16:00:00', 'BUENO', 'Entrega con ficha de control', NULL, NULL, NULL, NULL),
(5, 5, 66, 133, '2026-11-07 09:00:00', 'BUENO', 'Entrega con ficha de control', '2026-11-02 11:00:00', '98000002', 'BUENO', 'Libro completo'),
(6, 6, 184, 151, @entrega_activa + INTERVAL 3 DAY, 'BUENO', 'Entrega con ficha de control', NULL, NULL, NULL, NULL),
(7, 7, 180, 154, @entrega_parcial + INTERVAL 2 DAY, 'BUENO', 'Entrega con ficha de control', @devolucion_visor, '98000002', 'DANADO', 'Lente derecho dañado, informe de daño'),
(8, 7, 182, 151, @entrega_parcial + INTERVAL 3 DAY, 'BUENO', 'Entrega con ficha de control', NULL, NULL, NULL, NULL),
(9, 8, 42, 142, '2026-10-29 12:00:00', 'BUENO', 'Entrega con ficha de control', '2026-10-30 10:00:00', '98000002', 'BUENO', 'Un día después del plazo'),
(10, 9, 54, 133, '2026-11-08 09:00:00', 'BUENO', 'Entrega con ficha de control', '2026-11-03 10:00:00', '98000002', 'BUENO', 'Sin observaciones'),
(11, 10, 145, 148, '2026-11-08 14:00:00', 'BUENO', 'Entrega con ficha de control', NULL, NULL, NULL, NULL),
(12, 11, 187, 151, @entrega_activa + INTERVAL 3 DAY, 'BUENO', 'Entrega con ficha de control', NULL, NULL, NULL, NULL),
(13, 12, 12, 136, '2026-11-05 12:00:00', 'BUENO', 'Entrega con ficha de control', '2026-11-05 11:00:00', '98000002', 'BUENO', 'Balón sin daños'),
(14, 13, 151, 145, '2026-11-06 12:00:00', 'BUENO', 'Entrega con ficha de control', '2026-11-06 11:00:00', '98000002', 'DANADO', 'Conector del cargador dañado'),
(15, 14, 7, 136, '2026-11-12 20:00:00', 'BUENO', 'Entrega con ficha de control', '2026-11-12 19:30:00', '98000002', 'BUENO', 'Mesa recibida en buen estado'),
(16, 15, 178, 131, @entrega_activa + INTERVAL 5 DAY, 'BUENO', 'Entrega con ficha de control', NULL, NULL, NULL, NULL),
(17, 16, 188, 151, @entrega_grupal + INTERVAL 3 DAY, 'BUENO', 'Entrega con ficha de control', NULL, NULL, NULL, NULL),
(18, 16, 195, 151, @entrega_grupal + INTERVAL 3 DAY, 'BUENO', 'Entrega con ficha de control', NULL, NULL, NULL, NULL),
(19, 17, 70, 133, '2026-11-07 09:00:00', 'BUENO', 'Entrega con ficha de control', '2026-11-06 11:00:00', '98000002', 'BUENO', 'Devolución dentro del plazo ampliado'),
(20, 18, 86, 134, '2026-11-02 09:00:00', 'BUENO', 'Entrega con ficha de control', '2026-10-26 12:00:00', '98000002', 'BUENO', 'Ejemplar bien conservado'),
(21, 19, 152, 145, '2026-11-07 13:00:00', 'BUENO', 'Entrega con ficha de control', NULL, NULL, NULL, NULL),
(22, 20, 43, 142, '2026-11-05 12:00:00', 'BUENO', 'Entrega con ficha de control', '2026-11-05 11:00:00', '98000002', 'BUENO', 'Juego completo');

INSERT INTO detalle_prestamo (id_detalle, id_prestamo, id_bien, id_politica, fecha_limite_devolucion,
  fecha_regularizacion) VALUES
(23, 21, 200, 147, '2026-05-04 21:00:00', @fecha_reposicion);

-- PRESTAMO GRUPAL: UNA RESPONSABLE Y DOS PARTICIPANTES ADICIONALES.
INSERT INTO `participante_prestamo` (`id_participante`, `id_prestamo`, `dni_persona`, `rol_participacion`, `responsable`) VALUES
(1, 16, '99000006', 'Responsable del equipo', 1),
(2, 16, '99000009', 'Integrante', 0),
(3, 16, '99000010', 'Integrante', 0);

-- SOLICITUDES Y RESERVAS: TODOS LOS ESTADOS REPRESENTADOS.
INSERT INTO `reserva` (`id_reserva`, `id_recurso`, `fecha_solicitud`, `fecha_requerida`, `fecha_preparacion`, `fecha_limite_vencimiento`, `tipo_gestion`, `observaciones`, `salida_solicitada`, `id_bien`, `id_prestamo_ref`, `estado`, `dni_persona`) VALUES
(1, 2, '2026-10-30 18:38:04', '2026-10-30 18:38:04', NULL, '2026-11-01 18:38:04', 'PRESTAMO', 'Solicitud sin atender, expirada', 0, NULL, NULL, 'EXPIRADA', '99000001'),
(2, 3, '2026-10-30 18:38:04', '2026-11-01 10:00:00', NULL, '2026-11-01 18:38:04', 'RESERVA', 'Cancelada por la estudiante', 0, NULL, NULL, 'CANCELADA', '99000002'),
(3, 33, '2026-11-08 09:00:00', '2026-11-11 09:00:00', NULL, '2026-11-13 09:00:00', 'RESERVA', 'Rechazada al atenderla por una sanción posterior a la solicitud', 0, NULL, NULL, 'RECHAZADA', '99000001'),
(4, 34, @solicitud_visor, @preparacion_visor, @preparacion_visor, @preparacion_visor + INTERVAL 24 HOUR, 'RESERVA', 'Visor preparado para retirar; plazo de 24 h', 0, 181, NULL, 'LISTA_PARA_RETIRO', '99000002'),
(5, 4, '2026-11-09 12:00:00', '2026-11-10 10:00:00', NULL, '2026-11-11 12:00:00', 'RESERVA', 'Cancelada antes de preparación', 0, NULL, NULL, 'CANCELADA', '99000003'),
(6, 38, @solicitud_reserva, @fecha_reserva, NULL, @fecha_reserva + INTERVAL 2 DAY, 'RESERVA', 'Impresora 3D solicitada para una práctica', 0, NULL, NULL, 'EN_ESPERA', '99000006'),
(7, 2, '2026-11-03 09:00:00', '2026-11-05 09:00:00', '2026-11-05 09:00:00', '2026-11-06 09:00:00', 'RESERVA', 'No retiró libro antes del vencimiento', 1, 54, NULL, 'EXPIRADA', '99000005'),
(8, 25, '2026-11-04 09:00:00', '2026-11-05 09:00:00', '2026-11-05 08:30:00', '2026-11-06 08:30:00', 'PRESTAMO', 'Solicitud atendida mediante préstamo 12', 0, 12, 12, 'ATENDIDA', '99000006'),
(9, 34, @solicitud_reserva, @fecha_reserva, NULL, @fecha_reserva + INTERVAL 2 DAY, 'RESERVA', 'En cola mientras un visor está reservado y el otro está dañado', 0, NULL, NULL, 'EN_ESPERA', '99000008'),
(10, 9, '2026-11-05 09:00:00', '2026-11-06 07:55:00', '2026-11-06 07:55:00', '2026-11-07 07:55:00', 'PRESTAMO', 'Solicitud atendida mediante préstamo 13', 0, 151, 13, 'ATENDIDA', '99000007'),
(11, 32, '2026-11-11 10:00:00', '2026-11-13 10:00:00', NULL, '2026-11-13 10:00:00', 'PRESTAMO', 'Rechazada: matrícula no vigente', 0, NULL, NULL, 'RECHAZADA', '99000012'),
(12, 33, @solicitud_reserva, @fecha_reserva, NULL, @fecha_reserva + INTERVAL 2 DAY, 'RESERVA', 'Reserva de dron pendiente de preparación', 0, NULL, NULL, 'EN_ESPERA', '99000005');

-- El estado del libro y las ampliaciones descritas tienen sus registros de operación.
INSERT INTO mantenimiento_bien (id_bien, tipo, motivo, estado_previo, fecha_inicio, dni_apertura)
VALUES (5, 'CORRECTIVO', 'Reparación de encuadernación', 'DISPONIBLE', '2026-10-28 18:38:04', '98000001');

INSERT INTO mantenimiento_bien (id_bien, tipo, motivo, estado_previo, fecha_inicio, dni_apertura,
  fecha_fin_real, dni_cierre, resultado, observacion_cierre) VALUES
(200, 'CORRECTIVO', 'Revisión del original recuperado después de la reposición', 'PERDIDO',
 @fecha_recuperacion_original, '98000001', @fecha_recuperacion_original + INTERVAL 3 HOUR,
 '98000001', 'DISPONIBLE', 'Prueba de carga satisfactoria.');

INSERT INTO solicitud_ampliacion (id_solicitud, id_prestamo, id_detalle, dni_solicitante, cantidad, unidad, motivo,
  fecha_solicitud, fecha_limite_anterior, estado, fecha_resolucion, dni_resolucion,
  fecha_limite_nueva, observacion_resolucion) VALUES
(1, 6, 6, '99000002', 1, 'DIAS', 'Un día adicional para completar la práctica de robótica.',
 @entrega_activa + INTERVAL 30 MINUTE, @entrega_activa + INTERVAL 3 DAY, 'PENDIENTE', NULL, NULL, NULL, NULL),
(2, 17, 19, '99000002', 2, 'DIAS', 'Dos días adicionales para terminar la lectura.',
 '2026-11-04 14:00:00', '2026-11-05 09:00:00', 'APROBADA', '2026-11-04 15:00:00',
 '98000002', '2026-11-07 09:00:00', 'Ampliación autorizada antes del vencimiento.');

UPDATE detalle_prestamo SET ampliado=TRUE WHERE id_detalle=19;

-- CASOS DE PRUEBA DE SANCIONES POR GRAVEDAD, PLAZO Y REGULARIZACIÓN.
INSERT INTO `incidencia` (`id_incidencia`, `id_detalle`, `tipo`, `dni_registrador`, `descripcion`, `fecha`, `estado`) VALUES
(1, 1, 'RETRASO', NULL, 'Préstamo #1 vencido sin devolución', '2026-10-30 16:00:00', 'REGISTRADA'),
(2, 4, 'RETRASO', NULL, 'Laptop pendiente de devolución', '2026-11-09 16:00:00', 'REGISTRADA'),
(3, 7, 'DANIO', '98000002', 'Visor devuelto con el lente derecho dañado', @incidencia_visor, 'REGISTRADA'),
(4, 9, 'RETRASO', NULL, 'Jorge devolvió el juego después del plazo', '2026-10-29 12:00:00', 'RESUELTA'),
(5, 11, 'RETRASO', NULL, 'Valeria no devolvió la cámara web a tiempo', '2026-11-08 14:00:00', 'REGISTRADA'),
(6, 14, 'DANIO', '98000002', 'Daño del conector reportado al recibir el cargador', '2026-11-06 12:00:00', 'RESUELTA'),
(7, 21, 'PERDIDA', '98000001', 'Pérdida del cargador confirmada por el administrador', '2026-11-10 10:00:00', 'REGISTRADA'),
(8, 3, 'RETRASO', NULL, 'Libro devuelto fuera de plazo y recibido en buen estado', '2026-10-29 09:00:00', 'RESUELTA'),
(9, 23, 'PERDIDA', '98000001', 'Pérdida confirmada del cargador del préstamo #21', @inicio_sancion_reposicion, 'RESUELTA');

INSERT INTO `sancion` (`id_sancion`, `id_incidencia_ref`, `motivo`, `fecha`, `descripcion`, `estado`, `fecha_levantamiento`, `dni_levantamiento`, `justificacion_levantamiento`, `gravedad`, `dias_leve`, `dias_grave`, `dias_espera_perdida`, `fecha_inicio_nivel`, `fecha_fin`, `fecha_revision`, `fecha_regularizacion`, `tipo_regularizacion`, `dni_regularizacion`) VALUES
(1, 2, 'Retraso en la devolución de laptop', '2026-11-09 16:00:00', 'El plazo de sanción terminó y la laptop sigue pendiente de devolución.', 'ACTIVA', NULL, NULL, NULL, 'LEVE', 14, 180, 7, '2026-11-09 16:00:00', '2026-11-23 16:00:00', '2026-11-30 16:00:00', NULL, NULL, NULL),
(2, 3, 'Daño en visor de realidad virtual', @incidencia_visor, 'El visor se recibió con el lente dañado y está pendiente de reparación.', 'ACTIVA', NULL, NULL, NULL, 'GRAVE', 14, 180, 7, @incidencia_visor, @incidencia_visor + INTERVAL 180 DAY, NULL, NULL, NULL, NULL),
(3, 4, 'Retraso en la devolución de ajedrez', '2026-10-29 12:00:00', 'Juego recibido completo y en buen estado.', 'LEVANTADA', '2026-11-08 11:00:00', '98000002', 'El encargado verificó la devolución y aceptó la justificación del retraso.', 'LEVE', 14, 180, 7, '2026-10-29 12:00:00', '2026-11-12 12:00:00', '2026-11-19 12:00:00', '2026-10-30 10:00:00', 'DEVOLUCION', '98000002'),
(4, 6, 'Daño atribuido al préstamo de un cargador', '2026-11-06 12:00:00', 'La revisión del inventario confirmó que el daño era previo a la entrega.', 'ANULADA', '2026-11-09 10:00:00', '98000001', 'El defecto del conector ya existía antes del préstamo.', 'GRAVE', 14, 180, 7, '2026-11-06 12:00:00', '2027-05-05 12:00:00', NULL, NULL, NULL, NULL),
(5, 7, 'Pérdida confirmada de cargador', '2026-11-10 10:00:00', 'El administrador aplicó una sanción muy grave. Queda pendiente la reposición.', 'ACTIVA', NULL, NULL, NULL, 'MUY_GRAVE', 14, 180, 7, '2026-11-10 10:00:00', NULL, NULL, NULL, NULL, NULL),
(6, 8, 'Retraso en la devolución de un libro', '2026-10-29 09:00:00', 'Se recibió el libro en buen estado y se cumplió el plazo de sanción.', 'CUMPLIDA', '2026-11-12 09:00:00', NULL, 'Plazo cumplido y devolución aceptada.', 'LEVE', 14, 180, 7, '2026-10-29 09:00:00', '2026-11-12 09:00:00', '2026-11-19 09:00:00', '2026-10-30 10:00:00', 'DEVOLUCION', '98000002'),
(7, 1, 'Laptop vencida sin devolución', '2026-10-30 16:00:00', 'La laptop sigue pendiente de devolución.', 'ACTIVA', NULL, NULL, NULL, 'LEVE', 14, 180, 7, '2026-10-30 16:00:00', '2026-11-13 16:00:00', '2026-11-20 16:00:00', NULL, NULL, NULL),
(8, 5, 'Cámara web vencida sin devolución', '2026-11-08 14:00:00', 'La cámara sigue pendiente de devolución.', 'ACTIVA', NULL, NULL, NULL, 'LEVE', 14, 180, 7, '2026-11-08 14:00:00', '2026-11-22 14:00:00', '2026-11-29 14:00:00', NULL, NULL, NULL);

INSERT INTO sancion (id_sancion, id_incidencia_ref, motivo, fecha, descripcion, estado,
  fecha_levantamiento, justificacion_levantamiento, gravedad, fecha_inicio_nivel, fecha_fin,
  fecha_regularizacion, tipo_regularizacion, dni_regularizacion, observacion_regularizacion,
  id_bien_reposicion, fecha_recuperacion_original) VALUES
(9, 9, 'Pérdida de cargador', @inicio_sancion_reposicion,
 'El bien fue repuesto y el original se recuperó después.', 'CUMPLIDA',
 @fin_sancion_reposicion, 'Plazo cumplido y regularización aceptada.', 'GRAVE',
 @inicio_sancion_reposicion, @fin_sancion_reposicion, @fecha_reposicion, 'REPOSICION',
 '98000001', 'Se verificó un cargador equivalente en buen estado.', 201, @fecha_recuperacion_original);

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
(22, 'SANCION', 3, NULL, 'ACTIVA', '2026-10-29 12:00:00', 'Sanción leve por retraso en la devolución de ajedrez.', NULL),
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
(44, 'RESERVA', 8, 'LISTA_PARA_RETIRO', 'ATENDIDA', '2026-11-05 09:00:00', 'Solicitud atendida mediante préstamo 12', '98000002'),
(45, 'RESERVA', 10, NULL, 'EN_ESPERA', '2026-11-05 09:00:00', 'Solicitud registrada', '99000007'),
(46, 'BIEN_MATERIAL', 12, 'PRESTADO', 'DISPONIBLE', '2026-11-05 11:00:00', 'Devolución de préstamo #12; condición BUENO', '98000002'),
(47, 'BIEN_MATERIAL', 43, 'PRESTADO', 'DISPONIBLE', '2026-11-05 11:00:00', 'Devolución de préstamo #20; condición BUENO', '98000002'),
(48, 'PRESTAMO', 12, 'ACTIVO', 'DEVUELTO', '2026-11-05 11:00:00', 'Devolución completa', '98000002'),
(49, 'PRESTAMO', 20, 'ACTIVO', 'DEVUELTO', '2026-11-05 11:00:00', 'Devolución completa', '98000002'),
(50, 'BIEN_MATERIAL', 151, 'RESERVADO', 'PRESTADO', '2026-11-06 08:00:00', 'Entrega en préstamo #13', '98000002'),
(51, 'BIEN_MATERIAL', 151, 'DISPONIBLE', 'RESERVADO', '2026-11-06 07:55:00', 'Reserva #10 preparada', '98000002'),
(52, 'PRESTAMO', 13, NULL, 'ACTIVO', '2026-11-06 08:00:00', 'Entrega registrada', '98000002'),
(53, 'RESERVA', 10, 'LISTA_PARA_RETIRO', 'ATENDIDA', '2026-11-06 08:00:00', 'Solicitud atendida mediante préstamo 13', '98000002'),
(54, 'BIEN_MATERIAL', 54, 'RESERVADO', 'DISPONIBLE', '2026-11-06 09:00:00', 'Reserva #7 expirada; bien liberado', '98000002'),
(55, 'RESERVA', 7, 'LISTA_PARA_RETIRO', 'EXPIRADA', '2026-11-06 09:00:00', 'No retiró libro antes del vencimiento', '98000002'),
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
(70, 'SANCION', 4, 'ACTIVA', 'ANULADA', '2026-11-09 10:00:00', 'El defecto del conector ya existía antes del préstamo.', '98000001'),
(71, 'RESERVA', 5, NULL, 'EN_ESPERA', '2026-11-09 12:00:00', 'Solicitud registrada', '99000003'),
(72, 'PRESTAMO', 4, 'ACTIVO', 'VENCIDO', '2026-11-09 16:01:00', 'Plazo vencido y devolución pendiente', '98000002'),
(73, 'RESERVA', 5, 'EN_ESPERA', 'CANCELADA', '2026-11-09 17:00:00', 'Cancelada antes de preparación', '99000003'),
(74, 'BIEN_MATERIAL', 180, 'DISPONIBLE', 'PRESTADO', @entrega_parcial, 'Entrega en préstamo #7', '98000002'),
(75, 'BIEN_MATERIAL', 182, 'DISPONIBLE', 'PRESTADO', @entrega_parcial, 'Entrega en préstamo #7', '98000002'),
(76, 'PRESTAMO', 7, NULL, 'ACTIVO', @entrega_parcial, 'Entrega registrada', '98000002'),
(77, 'BIEN_MATERIAL', 152, 'PRESTADO', 'PERDIDO', '2026-11-10 10:00:00', 'Pérdida confirmada en préstamo #19', '98000001'),
(78, 'BIEN_MATERIAL', 178, 'DISPONIBLE', 'PRESTADO', @entrega_activa, 'Entrega en préstamo #15', '98000002'),
(79, 'PRESTAMO', 15, NULL, 'ACTIVO', @entrega_activa, 'Entrega registrada', '98000002'),
(80, 'SANCION', 1, NULL, 'ACTIVA', '2026-11-09 16:00:00', 'Sanción leve por retraso en la devolución de laptop.', NULL),
(81, 'SANCION', 5, NULL, 'ACTIVA', '2026-11-10 10:00:00', 'Sanción muy grave por pérdida confirmada de cargador.', '98000001'),
(82, 'BIEN_MATERIAL', 184, 'DISPONIBLE', 'PRESTADO', @entrega_activa, 'Entrega en préstamo #6', '98000002'),
(83, 'BIEN_MATERIAL', 187, 'DISPONIBLE', 'PRESTADO', @entrega_activa, 'Entrega en préstamo #11', '98000002'),
(84, 'PRESTAMO', 6, NULL, 'ACTIVO', @entrega_activa, 'Entrega registrada', '98000002'),
(85, 'PRESTAMO', 11, NULL, 'ACTIVO', @entrega_activa, 'Entrega registrada', '98000002'),
(86, 'RESERVA', 3, NULL, 'EN_ESPERA', '2026-11-08 09:00:00', 'Solicitud registrada', '99000001'),
(87, 'RESERVA', 3, 'EN_ESPERA', 'RECHAZADA', '2026-11-11 09:15:00', 'Rechazada por sanción activa', '98000002'),
(88, 'BIEN_MATERIAL', 180, 'PRESTADO', 'DANADO', @devolucion_visor, 'Devolución de préstamo #7; condición DANADO', '98000002'),
(89, 'BIEN_MATERIAL', 188, 'DISPONIBLE', 'PRESTADO', @entrega_grupal, 'Entrega en préstamo #16', '98000002'),
(90, 'BIEN_MATERIAL', 195, 'DISPONIBLE', 'PRESTADO', @entrega_grupal, 'Entrega en préstamo #16', '98000002'),
(91, 'PRESTAMO', 7, 'ACTIVO', 'PARCIALMENTE_DEVUELTO', @devolucion_visor, 'Recepción parcial; restan bienes por devolver', '98000002'),
(92, 'PRESTAMO', 16, NULL, 'ACTIVO', @entrega_grupal, 'Entrega registrada', '98000002'),
(93, 'RESERVA', 11, NULL, 'EN_ESPERA', '2026-11-11 10:00:00', 'Solicitud registrada', '99000012'),
(94, 'RESERVA', 11, 'EN_ESPERA', 'RECHAZADA', '2026-11-11 10:15:00', 'Rechazada: matrícula no vigente', '98000002'),
(95, 'RESERVA', 4, NULL, 'EN_ESPERA', @solicitud_visor, 'Solicitud registrada', '99000002'),
(96, 'SANCION', 2, NULL, 'ACTIVA', @incidencia_visor, 'Sanción grave por daño en visor de realidad virtual.', '98000002'),
(97, 'RESERVA', 12, NULL, 'EN_ESPERA', @solicitud_reserva, 'Solicitud registrada', '99000005'),
(98, 'SANCION', 6, 'ACTIVA', 'CUMPLIDA', '2026-11-12 09:00:00', 'Plazo cumplido y devolución aceptada.', NULL),
(99, 'BIEN_MATERIAL', 181, 'DISPONIBLE', 'RESERVADO', @preparacion_visor, 'Reserva #4 preparada', '98000002'),
(100, 'RESERVA', 4, 'EN_ESPERA', 'LISTA_PARA_RETIRO', @preparacion_visor, 'Visor preparado para retirar; plazo de 24 h', '98000002'),
(101, 'RESERVA', 6, NULL, 'EN_ESPERA', @solicitud_reserva, 'Solicitud registrada', '99000006'),
(102, 'RESERVA', 9, NULL, 'EN_ESPERA', @solicitud_reserva, 'Solicitud registrada', '99000008'),
(103, 'BIEN_MATERIAL', 7, 'DISPONIBLE', 'PRESTADO', '2026-11-12 17:00:00', 'Entrega en préstamo #14', '98000002'),
(104, 'PRESTAMO', 14, NULL, 'ACTIVO', '2026-11-12 17:00:00', 'Entrega registrada', '98000002'),
(105, 'SANCION', 6, NULL, 'ACTIVA', '2026-10-29 09:00:00', 'Sanción leve por devolución fuera de plazo.', NULL),
(106, 'SANCION', 6, 'ACTIVA', 'ACTIVA', '2026-10-30 10:00:00', 'Regularización: libro recibido en buen estado.', '98000002'),
(107, 'BIEN_MATERIAL', 7, 'PRESTADO', 'DISPONIBLE', '2026-11-12 19:30:00', 'Mesa recibida en buen estado.', '98000002'),
(108, 'PRESTAMO', 14, 'ACTIVO', 'DEVUELTO', '2026-11-12 19:30:00', 'Devolución completa.', '98000002'),
(109, 'SANCION', 7, NULL, 'ACTIVA', '2026-10-30 16:00:00', 'Sanción leve por laptop vencida.', NULL),
(110, 'SANCION', 8, NULL, 'ACTIVA', '2026-11-08 14:00:00', 'Sanción leve por cámara web vencida.', NULL),
(112, 'RESERVA', 7, 'EN_ESPERA', 'LISTA_PARA_RETIRO', '2026-11-05 09:00:00', 'Libro preparado para el retiro.', '98000002'),
(113, 'RESERVA', 8, 'EN_ESPERA', 'LISTA_PARA_RETIRO', '2026-11-05 08:30:00', 'Balón preparado para el retiro.', '98000002'),
(114, 'RESERVA', 10, 'EN_ESPERA', 'LISTA_PARA_RETIRO', '2026-11-06 07:55:00', 'Cargador preparado para el retiro.', '98000002'),
(115, 'SANCION', 3, 'ACTIVA', 'ACTIVA', '2026-10-30 10:00:00', 'Regularización: ajedrez recibido en buen estado.', '98000002');

-- Auditoría del formato vigente. Los ejemplos se vinculan a sus préstamos y personas.
INSERT INTO historial_estado (id_historial_estado, entidad, id_entidad, estado_anterior,
  estado_nuevo, fecha, observacion, dni_responsable, dni_objetivo, datos) VALUES
(111, 'PRESTAMO', 17, 'ACTIVO', 'ACTIVO', '2026-11-04 15:00:00',
 'Solicitud #2 aprobada. Detalle #19: 2026-11-05 09:00:00 UTC → 2026-11-07 09:00:00 UTC',
 '98000002', NULL, JSON_OBJECT('evento', 'AMPLIACION_PLAZO', 'id_detalle', 19, 'id_solicitud', 2,
   'fecha_limite_anterior', '2026-11-05T09:00:00', 'fecha_limite_nueva', '2026-11-07T09:00:00')),
(116, 'AUTORIZACION_PROPIA', NULL, 'EMITIDA', 'UTILIZADA', '2026-05-04 13:45:00',
 'Autorización del administrador para la entrega propia del cargador.', '98000001', '98000002',
 JSON_OBJECT('accion', 'ENTREGA', 'fecha_uso', '2026-05-04 14:00:00', 'id_prestamo_uso', 21)),
(117, 'TIPO_PERSONA', NULL, 'ESTUDIANTE', 'DOCENTE', '2026-10-01 14:00:00',
 'Se acreditó el ingreso a la plana docente.', '98000001', '99000013',
 JSON_OBJECT('datos_institucionales', JSON_OBJECT('cui', '20260013', 'ciclo', 10, 'estado_matricula', 'NO_VIGENTE'))),
(118, 'RECTIFICACION_DEVOLUCION', 22, 'DEVUELTO', 'PENDIENTE', '2026-11-05 10:25:00',
 'Se marcó el juego equivocado como recibido. Se corrigió la recepción.', '98000001', '98000002',
 JSON_OBJECT('fecha_devolucion_original', '2026-11-05 10:20:00', 'condicion_original', 'BUENO',
   'observacion_original', 'Recepción registrada para un ejemplar distinto.'));

INSERT INTO historial_estado (entidad, id_entidad, estado_anterior, estado_nuevo,
  fecha, observacion, dni_responsable) VALUES
('BIEN_MATERIAL', 43, 'PRESTADO', 'DISPONIBLE', '2026-11-05 10:20:00', 'Recepción registrada para un ejemplar distinto.', '98000002'),
('PRESTAMO', 20, 'ACTIVO', 'DEVUELTO', '2026-11-05 10:20:00', 'Devolución registrada por error.', '98000002'),
('BIEN_MATERIAL', 43, 'DISPONIBLE', 'PRESTADO', '2026-11-05 10:25:00', 'Rectificación de la devolución del préstamo #20.', '98000001'),
('PRESTAMO', 20, 'DEVUELTO', 'ACTIVO', '2026-11-05 10:25:00', 'Rectificación de devolución del detalle #22.', '98000001'),
('BIEN_MATERIAL', 200, 'DISPONIBLE', 'PRESTADO', '2026-05-04 14:00:00', 'Entrega del préstamo #21.', '98000002'),
('PRESTAMO', 21, NULL, 'ACTIVO', '2026-05-04 14:00:00', 'Entrega registrada.', '98000002'),
('PRESTAMO', 21, 'ACTIVO', 'ACTIVO', '2026-05-04 14:00:00', 'Operación propia con autorización #116 del DNI 98000001.', '98000002'),
('BIEN_MATERIAL', 200, 'PRESTADO', 'PERDIDO', @inicio_sancion_reposicion, 'Pérdida confirmada del cargador.', '98000001'),
('PRESTAMO', 21, 'ACTIVO', 'VENCIDO', @inicio_sancion_reposicion, 'Pérdida registrada en el detalle #23.', '98000001'),
('SANCION', 9, NULL, 'ACTIVA', @inicio_sancion_reposicion, 'Aplicación de sanción GRAVE por pérdida.', '98000001'),
('BIEN_MATERIAL', 201, NULL, 'DISPONIBLE', @fecha_reposicion, 'Reposición por sanción #9.', '98000001'),
('BIEN_MATERIAL', 200, 'PERDIDO', 'PERDIDO', @fecha_reposicion, 'Repuesto por bien #201.', '98000001'),
('PRESTAMO', 21, 'VENCIDO', 'REGULARIZADO', @fecha_reposicion, 'Regularización por reposición del detalle #23.', '98000001'),
('SANCION', 9, 'ACTIVA', 'ACTIVA', @fecha_reposicion, 'Regularización por reposición aceptada.', '98000001'),
('BIEN_MATERIAL', 200, 'PERDIDO', 'MANTENIMIENTO', @fecha_recuperacion_original, 'Original recuperado y enviado a revisión.', '98000001'),
('SANCION', 9, 'ACTIVA', 'ACTIVA', @fecha_recuperacion_original, 'Original recuperado después de la reposición.', '98000001'),
('BIEN_MATERIAL', 200, 'MANTENIMIENTO', 'DISPONIBLE', @fecha_recuperacion_original + INTERVAL 3 HOUR, 'Mantenimiento cerrado con prueba de carga satisfactoria.', '98000001'),
('SANCION', 9, 'ACTIVA', 'CUMPLIDA', @fin_sancion_reposicion, 'Plazo cumplido y regularización aceptada.', NULL);

INSERT INTO historial_estado (entidad, id_entidad, estado_anterior, estado_nuevo,
  fecha, observacion, dni_responsable)
SELECT 'CUENTA', id_usuario, 'PENDIENTE', 'ACTIVADA', '2026-11-04 13:50:00',
       'Contraseña establecida.', dni_persona
FROM usuario_sistema WHERE nombre_usuario='encargado2';

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
WHERE d.fecha_devolucion IS NULL AND d.fecha_regularizacion IS NULL
GROUP BY d.id_bien HAVING COUNT(*)>1;

-- Comprobar que toda reserva con bien asignado corresponde al recurso.
SELECT rv.id_reserva,rv.id_recurso,b.id_recurso AS recurso_del_bien
FROM reserva rv JOIN bien_material b ON b.id_bien=rv.id_bien
WHERE rv.id_recurso<>b.id_recurso;

-- Resumen de la carga para verificar la instalación antes de iniciar la aplicación.
SELECT (SELECT COUNT(*) FROM usuario_sistema) AS cuentas_de_prueba,
       (SELECT COUNT(*) FROM sancion) AS sanciones_de_prueba;
