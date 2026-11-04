-- Ejecutar con la base de la aplicación seleccionada.
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
