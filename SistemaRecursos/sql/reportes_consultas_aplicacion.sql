
USE prestamos_escuela_pruebas;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Consultas de referencia. La aplicación ejecuta las consultas de repositorio/reportes,
-- que aplican los filtros y completan las filas según el reporte seleccionado.

-- 01. Préstamos
SELECT
    p.id_prestamo, p.dni_persona,
    CONCAT(per.nombres, ' ', per.apellidos) AS solicitante,
    p.tipo_prestamo, p.fecha_entrega,
    b.codigo_inventario, r.nombre AS recurso,
    c.nombre AS categoria,
    d.fecha_limite_devolucion, d.fecha_devolucion,
    CASE
        WHEN d.fecha_regularizacion IS NOT NULL THEN 'REGULARIZADO'
        WHEN d.fecha_devolucion IS NOT NULL THEN 'DEVUELTO'
        WHEN b.estado = 'PERDIDO' THEN 'PERDIDO'
        WHEN d.fecha_limite_devolucion < UTC_TIMESTAMP() THEN 'VENCIDO'
        ELSE 'PENDIENTE'
    END AS situacion
FROM prestamo p
JOIN persona per ON per.dni = p.dni_persona
JOIN detalle_prestamo d ON d.id_prestamo = p.id_prestamo
JOIN bien_material b ON b.id_bien = d.id_bien
JOIN recurso r ON r.id_recurso = b.id_recurso
JOIN categoria_recurso c ON c.id_categoria = r.id_categoria
ORDER BY p.fecha_entrega DESC, p.id_prestamo DESC, d.id_detalle;


-- 02. Devoluciones y cumplimiento
SELECT
    p.id_prestamo, p.dni_persona,
    CONCAT(per.nombres, ' ', per.apellidos) AS solicitante,
    p.tipo_prestamo, b.codigo_inventario,
    r.nombre AS recurso, c.nombre AS categoria,
    p.fecha_entrega, d.fecha_limite_devolucion,
    d.fecha_devolucion, d.condicion_devolucion,
    CASE
        WHEN d.fecha_devolucion <= d.fecha_limite_devolucion THEN 'A_TIEMPO'
        ELSE 'TARDIA'
    END AS cumplimiento,
    GREATEST(TIMESTAMPDIFF(MINUTE, d.fecha_limite_devolucion, d.fecha_devolucion), 0) AS retraso_minutos
FROM prestamo p
JOIN persona per ON per.dni = p.dni_persona
JOIN detalle_prestamo d ON d.id_prestamo = p.id_prestamo
JOIN bien_material b ON b.id_bien = d.id_bien
JOIN recurso r ON r.id_recurso = b.id_recurso
JOIN categoria_recurso c ON c.id_categoria = r.id_categoria
WHERE d.fecha_devolucion IS NOT NULL
ORDER BY d.fecha_devolucion DESC, p.id_prestamo DESC, d.id_detalle;


-- 03. Bienes atrasados: filas para pantalla, CSV y PDF.
SELECT
    p.id_prestamo, p.dni_persona,
    CONCAT(per.nombres, ' ', per.apellidos) AS solicitante,
    b.codigo_inventario, r.nombre AS recurso,
    p.fecha_entrega, d.fecha_limite_devolucion,
    TIMESTAMPDIFF(MINUTE, d.fecha_limite_devolucion, UTC_TIMESTAMP()) AS retraso_minutos
FROM detalle_prestamo d
JOIN prestamo p ON p.id_prestamo = d.id_prestamo
JOIN persona per ON per.dni = p.dni_persona
JOIN bien_material b ON b.id_bien = d.id_bien
JOIN recurso r ON r.id_recurso = b.id_recurso
WHERE d.fecha_devolucion IS NULL AND d.fecha_regularizacion IS NULL AND d.fecha_limite_devolucion < UTC_TIMESTAMP()
ORDER BY d.fecha_limite_devolucion, p.id_prestamo, d.id_detalle;


-- 04. Inventario: filas para pantalla, CSV y PDF.
SELECT
    b.id_bien, b.codigo_inventario,
    r.nombre AS recurso, c.nombre AS categoria,
    r.marca, r.modelo, b.numero_serie,
    b.estado, b.ubicacion, b.fecha_adquisicion
FROM bien_material b
JOIN recurso r ON r.id_recurso = b.id_recurso
JOIN categoria_recurso c ON c.id_categoria = r.id_categoria
ORDER BY r.nombre, b.codigo_inventario, b.id_bien;


