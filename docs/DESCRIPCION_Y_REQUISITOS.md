# 1. Descripción

El sistema administra el préstamo de libros, equipos y otros materiales de la Escuela Profesional de Ciencia de la Computación. Permite saber qué recursos ofrece la escuela, qué ejemplares tiene en inventario, a quién se entregaron y cuándo deben devolverse.

Un recurso es una entrada del catálogo, como un modelo de laptop. Cada unidad de ese modelo es un bien material con código de inventario y estado propios. El usuario puede consultar el catálogo y reservar un recurso para una fecha futura. El encargado prepara el bien y registra el préstamo al confirmar la entrega física. Cada bien tiene su propio plazo y puede devolverse por separado.

El sistema también permite gestionar personas y cuentas, configurar políticas según el tipo de persona y la categoría del recurso, dar seguimiento a incidencias y sanciones, consultar historiales y generar reportes.

# 2. Problema identificado

El proyecto parte de un proceso manual de préstamo de materiales. Los registros dispersos dificultan verificar la disponibilidad de cada bien, identificar quién lo tiene, controlar los plazos y reconstruir lo ocurrido ante una devolución tardía, un daño o una pérdida.

El sistema reúne en un mismo lugar el inventario, las reservas, las entregas, las devoluciones y las sanciones. Esto facilita el seguimiento de cada bien y la aplicación de las políticas de préstamo.

# 3. Objetivo general

Gestionar el préstamo de recursos de la Escuela Profesional de Ciencia de la Computación mediante un sistema que controle la disponibilidad de los bienes y permita seguir cada operación desde la reserva o entrega hasta la devolución o regularización.

# 4. Actores del sistema

Cada cuenta tiene uno de los tres roles fijos del sistema. Estudiante, docente y administrativo son tipos de persona. El tipo de persona determina las políticas de préstamo aplicables y el rol determina las acciones disponibles en la aplicación.

## 4.1. Administrador

Es responsable de la administración general del sistema y puede:

- Registrar, consultar, modificar y desactivar personas de la institución.
- Gestionar cuentas, asignarles uno de los tres roles y consultar la matriz de permisos.
- Administrar categorías, recursos y bienes materiales, así como consultar el inventario.
- Gestionar préstamos, reservas, devoluciones y ampliaciones.
- Configurar políticas de préstamo, horario de atención, límites de artículos y plazos de reserva y sanción.
- Gestionar sanciones y regularizaciones. La aplicación y el levantamiento de sanciones muy graves corresponden exclusivamente a este rol.
- Consultar historiales y descargar reportes en CSV y PDF.

## 4.2. Encargado de préstamos

Es responsable de la entrega, recepción y seguimiento de los bienes materiales y puede:

- Registrar, consultar, modificar y desactivar personas de la institución.
- Consultar el catálogo y el inventario para verificar disponibilidad.
- Preparar, entregar, cancelar, rechazar y expirar reservas, según su estado.
- Registrar préstamos individuales y grupales, devoluciones por bien y ampliaciones de plazo.
- Registrar pérdidas, evaluar incidencias, tramitar regularizaciones y levantar sanciones leves con justificación cuando corresponda.
- Consultar historiales y descargar reportes en CSV y PDF.

## 4.3. Usuario

Es la persona que utiliza los recursos de la escuela y puede:

- Iniciar y cerrar sesión, y cambiar su contraseña.
- Buscar recursos, consultar la disponibilidad y revisar las condiciones de préstamo aplicables.
- Registrar, consultar y cancelar sus propias reservas, según su estado.
- Solicitar un préstamo presencialmente con el encargado.
- Consultar sus préstamos y descargar su historial en CSV y PDF.

### Estudiante

Persona matriculada en la escuela profesional. Debe tener matrícula vigente para reservar o recibir bienes en préstamo.

### Docente

Persona que pertenece al personal académico. Puede reservar y recibir bienes en préstamo de acuerdo con las políticas definidas para docentes.

### Administrativo

Persona que pertenece al personal administrativo. Puede reservar y recibir bienes en préstamo de acuerdo con las políticas definidas para administrativos.

# 5. Requisitos del sistema

## 5.1. Requisitos funcionales

