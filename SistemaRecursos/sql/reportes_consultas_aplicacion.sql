-- CONSULTAS DEL REPOSITORIO, MATERIALIZADAS SIN FILTROS NI PAGINACION.
-- Las consultas 01 a 16 son el SQL actual de filas y resumen, sin reformular los JOIN.
-- Corresponden a descargar un CSV con los filtros limpios: paginar=False.
-- Ejecuta USE y SET NAMES; despues selecciona solo la consulta que quieras comprobar.
-- Las impares 01-15 devuelven las filas; las pares 02-16 devuelven los indicadores.
-- La 17 obtiene integrantes; Python los reune y convierte fechas UTC a Lima para el CSV.
-- Por eso el SELECT de filas y el CSV no son identicos celda por celda. Ver LEEME_reportes.md.
-- Las consultas 18-20 son de acceso y del selector, no contienen las filas del CSV.
USE prestamos_escuela_pruebas;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;


-- 01. Préstamos: filas sin paginar.

SELECT
    p.id_prestamo,
    p.dni_persona,
    CONCAT(per.nombres, ' ', per.apellidos) AS solicitante,
    p.tipo_prestamo,
    p.fecha_entrega,
    b.codigo_inventario,
    r.nombre AS recurso,
    c.nombre AS categoria,
    d.fecha_limite_devolucion,
    d.fecha_devolucion,
    CASE
        WHEN d.fecha_devolucion IS NOT NULL THEN 'DEVUELTO'
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


-- 02. Préstamos: resumen de indicadores.

SELECT
    COUNT(*) AS detalles,
    COUNT(DISTINCT id_prestamo) AS prestamos,
    COALESCE(SUM(fecha_devolucion IS NOT NULL), 0) AS devueltos,
    COALESCE(SUM(fecha_devolucion IS NULL), 0) AS pendientes,
    COALESCE(SUM(
        fecha_devolucion IS NULL
        AND fecha_limite_devolucion < UTC_TIMESTAMP()
    ), 0) AS vencidos
FROM detalle_prestamo;

-- 03. Devoluciones y cumplimiento: filas sin paginar.
SELECT p.id_prestamo,p.dni_persona,CONCAT(per.nombres,' ',per.apellidos) AS solicitante,
            p.tipo_prestamo,b.codigo_inventario,r.nombre AS recurso,c.nombre AS categoria,
            p.fecha_entrega,d.fecha_limite_devolucion,d.fecha_devolucion,d.condicion_devolucion,
            CASE WHEN d.fecha_devolucion<=d.fecha_limite_devolucion THEN 'A_TIEMPO'
                ELSE 'TARDIA' END AS cumplimiento,GREATEST(TIMESTAMPDIFF(MINUTE,d.fecha_limite_devolucion,d.fecha_devolucion),0) AS retraso_minutos FROM prestamo p JOIN persona per ON per.dni=p.dni_persona
    JOIN detalle_prestamo d ON d.id_prestamo=p.id_prestamo
    JOIN bien_material b ON b.id_bien=d.id_bien JOIN recurso r ON r.id_recurso=b.id_recurso
    JOIN categoria_recurso c ON c.id_categoria=r.id_categoria WHERE 1=1 AND d.fecha_devolucion IS NOT NULL ORDER BY d.fecha_devolucion DESC,p.id_prestamo DESC,d.id_detalle;


-- 04. Devoluciones y cumplimiento: resumen de indicadores.
SELECT COUNT(*) AS detalles,
            COALESCE(SUM(d.fecha_devolucion<=d.fecha_limite_devolucion),0) AS puntuales,
            COALESCE(SUM(d.fecha_devolucion>d.fecha_limite_devolucion),0) AS tardias,
            COALESCE(100.0*SUM(d.fecha_devolucion<=d.fecha_limite_devolucion)/NULLIF(COUNT(*),0),0) AS porcentaje_puntual,
            COALESCE(AVG(CASE WHEN d.fecha_devolucion>d.fecha_limite_devolucion THEN GREATEST(TIMESTAMPDIFF(MINUTE,d.fecha_limite_devolucion,d.fecha_devolucion),0) END),0) AS retraso_promedio FROM prestamo p JOIN persona per ON per.dni=p.dni_persona
    JOIN detalle_prestamo d ON d.id_prestamo=p.id_prestamo
    JOIN bien_material b ON b.id_bien=d.id_bien JOIN recurso r ON r.id_recurso=b.id_recurso
    JOIN categoria_recurso c ON c.id_categoria=r.id_categoria WHERE 1=1 AND d.fecha_devolucion IS NOT NULL;