-- 05. Solicitudes y reservas: filas para pantalla, CSV y PDF.
SELECT
    COALESCE(p.id_reserva_principal,p.id_reserva) AS id_reserva, p.tipo_gestion, p.dni_persona,
    CONCAT(per.nombres, ' ', per.apellidos) AS solicitante,
    r.nombre AS recurso, c.nombre AS categoria,
    p.fecha_solicitud, p.fecha_requerida,
    p.estado, p.fecha_limite_vencimiento
FROM reserva p
JOIN persona per ON per.dni = p.dni_persona
JOIN recurso r ON r.id_recurso = p.id_recurso
JOIN categoria_recurso c ON c.id_categoria = r.id_categoria
ORDER BY p.fecha_solicitud DESC, p.id_reserva DESC;


-- 06. Sanciones:
SELECT
    s.id_sancion, s.gravedad, s.fecha_fin, s.fecha_regularizacion, s.tipo_regularizacion,
    p.id_prestamo, p.dni_persona,
    CONCAT(per.nombres, ' ', per.apellidos) AS solicitante,
    p.tipo_prestamo, b.codigo_inventario,
    r.nombre AS recurso, c.nombre AS categoria,
    s.fecha, s.motivo, s.descripcion, s.estado,
    s.fecha_levantamiento, s.justificacion_levantamiento
FROM prestamo p
JOIN persona per ON per.dni = p.dni_persona
JOIN detalle_prestamo d ON d.id_prestamo = p.id_prestamo
JOIN bien_material b ON b.id_bien = d.id_bien
JOIN recurso r ON r.id_recurso = b.id_recurso
JOIN categoria_recurso c ON c.id_categoria = r.id_categoria
JOIN incidencia i ON i.id_detalle = d.id_detalle
JOIN sancion s ON s.id_incidencia_ref = i.id_incidencia
ORDER BY s.fecha DESC, s.id_sancion DESC;


-- 07. Daños y pérdidas
SELECT
    h.id_historial_estado, h.fecha, b.id_bien,
    b.codigo_inventario, r.nombre AS recurso,
    c.nombre AS categoria, h.estado_nuevo AS tipo_evento,
    b.estado AS estado_actual,
    h.dni_responsable AS dni_registrador,
    CONCAT(reg.nombres, ' ', reg.apellidos) AS registrador,
    h.observacion
FROM historial_estado h
JOIN bien_material b ON b.id_bien = h.id_entidad
JOIN recurso r ON r.id_recurso = b.id_recurso
JOIN categoria_recurso c ON c.id_categoria = r.id_categoria
LEFT JOIN persona reg ON reg.dni = h.dni_responsable
WHERE h.entidad = 'BIEN_MATERIAL' AND h.estado_nuevo IN ('DANADO', 'PERDIDO')
ORDER BY h.fecha DESC, h.id_historial_estado DESC;


-- 08. Personas: una fila por persona para pantalla, CSV y PDF.
SELECT personas.dni, personas.nombres, personas.apellidos,
    personas.tipo_persona, personas.telefono, personas.correo, personas.estado
FROM (
    SELECT per.dni, per.nombres, per.apellidos, per.telefono, per.correo, per.estado,
        CASE
            WHEN e.dni IS NOT NULL THEN 'ESTUDIANTE'
            WHEN doc.dni IS NOT NULL THEN 'DOCENTE'
            WHEN a.dni IS NOT NULL THEN 'ADMINISTRATIVO'
            ELSE 'SIN_TIPO'
        END AS tipo_persona
    FROM persona per
    LEFT JOIN estudiante e ON e.dni = per.dni
    LEFT JOIN docente doc ON doc.dni = per.dni
    LEFT JOIN administrativo a ON a.dni = per.dni
) personas
ORDER BY personas.apellidos, personas.nombres, personas.dni;


-- 09. Integrantes
SELECT pp.id_prestamo, pp.dni_persona, CONCAT(p.nombres, ' ', p.apellidos) AS nombre
FROM participante_prestamo pp
JOIN persona p ON p.dni = pp.dni_persona
WHERE pp.id_prestamo IN (1, 2, 3)
ORDER BY pp.id_prestamo, pp.responsable DESC, pp.id_participante;


-- 10. Cuenta de la sesion
SET @id_usuario = 1;
SELECT u.id_usuario, p.dni, u.nombre_usuario, u.contrasena_hash,
       u.rol, u.estado_cuenta, u.debe_cambiar_clave, p.estado AS estado_persona, p.nombres, p.apellidos
FROM usuario_sistema u
JOIN persona p ON p.dni = u.dni_persona
WHERE u.id_usuario = @id_usuario;


-- 11. Categorías del selector
SELECT * FROM categoria_recurso ORDER BY nombre;
