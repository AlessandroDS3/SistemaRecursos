-- Carga las personas y cuentas de demostración que faltan. Usar solo en MySQL local de pruebas.
-- Si quedó abierta la importación fallida, ejecuta ROLLBACK en esa pestaña antes de continuar.
USE prestamos_escuela_pruebas;
START TRANSACTION;

INSERT INTO persona (nombres, apellidos, dni, telefono, correo, estado)
SELECT d.nombres, d.apellidos, d.dni, d.telefono, d.correo, d.estado
FROM (
    SELECT 'Ana' AS nombres, 'Torres' AS apellidos, '02167885' AS dni, '' AS telefono, 'ana@ejemplo.gmail' AS correo, 'ACTIVA' AS estado
    UNION ALL
    SELECT 'Administrador' AS nombres, 'Prueba' AS apellidos, '98000001' AS dni, '' AS telefono, 'admin@ejemplo.gmail' AS correo, 'ACTIVA' AS estado
    UNION ALL
    SELECT 'Carlos' AS nombres, 'Rojas' AS apellidos, '98000002' AS dni, '' AS telefono, 'encargado@ejemplo.gmail' AS correo, 'ACTIVA' AS estado
    UNION ALL
    SELECT 'Diego' AS nombres, 'Huamán Quispe' AS apellidos, '99000001' AS dni, '999000001' AS telefono, 'diego.huaman@ejemplo.gmail' AS correo, 'ACTIVA' AS estado
    UNION ALL
    SELECT 'Camila' AS nombres, 'Rojas Medina' AS apellidos, '99000002' AS dni, '999000002' AS telefono, 'camila.rojas@ejemplo.gmail' AS correo, 'ACTIVA' AS estado
    UNION ALL
    SELECT 'Jorge' AS nombres, 'Mamani Apaza' AS apellidos, '99000003' AS dni, '999000003' AS telefono, 'jorge.mamani@ejemplo.gmail' AS correo, 'ACTIVA' AS estado
    UNION ALL
    SELECT 'Valeria' AS nombres, 'Condori Paredes' AS apellidos, '99000004' AS dni, '999000004' AS telefono, 'valeria.condori@ejemplo.gmail' AS correo, 'ACTIVA' AS estado
    UNION ALL
    SELECT 'Mateo' AS nombres, 'Chávez Flores' AS apellidos, '99000005' AS dni, '999000005' AS telefono, 'mateo.chavez@ejemplo.gmail' AS correo, 'ACTIVA' AS estado
    UNION ALL
    SELECT 'Andrea' AS nombres, 'Quispe Salas' AS apellidos, '99000006' AS dni, '999000006' AS telefono, 'andrea.quispe@ejemplo.gmail' AS correo, 'ACTIVA' AS estado
    UNION ALL
    SELECT 'Bruno' AS nombres, 'Vargas Cárdenas' AS apellidos, '99000007' AS dni, '999000007' AS telefono, 'bruno.vargas@ejemplo.gmail' AS correo, 'ACTIVA' AS estado
    UNION ALL
    SELECT 'Fernanda' AS nombres, 'Paredes Soto' AS apellidos, '99000008' AS dni, '999000008' AS telefono, 'fernanda.paredes@ejemplo.gmail' AS correo, 'ACTIVA' AS estado
    UNION ALL
    SELECT 'Mariana' AS nombres, 'Peña Salazar' AS apellidos, '99000015' AS dni, '999000015' AS telefono, 'mariana.pena@ejemplo.gmail' AS correo, 'ACTIVA' AS estado
) AS d
WHERE NOT EXISTS (SELECT 1 FROM persona existente WHERE existente.dni = d.dni)
  AND NOT EXISTS (SELECT 1 FROM persona existente WHERE existente.correo = d.correo);

INSERT INTO estudiante (ciclo, estado_matricula, dni, cui)
SELECT d.ciclo, d.estado_matricula, d.dni, d.cui
FROM (
    SELECT 4 AS ciclo, 'VIGENTE' AS estado_matricula, '02167885' AS dni, '20245555' AS cui
    UNION ALL
    SELECT 2 AS ciclo, 'VIGENTE' AS estado_matricula, '99000001' AS dni, '20260001' AS cui
    UNION ALL
    SELECT 4 AS ciclo, 'VIGENTE' AS estado_matricula, '99000002' AS dni, '20260002' AS cui
    UNION ALL
    SELECT 6 AS ciclo, 'VIGENTE' AS estado_matricula, '99000003' AS dni, '20260003' AS cui
    UNION ALL
    SELECT 3 AS ciclo, 'VIGENTE' AS estado_matricula, '99000004' AS dni, '20260004' AS cui
    UNION ALL
    SELECT 5 AS ciclo, 'VIGENTE' AS estado_matricula, '99000005' AS dni, '20260005' AS cui
    UNION ALL
    SELECT 7 AS ciclo, 'VIGENTE' AS estado_matricula, '99000006' AS dni, '20260006' AS cui
    UNION ALL
    SELECT 2 AS ciclo, 'VIGENTE' AS estado_matricula, '99000007' AS dni, '20260007' AS cui
    UNION ALL
    SELECT 8 AS ciclo, 'VIGENTE' AS estado_matricula, '99000008' AS dni, '20260008' AS cui
) AS d
JOIN persona p ON p.dni = d.dni AND p.estado = 'ACTIVA'
WHERE NOT EXISTS (SELECT 1 FROM estudiante existente WHERE existente.dni = d.dni)
  AND NOT EXISTS (SELECT 1 FROM estudiante existente WHERE existente.cui = d.cui);

INSERT INTO administrativo (codigo_empleado, area, dni)
SELECT d.codigo_empleado, d.area, d.dni
FROM (
    SELECT 'ADM-PRUEBA-01' AS codigo_empleado, 'Administración' AS area, '98000001' AS dni
    UNION ALL
    SELECT 'ADM-PRUEBA-02' AS codigo_empleado, 'Préstamos' AS area, '98000002' AS dni
    UNION ALL
    SELECT 'ADM-PRB-03' AS codigo_empleado, 'Préstamos' AS area, '99000015' AS dni
) AS d
JOIN persona p ON p.dni = d.dni AND p.estado = 'ACTIVA'
WHERE NOT EXISTS (SELECT 1 FROM administrativo existente WHERE existente.dni = d.dni)
  AND NOT EXISTS (SELECT 1 FROM administrativo existente WHERE existente.codigo_empleado = d.codigo_empleado);

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

SELECT ROW_COUNT() AS cuentas_creadas;
COMMIT;

SELECT nombre_usuario, rol, estado_cuenta
FROM usuario_sistema
WHERE nombre_usuario IN (
    'admin', 'encargado1', 'encargado2', 'usuario1', 'estudiante01', 'estudiante02',
    'estudiante03', 'estudiante04', 'estudiante05', 'estudiante06', 'estudiante07', 'estudiante08'
)
ORDER BY nombre_usuario;

-- Permite ver por qué una cuenta esperada no está disponible.
SELECT d.usuario AS cuenta_esperada, d.dni, p.estado AS estado_persona,
       u.nombre_usuario AS cuenta_vinculada, u.estado_cuenta
FROM (
    SELECT '98000001' AS dni, 'admin' AS usuario
    UNION ALL SELECT '98000002', 'encargado1'
    UNION ALL SELECT '02167885', 'usuario1'
    UNION ALL SELECT '99000001', 'estudiante01'
) AS d
LEFT JOIN persona p ON p.dni = d.dni
LEFT JOIN usuario_sistema u ON u.dni_persona = d.dni
ORDER BY d.usuario;