| Código | Requisito funcional |
| --- | --- |
| **RF01** | Permitir iniciar sesión con nombre de usuario y contraseña, cerrar sesión y cambiar la contraseña. Si la cuenta requiere un cambio de contraseña, solicitarlo antes de habilitar el resto de opciones. |
| **RF02** | Permitir al administrador y al encargado registrar, consultar, modificar y desactivar personas. Consultar la ficha completa requiere el permiso de consulta de personas. |
| **RF03** | Clasificar a las personas como estudiantes, docentes o administrativos y registrar los datos correspondientes a cada tipo. |
| **RF04** | Permitir al administrador crear, consultar y modificar cuentas asociadas a personas registradas, incluida la gestión de su estado. Cada persona puede tener como máximo una cuenta. |
| **RF05** | Permitir al administrador asignar a cada cuenta uno de los roles fijos `USUARIO`, `ENCARGADO_PRESTAMOS` o `ADMINISTRADOR`. |
| **RF06** | Aplicar los permisos predefinidos de cada rol y permitir que el administrador consulte la matriz de permisos. |
| **RF07** | Permitir al administrador registrar, consultar y modificar las categorías de recursos, y eliminar una categoría cuando sus relaciones lo permitan. |
| **RF08** | Permitir al administrador registrar, consultar y modificar los recursos del catálogo y asociarlos a una categoría. |
| **RF09** | Registrar cada bien material bajo un recurso con un código de inventario único. Guardar su número de serie, ubicación, fecha de adquisición y descripción cuando se proporcionen. |
| **RF10** | Permitir consultar el catálogo y la disponibilidad de los recursos, y permitir al personal autorizado consultar el estado de cada bien en el inventario. |
| **RF11** | Permitir al administrador cambiar el estado de un bien a disponible, dañado, en mantenimiento o perdido, según las transiciones permitidas. Los estados prestado y reservado se gestionan en sus respectivos flujos. |
| **RF12** | Registrar la fecha, el responsable y la observación del cambio de estado de un bien, cuando correspondan, y permitir consultar su historial. |
| **RF13** | Registrar el préstamo al confirmar la entrega física dentro del horario de atención. Asociar el solicitante, el encargado y los bienes entregados. La entrega puede ser directa o proceder de una reserva preparada. |
| **RF14** | Validar que cada bien esté disponible para la entrega directa o preparado para la reserva que se atiende. Exigir que la política permita la salida de cada bien si el préstamo es para uso externo. |
| **RF15** | Calcular el plazo y la fecha límite de devolución por bien según su política. En los préstamos cuyo plazo se expresa en horas, limitar la devolución a la hora de cierre. |
| **RF16** | Registrar préstamos individuales y grupales. Identificar en los grupales al responsable y a los demás participantes, y validar la elegibilidad y el cupo de todos. Cada bien pendiente del grupo cuenta una vez para cada integrante, incluido el responsable. |
| **RF17** | Registrar devoluciones por bien con fecha, encargado que lo recibe, condición y observaciones. En devoluciones parciales, mantener pendientes los bienes restantes. |
| **RF18** | Actualizar los estados del préstamo y de los bienes según la entrega, el vencimiento, la devolución o la regularización que corresponda. |
| **RF19** | Permitir reservar un recurso para una fecha futura, consultar y cancelar reservas propias, y permitir al encargado preparar un bien, confirmar su entrega, rechazar o expirar una reserva. Liberar el bien preparado al cancelar, rechazar o vencer la reserva. |
| **RF20** | Permitir al personal con permiso de gestión de préstamos calcular y aplicar una ampliación al plazo de un bien prestado, pendiente y aún sin vencer. Aplicar los límites de la política y registrar el cambio en el historial. |
| **RF21** | Registrar incidencias asociadas al bien prestado por retraso, daño, pérdida, salida no autorizada o falta de custodia. |
| **RF22** | Registrar, consultar y evaluar sanciones según su gravedad. Aplicar la leve por retraso y permitir su levantamiento anticipado con justificación después de recibir el bien. Exigir el cumplimiento del plazo y la regularización para cerrar una grave. Reservar al administrador la aplicación y el levantamiento de la muy grave, que requiere regularización y justificación para rehabilitar a la persona. En préstamos grupales, aplicar el efecto de las sanciones a todos los participantes. |
| **RF23** | Administrar políticas por tipo de persona y categoría del recurso, con plazo en horas o días y permiso de salida. Configurar el horario, el máximo total de bienes pendientes por tipo de persona, los plazos de espera y retiro de reservas y los plazos de sanción. |
| **RF24** | Registrar y permitir la consulta del historial de cambios de estado de préstamos, bienes, reservas y sanciones. Registrar también los cambios en la configuración de plazos de sanción. |
| **RF25** | Revisar periódicamente los vencimientos mientras esté activo el proceso automático. Actualizar préstamos y reservas, generar sanciones leves por retraso y mostrar alertas de posibles pérdidas o problemas de custodia para evaluación. La confirmación de esos casos requiere revisión del personal autorizado. |
| **RF26** | Permitir filtrar préstamos activos, vencidos, devueltos, parcialmente devueltos y regularizados, así como localizar préstamos con bienes pendientes o con bienes perdidos pendientes. Limitar la vista del usuario a sus propios préstamos. |
| **RF27** | Mostrar en Inicio los indicadores de préstamos pendientes de devolución, préstamos vencidos y bienes disponibles. Mostrar accesos a las operaciones según el rol. |
| **RF28** | Permitir al administrador y al encargado consultar reportes e historiales con filtros y exportarlos a CSV y PDF. Permitir al usuario consultar y descargar su propio historial. |
| **RF29** | Verificar que la persona esté activa y, si es estudiante, que la matrícula esté vigente. Bloquear nuevas reservas y préstamos ante sanciones activas o bienes vencidos pendientes, y permitir la devolución de bienes ya prestados. |
| **RF30** | Registrar la regularización de una incidencia según corresponda mediante devolución, recuperación, reparación, reposición o verificación. Para una reposición, registrar el bien equivalente con un código de inventario nuevo y conservar el historial del bien original. |