-- 05. Bienes atrasados: filas sin paginar.
SELECT p.id_prestamo,p.dni_persona,CONCAT(per.nombres,' ',per.apellidos) AS solicitante,
            b.codigo_inventario,r.nombre AS recurso,p.fecha_entrega,d.fecha_limite_devolucion,
            TIMESTAMPDIFF(MINUTE,d.fecha_limite_devolucion,UTC_TIMESTAMP()) AS retraso_minutos FROM detalle_prestamo d JOIN prestamo p ON p.id_prestamo=d.id_prestamo
            JOIN persona per ON per.dni=p.dni_persona JOIN bien_material b ON b.id_bien=d.id_bien
            JOIN recurso r ON r.id_recurso=b.id_recurso WHERE 1=1 AND d.fecha_devolucion IS NULL AND d.fecha_limite_devolucion<UTC_TIMESTAMP() ORDER BY d.fecha_limite_devolucion,p.id_prestamo,d.id_detalle;


-- 06. Bienes atrasados: resumen de indicadores.
SELECT COUNT(*) AS detalles,COUNT(DISTINCT p.id_prestamo) AS prestamos,
            COUNT(DISTINCT p.dni_persona) AS responsables,COALESCE(MAX(TIMESTAMPDIFF(MINUTE,d.fecha_limite_devolucion,UTC_TIMESTAMP())),0) AS retraso_maximo FROM detalle_prestamo d JOIN prestamo p ON p.id_prestamo=d.id_prestamo
            JOIN persona per ON per.dni=p.dni_persona JOIN bien_material b ON b.id_bien=d.id_bien
            JOIN recurso r ON r.id_recurso=b.id_recurso WHERE 1=1 AND d.fecha_devolucion IS NULL AND d.fecha_limite_devolucion<UTC_TIMESTAMP();


-- 07. Inventario: filas sin paginar.
SELECT b.id_bien,b.codigo_inventario,r.nombre AS recurso,c.nombre AS categoria,
            r.marca,r.modelo,b.numero_serie,b.estado,b.ubicacion,b.fecha_adquisicion FROM bien_material b JOIN recurso r ON r.id_recurso=b.id_recurso
            JOIN categoria_recurso c ON c.id_categoria=r.id_categoria WHERE 1=1 ORDER BY r.nombre,b.codigo_inventario,b.id_bien;


-- 08. Inventario: resumen de indicadores.
SELECT COUNT(*) AS detalles,COUNT(DISTINCT r.id_recurso) AS recursos,COALESCE(SUM(b.estado='DISPONIBLE'),0) AS disponibles,COALESCE(SUM(b.estado='PRESTADO'),0) AS prestados,COALESCE(SUM(b.estado='RESERVADO'),0) AS reservados,COALESCE(SUM(b.estado='DANADO'),0) AS danados,COALESCE(SUM(b.estado='MANTENIMIENTO'),0) AS mantenimiento,COALESCE(SUM(b.estado='PERDIDO'),0) AS perdidos FROM bien_material b JOIN recurso r ON r.id_recurso=b.id_recurso
            JOIN categoria_recurso c ON c.id_categoria=r.id_categoria WHERE 1=1;


