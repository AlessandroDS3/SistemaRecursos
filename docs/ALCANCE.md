# Alcance acumulado estimado: 25%

El porcentaje es una estimación de alcance para avanzar gradualmente, no una medición de líneas de código. No aparece dentro de la web.

| Parte | Peso de referencia | Estado |
|---|---:|---|
| Base, catálogo y ejemplares | 15% | Implementado |
| Personas: registro, consulta, búsqueda y fichas por tipo | 10% | Implementado |
| Cuentas, autenticación, roles y permisos | 10% | Login local añadido; roles y permisos pendientes |
| Políticas y préstamos individuales | 25% | Pendiente |
| Devoluciones e incidencias | 15% | Pendiente |
| Reservas, grupos y ampliaciones | 15% | Pendiente |
| Sanciones, avisos, mantenimiento y despliegue | 10% | Pendiente |

Se conserva el modelo detallado de ddd_completo.mdj: Recurso y BienMaterial independientes, categoría, Persona como raíz y especializaciones Estudiante, Docente y Administrativo. La relación de especialización se persiste con una tabla por tipo y clave foránea hacia Persona. Los identificadores se generan en MySQL.

Los atributos personales e institucionales corresponden al modelo. Se añade el discriminador tipo para seleccionar la especialización y fechaRegistro como dato técnico automático. La fechaAdquisicion del bien conserva el nombre previo por compatibilidad, y en nuevas altas representa la fecha de registro automática. Las series aleatorias son identificadores internos, no números del fabricante.

Reglas propuestas: documento alfanumérico de 4–20 caracteres, código requerido por tipo, correo requerido, teléfono opcional y ciclo entero de 1–20 para estudiantes. Nuevas personas activas; duplicados rechazados. No se presume verificación externa de documentos ni matrículas. Consultas y registros locales protegidos con inicio de sesión; el despliegue público sigue pendiente.

No incluye todavía edición/baja de personas, cambios de estado, préstamos, devoluciones, reservas ni sanciones. La nueva paleta visual es azul, verde claro y blanco.

## Ampliación solicitada: login
Cuentas locales con usuario único, contraseña derivada mediante scrypt, sesión y cierre de sesión. Las cuentas se administran mediante crear_usuario.cmd y no se vinculan todavía a Persona ni a roles. Todas acceden a catálogo y directorio. No se implementó registro público ni recuperación de contraseña. El 25% corresponde al hito previo; esta mejora no pretende certificar un nuevo porcentaje.
