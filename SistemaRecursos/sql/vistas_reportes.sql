USE prestamos_escuela_pruebas;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 01. VISTA: Personas (sin cambios; tipo_persona ya es calculado)
CREATE OR REPLACE VIEW reporte_personas AS
SELECT per.dni, per.nombres, per.apellidos,
    CASE
        WHEN e.dni IS NOT NULL THEN 'ESTUDIANTE'
        WHEN doc.dni IS NOT NULL THEN 'DOCENTE'
        WHEN a.dni IS NOT NULL THEN 'ADMINISTRATIVO'
        ELSE 'SIN_TIPO'
    END AS tipo_persona,
    per.telefono, per.correo, per.estado
FROM persona per
LEFT JOIN estudiante e ON e.dni = per.dni
LEFT JOIN docente doc ON doc.dni = per.dni
LEFT JOIN administrativo a ON a.dni = per.dni
ORDER BY per.apellidos, per.nombres, per.dni;


-- 02. VISTA: Daños y pérdidas (sin cambios)
CREATE OR REPLACE VIEW reporte_danos_y_perdidas AS
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


-- 03. VISTA: Sanciones (sin cambios)
CREATE OR REPLACE VIEW reporte_sanciones AS
SELECT
    s.id_sancion, p.id_prestamo, p.dni_persona,
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


-- 04. VISTA: Solicitudes y reservas (agrega filtros auxiliares de tipo)
CREATE OR REPLACE VIEW reporte_solicitudes_y_reservas AS
SELECT
    p.id_reserva, p.tipo_gestion, p.dni_persona,
    CONCAT(per.nombres, ' ', per.apellidos) AS solicitante,
    r.nombre AS recurso, c.nombre AS categoria,
    p.fecha_solicitud, p.fecha_requerida,
    p.estado, p.fecha_limite_vencimiento,
    CASE
        WHEN EXISTS (SELECT 1 FROM estudiante e WHERE e.dni = p.dni_persona) THEN 'ESTUDIANTE'
        WHEN EXISTS (SELECT 1 FROM docente doc WHERE doc.dni = p.dni_persona) THEN 'DOCENTE'
        WHEN EXISTS (SELECT 1 FROM administrativo a WHERE a.dni = p.dni_persona) THEN 'ADMINISTRATIVO'
        ELSE 'SIN_TIPO'
    END AS tipo_persona,
    EXISTS (SELECT 1 FROM estudiante e WHERE e.dni = p.dni_persona) AS es_estudiante,
    EXISTS (SELECT 1 FROM docente doc WHERE doc.dni = p.dni_persona) AS es_docente,
    EXISTS (SELECT 1 FROM administrativo a WHERE a.dni = p.dni_persona) AS es_administrativo
FROM reserva p
JOIN persona per ON per.dni = p.dni_persona
JOIN recurso r ON r.id_recurso = p.id_recurso
JOIN categoria_recurso c ON c.id_categoria = r.id_categoria
ORDER BY p.fecha_solicitud DESC, p.id_reserva DESC;


-- 05. VISTA: Inventario (sin cambios)
CREATE OR REPLACE VIEW reporte_inventario AS
SELECT
    b.id_bien, b.codigo_inventario,
    r.nombre AS recurso, c.nombre AS categoria,
    r.marca, r.modelo, b.numero_serie,
    b.estado, b.ubicacion, b.fecha_adquisicion
FROM bien_material b
JOIN recurso r ON r.id_recurso = b.id_recurso
JOIN categoria_recurso c ON c.id_categoria = r.id_categoria
ORDER BY r.nombre, b.codigo_inventario, b.id_bien;


-- 06. VISTA: Bienes atrasados (agrega categoria)
CREATE OR REPLACE VIEW reporte_bienes_atrasados AS
SELECT
    p.id_prestamo, p.dni_persona,
    CONCAT(per.nombres, ' ', per.apellidos) AS solicitante,
    b.codigo_inventario, r.nombre AS recurso,
    p.fecha_entrega, d.fecha_limite_devolucion,
    TIMESTAMPDIFF(MINUTE, d.fecha_limite_devolucion, UTC_TIMESTAMP()) AS retraso_minutos,
    c.nombre AS categoria