-- 09. Uso de recursos: filas sin paginar.
SELECT DATE_FORMAT(CONVERT_TZ(p.fecha_entrega,'+00:00','-05:00'),'%Y-%m') AS periodo,r.nombre AS recurso,c.nombre AS categoria,
            COUNT(DISTINCT p.id_prestamo) AS prestamos,COUNT(*) AS bienes_prestados,
            COUNT(DISTINCT p.dni_persona) AS solicitantes FROM prestamo p JOIN persona per ON per.dni=p.dni_persona
    JOIN detalle_prestamo d ON d.id_prestamo=p.id_prestamo
    JOIN bien_material b ON b.id_bien=d.id_bien JOIN recurso r ON r.id_recurso=b.id_recurso
    JOIN categoria_recurso c ON c.id_categoria=r.id_categoria WHERE 1=1 AND p.fecha_entrega IS NOT NULL GROUP BY periodo,r.id_recurso,r.nombre,c.nombre ORDER BY periodo DESC,bienes_prestados DESC,r.nombre,r.id_recurso;


-- 10. Uso de recursos: resumen de indicadores.
SELECT COUNT(DISTINCT DATE_FORMAT(CONVERT_TZ(p.fecha_entrega,'+00:00','-05:00'),'%Y-%m'),r.id_recurso) AS detalles,
            COUNT(DISTINCT p.id_prestamo) AS prestamos,COUNT(*) AS bienes_prestados,
            COUNT(DISTINCT r.id_recurso) AS recursos,COUNT(DISTINCT p.dni_persona) AS solicitantes FROM prestamo p JOIN persona per ON per.dni=p.dni_persona
    JOIN detalle_prestamo d ON d.id_prestamo=p.id_prestamo
    JOIN bien_material b ON b.id_bien=d.id_bien JOIN recurso r ON r.id_recurso=b.id_recurso
    JOIN categoria_recurso c ON c.id_categoria=r.id_categoria WHERE 1=1 AND p.fecha_entrega IS NOT NULL;


-- 11. Solicitudes y reservas: filas sin paginar.
SELECT p.id_reserva,p.tipo_gestion,p.dni_persona,
            CONCAT(per.nombres,' ',per.apellidos) AS solicitante,
            r.nombre AS recurso,c.nombre AS categoria,p.fecha_solicitud,p.fecha_requerida,
            p.estado,p.fecha_limite_vencimiento FROM reserva p JOIN persona per ON per.dni=p.dni_persona
            JOIN recurso r ON r.id_recurso=p.id_recurso
            JOIN categoria_recurso c ON c.id_categoria=r.id_categoria WHERE 1=1 ORDER BY p.fecha_solicitud DESC,p.id_reserva DESC;


-- 12. Solicitudes y reservas: resumen de indicadores.
SELECT COUNT(*) AS detalles,COALESCE(SUM(p.estado IN ('EN_ESPERA','LISTA_PARA_RETIRO')),0) AS pendientes,
            COALESCE(SUM(p.estado='ATENDIDA'),0) AS atendidas,
            COALESCE(SUM(p.estado='CANCELADA'),0) AS canceladas,
            COALESCE(SUM(p.estado='RECHAZADA'),0) AS rechazadas,
            COALESCE(SUM(p.estado='EXPIRADA'),0) AS expiradas FROM reserva p JOIN persona per ON per.dni=p.dni_persona
            JOIN recurso r ON r.id_recurso=p.id_recurso
            JOIN categoria_recurso c ON c.id_categoria=r.id_categoria WHERE 1=1;


-- 13. Sanciones: filas sin paginar.
SELECT s.id_sancion,p.id_prestamo,p.dni_persona,
            CONCAT(per.nombres,' ',per.apellidos) AS solicitante,
            p.tipo_prestamo,b.codigo_inventario,r.nombre AS recurso,c.nombre AS categoria,
            s.fecha,s.motivo,s.descripcion,s.estado,s.fecha_levantamiento,s.justificacion_levantamiento FROM prestamo p JOIN persona per ON per.dni=p.dni_persona
    JOIN detalle_prestamo d ON d.id_prestamo=p.id_prestamo
    JOIN bien_material b ON b.id_bien=d.id_bien JOIN recurso r ON r.id_recurso=b.id_recurso
    JOIN categoria_recurso c ON c.id_categoria=r.id_categoria JOIN incidencia i ON i.id_detalle=d.id_detalle
            JOIN sancion s ON s.id_incidencia_ref=i.id_incidencia WHERE 1=1 ORDER BY s.fecha DESC,s.id_sancion DESC;