Los valores iniciales son 14 días para la sanción leve, 180 días para la grave y 7 días adicionales para revisar una posible pérdida. El administrador puede configurarlos y cada sanción conserva los valores registrados al momento de aplicarse.

## 5.2. Requisitos no funcionales

| Código | Tipo | Requisito no funcional |
| --- | --- | --- |
| **RNF01** | Seguridad | Proteger el acceso mediante autenticación con nombre de usuario y contraseña. Almacenar las contraseñas como hashes y proteger los formularios de modificación con tokens CSRF. |
| **RNF02** | Control de acceso | Verificar en el servidor los permisos del rol y el alcance de los datos consultados, incluidos los préstamos, las reservas y el historial propios. |
| **RNF03** | Integridad | Mantener coherentes el inventario, los préstamos y las reservas mediante validaciones y transacciones. Cada devolución debe corresponder a un bien asociado a un préstamo. |
| **RNF04** | Rendimiento | Responder las consultas de recursos, préstamos, reservas y personas en un máximo de 3 segundos bajo condiciones normales de uso. Objetivo pendiente de verificar mediante mediciones. |
| **RNF05** | Usabilidad | Presentar formularios, filtros y mensajes de validación comprensibles para realizar las operaciones habituales sin conocimientos técnicos especializados. |
| **RNF06** | Persistencia | Almacenar en MySQL 8 los registros de personas, cuentas, inventario, préstamos, devoluciones por bien, reservas, incidencias, sanciones, políticas e historiales. |
| **RNF07** | Mantenibilidad | Organizar la aplicación por módulos y cuatro capas. `presentacion` contiene las rutas y vistas, `servicios` los casos de uso, `dominio` las reglas y contratos, y `repositorio` la persistencia MySQL. |
| **RNF08** | Respaldo | Realizar copias de seguridad periódicas de la base de datos mediante herramientas de MySQL. La ejecución y verificación del respaldo son tareas de operación de la base de datos. |
| **RNF09** | Validación | Validar en el servidor los campos obligatorios, los formatos, las fechas, los estados y las transiciones permitidas antes de guardar los datos. |
| **RNF10** | Trazabilidad | Registrar las operaciones relevantes de préstamos, bienes, reservas y sanciones con fecha, estados y, cuando corresponda, responsable y observación. |

## Referencias del proyecto

- [Descripción de roles, sanciones y arquitectura](../README.md)
- [Esquema MySQL](../SistemaRecursos/sql/schema.sql)
- [Roles y permisos definidos en el dominio](../SistemaRecursos/dominio/gestion_personas_usuarios/rol.py)
- [Modelo de dominio](uml/modelo_dominio.mdj)
- [Arquitectura extendida](uml/arquitectura_extendida.mdj)