FROM detalle_prestamo d
JOIN prestamo p ON p.id_prestamo = d.id_prestamo
JOIN persona per ON per.dni = p.dni_persona
JOIN bien_material b ON b.id_bien = d.id_bien
JOIN recurso r ON r.id_recurso = b.id_recurso
JOIN categoria_recurso c ON c.id_categoria = r.id_categoria
WHERE d.fecha_devolucion IS NULL AND d.fecha_limite_devolucion < UTC_TIMESTAMP()
ORDER BY d.fecha_limite_devolucion, p.id_prestamo, d.id_detalle;


-- 07. VISTA: Devoluciones y cumplimiento (sin cambios; ya calcula cumplimiento)
CREATE OR REPLACE VIEW reporte_devoluciones_y_cumplimiento AS
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


-- 08. VISTA: Préstamos (agrega estado_prestamo con los 4 estados reales)
CREATE OR REPLACE VIEW reporte_prestamos AS
SELECT
    p.id_prestamo, p.dni_persona,
    CONCAT(per.nombres, ' ', per.apellidos) AS solicitante,
    p.tipo_prestamo, p.fecha_entrega,
    b.codigo_inventario, r.nombre AS recurso,
    c.nombre AS categoria,
    d.fecha_limite_devolucion, d.fecha_devolucion,
    CASE
        WHEN d.fecha_devolucion IS NOT NULL THEN 'DEVUELTO'
        WHEN d.fecha_limite_devolucion < UTC_TIMESTAMP() THEN 'VENCIDO'
        ELSE 'PENDIENTE'
    END AS situacion,
    CASE
        WHEN EXISTS (SELECT 1 FROM estudiante e WHERE e.dni = p.dni_persona) THEN 'ESTUDIANTE'
        WHEN EXISTS (SELECT 1 FROM docente doc WHERE doc.dni = p.dni_persona) THEN 'DOCENTE'
        WHEN EXISTS (SELECT 1 FROM administrativo a WHERE a.dni = p.dni_persona) THEN 'ADMINISTRATIVO'
        ELSE 'SIN_TIPO'
    END AS tipo_persona,
    CASE
        WHEN NOT EXISTS (
            SELECT 1 FROM detalle_prestamo x
            WHERE x.id_prestamo = p.id_prestamo
              AND x.fecha_devolucion IS NULL
        ) THEN 'DEVUELTO'
        WHEN EXISTS (
            SELECT 1 FROM detalle_prestamo x
            WHERE x.id_prestamo = p.id_prestamo
              AND x.fecha_devolucion IS NULL
              AND x.fecha_limite_devolucion < UTC_TIMESTAMP()
        ) THEN 'VENCIDO'
        WHEN EXISTS (
            SELECT 1 FROM detalle_prestamo x
            WHERE x.id_prestamo = p.id_prestamo
              AND x.fecha_devolucion IS NOT NULL
        ) THEN 'PARCIALMENTE_DEVUELTO'
        ELSE 'ACTIVO'
    END AS estado_prestamo
FROM prestamo p
JOIN persona per ON per.dni = p.dni_persona
JOIN detalle_prestamo d ON d.id_prestamo = p.id_prestamo
JOIN bien_material b ON b.id_bien = d.id_bien
JOIN recurso r ON r.id_recurso = b.id_recurso
JOIN categoria_recurso c ON c.id_categoria = r.id_categoria
ORDER BY p.fecha_entrega DESC, p.id_prestamo DESC, d.id_detalle;

-- REVISION DE NOMBRES DESPUES DE EJECUTAR
SELECT TABLE_NAME AS nombre_vista
FROM information_schema.VIEWS
WHERE TABLE_SCHEMA = 'prestamos_escuela_pruebas'
ORDER BY TABLE_NAME;