-- 14. Sanciones: resumen de indicadores.
SELECT COUNT(*) AS detalles,COALESCE(SUM(s.estado='ACTIVA'),0) AS activas,
            COALESCE(SUM(s.estado='LEVANTADA'),0) AS levantadas,
            COALESCE(SUM(s.estado='CUMPLIDA'),0) AS cumplidas,
            COALESCE(SUM(s.estado='ANULADA'),0) AS anuladas FROM prestamo p JOIN persona per ON per.dni=p.dni_persona
    JOIN detalle_prestamo d ON d.id_prestamo=p.id_prestamo
    JOIN bien_material b ON b.id_bien=d.id_bien JOIN recurso r ON r.id_recurso=b.id_recurso
    JOIN categoria_recurso c ON c.id_categoria=r.id_categoria JOIN incidencia i ON i.id_detalle=d.id_detalle
            JOIN sancion s ON s.id_incidencia_ref=i.id_incidencia WHERE 1=1;


-- 15. Daños y pérdidas: filas sin paginar.
SELECT h.id_historial_estado,h.fecha,b.id_bien,b.codigo_inventario,r.nombre AS recurso,
            c.nombre AS categoria,h.estado_nuevo AS tipo_evento,b.estado AS estado_actual,
            h.dni_responsable AS dni_registrador,CONCAT(reg.nombres,' ',reg.apellidos) AS registrador,
            h.observacion FROM historial_estado h JOIN bien_material b ON b.id_bien=h.id_entidad
            JOIN recurso r ON r.id_recurso=b.id_recurso
            JOIN categoria_recurso c ON c.id_categoria=r.id_categoria
            LEFT JOIN persona reg ON reg.dni=h.dni_responsable WHERE 1=1 AND h.entidad='BIEN_MATERIAL' AND h.estado_nuevo IN ('DANADO','PERDIDO') ORDER BY h.fecha DESC,h.id_historial_estado DESC;


-- 16. Daños y pérdidas: resumen de indicadores.
SELECT COUNT(*) AS detalles,COUNT(DISTINCT b.id_bien) AS bienes,
            COALESCE(SUM(h.estado_nuevo='DANADO'),0) AS danos,
            COALESCE(SUM(h.estado_nuevo='PERDIDO'),0) AS perdidas FROM historial_estado h JOIN bien_material b ON b.id_bien=h.id_entidad
            JOIN recurso r ON r.id_recurso=b.id_recurso
            JOIN categoria_recurso c ON c.id_categoria=r.id_categoria
            LEFT JOIN persona reg ON reg.dni=h.dni_responsable WHERE 1=1 AND h.entidad='BIEN_MATERIAL' AND h.estado_nuevo IN ('DANADO','PERDIDO');

-- 17. Integrantes: se reutiliza para prestamos, devoluciones y sanciones.
-- Sustituir (1, 2, 3) por los id_prestamo presentes en las filas recuperadas.
SELECT pp.id_prestamo, pp.dni_persona, CONCAT(p.nombres, ' ', p.apellidos) AS nombre
FROM participante_prestamo pp
JOIN persona p ON p.dni = pp.dni_persona
WHERE pp.id_prestamo IN (1, 2, 3)
ORDER BY pp.id_prestamo, pp.responsable DESC, pp.id_participante;

-- 18. Cuenta de la sesion: consulta compartida por todas las pantallas.
SET @id_usuario = 1;
SELECT u.id_usuario, p.dni, u.nombre_usuario, u.contrasena_hash,
       u.rol, u.estado_cuenta, p.estado AS estado_persona, p.nombres, p.apellidos
FROM usuario_sistema u
JOIN persona p ON p.dni = u.dni_persona
WHERE u.id_usuario = @id_usuario;

-- 19. Permisos: usar el rol devuelto por la consulta anterior.
SET @rol = 'ADMINISTRADOR';
SELECT permiso FROM rol_permiso WHERE rol = @rol;

-- 20. Categorias del selector: se ejecuta en pantalla, no al descargar CSV.
SELECT * FROM categoria_recurso ORDER BY nombre;
