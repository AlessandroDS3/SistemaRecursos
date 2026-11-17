# Diagnóstico de mantenibilidad

Fecha: 16 de noviembre de 2026.

## Estado de las correcciones

La revisión posterior de capas también está atendida: ampliaciones devuelve
`ContextoAmpliacion` con campos nombrados y el servicio decide los errores de
ausencia; los formatos y la visibilidad HTML están en `presentacion/formatos_reportes.py`.
La pantalla de reportes muestra todos los resultados filtrados, la lectura de filtros
usa `FiltroReporte.desde_datos` y reportes reutiliza `TABLAS_TIPO` de persistencia.
Los ocho reportes conservan el formato, el orden y la visibilidad anteriores.
Esta revisión pasó la suite completa de 139 pruebas, una comprobación adicional de
20 pruebas de reportes y la revisión de tipos de ocho módulos.

Los diez puntos se han atendido. El historial inserta la hora directamente; las
políticas y permisos idénticos no se reescriben; las escrituras de préstamos cargan
solo cabecera y detalles; inicio usa resúmenes SQL; administración omite contadores
del catálogo; el autocompletado devuelve tres campos; los servicios preparan las
versiones de políticas y los POST evitan la lectura del formulario.

El identificador cero se rechaza y la configuración exige sus seis campos juntos.
Los estados de préstamo se comparten desde el dominio y ContextoEntrega documenta
sus claves con TypedDict. El CSV consulta solo filas y carga integrantes únicamente
cuando hay grupos. El archivo SQL se ha sincronizado con el repositorio.

Se conserva el cálculo de estado en SQL y Python porque sirve a recorridos distintos;
una prueba comprueba que coinciden en los cuatro estados. Se conservan permisos,
versiones y bloqueos necesarios. Las secciones siguientes describen el diagnóstico
original como referencia de las correcciones.

Validación final: 125 pruebas de la suite existente y siete pruebas nuevas de
regresión, todas correctas en MySQL temporal. Mypy sin errores en los siete módulos
comprobados y 16 consultas documentadas iguales a las del repositorio. La descarga
de préstamos individuales utiliza una consulta de datos y la de grupos utiliza dos.

Se revisaron los doce repositorios de casos de uso, los servicios, el dominio,
controladores, plantillas y JavaScript, además de la conexión y los auxiliares SQL.
La revisión distingue repetición de código, lecturas excesivas y escrituras que
podrían evitarse. No es una medición de rendimiento con datos de producción.

Las capas están separadas y las pruebas de arquitectura comprueban sus dependencias.
El problema principal está en consultas demasiado amplias y guardados que vuelven a
hacer trabajo aunque los datos sean los mismos. No se encontraron cuerpos de
funciones enteros exactamente repetidos con más de dos instrucciones en el análisis
estructural de los módulos de aplicación.

## Hallazgos y correcciones recomendadas

### 1. Una lectura adicional de la hora por cada evento de historial

- Archivo: `repositorio/base_sql.py`, `registrar_historial_estado`.
- Actual: ejecuta `consultar_fecha_actual()` y luego inserta el historial.
- Efecto: cada evento requiere un SELECT y un INSERT. Una entrega de dos bienes
  registra tres eventos y hace tres lecturas adicionales de hora por esos eventos.
- Recomendación: usar `UTC_TIMESTAMP()` directamente en el INSERT del historial.
  Mantener las lecturas de hora que necesita el dominio para calcular plazos.
- Prioridad: alta. Es una mejora localizada en un auxiliar ya compartido.

### 2. Guardar una política sin cambios genera otra versión

- Archivos: `servicios/servicio_politica_prestamo.py` y
  `repositorio/repositorio_politica_prestamo_sql.py`.
- Actual: desactiva la política vigente e inserta otra incluso si se envían los
  mismos valores.
- Recomendación: comparar sus campos normalizados tras validar permiso y versión;
  si no cambian, conservar la política vigente. Crear una versión cuando cambie una
  condición, para conservar las políticas referenciadas por préstamos anteriores.
- Prioridad: alta. Reduce escrituras y versiones innecesarias.

En este recorrido también hay dos correcciones funcionales pendientes:

- `if identificador:` trata el identificador 0 como un registro nuevo. Conviene
  normalizarlo y distinguir `None` de un identificador proporcionado, como ya hacen
  recursos y bienes.
- Al guardar configuración con horario y sin los cuatro campos de vencimiento,
  `ConfiguracionReservas` introduce sus valores predeterminados. El formulario
  actual envía todos los campos; el servicio debería exigir explícitamente ese
  contrato o conservar los campos omitidos.

### 3. La matriz de permisos se borra y se inserta completa al guardar

- Archivos: `servicios/servicio_rol.py`, `guardar_matriz_permisos`, y
  `repositorio/repositorio_rol_sql.py`, `guardar_matriz_permisos`.
- Actual: aunque no haya cambios, ejecuta DELETE y un INSERT por cada permiso.
- Recomendación inicial: después de comprobar permiso y versión, comparar la matriz
  normalizada con la actual y omitir la escritura si son iguales.
- Prioridad: alta. Actualizar únicamente las diferencias puede estudiarse después;
  para el tamaño actual, saltarse el guardado idéntico es más sencillo.

### 4. Devolución y pérdida cargan el detalle diseñado para la pantalla

- Archivos: `repositorio/repositorio_prestamo_sql.py`, `consultar_prestamo`, y
  `servicios/servicio_prestamo.py`, `registrar_devolucion` y
  `registrar_perdida_bien_material`.
- Actual: la carga incluye estado calculado, información de políticas y sanciones,
  nombres de recursos e integrantes. La devolución y la pérdida no consumen todo eso.
- Recomendación: una lectura de escritura con cabecera y detalles mínimos bajo
  bloqueo; conservar la lectura completa para mostrar el préstamo.
- Prioridad: alta. Revisar el orden de bloqueos y las pruebas concurrentes antes de
  cambiar los JOIN: un JOIN con FOR UPDATE también participa en los bloqueos.

### 5. Inicio carga listados completos para mostrar tres cantidades

- Archivo: `app.py`, función `inicio`.
- Actual: obtiene todos los préstamos para contar pendientes y vencidos; obtiene
  recursos y sus contadores para sumar bienes disponibles.
- Recomendación: consultas de resumen que devuelvan directamente las cantidades,
  manteniendo el alcance del usuario y sus permisos.
- Prioridad: media. Reduce datos transferidos y evita repetir el recorrido de las
  pantallas de listados. La mejora de tiempo debe medirse si se necesita cuantificar.

### 6. Administración de recursos calcula contadores que no utiliza

- Archivos: `repositorio/repositorio_recurso_sql.py`, `consultar_recursos`, y
  `servicios/servicio_recurso.py`, `consultar_administracion_recursos`.
- Actual: reutiliza la consulta del catálogo, que calcula `total` y `disponibles`
  mediante dos subconsultas por recurso. Luego carga los bienes filtrados y prepara
  el resumen de administración con ellos. Esa vista no utiliza los dos contadores
  de cada recurso.
- Recomendación: evitar calcular esos contadores en el recorrido de administración.
  Mantenerlos en catálogo, donde sí se muestran.
- Prioridad: media. Son subconsultas dentro de un SELECT, no dos conexiones nuevas
  por recurso. No confundir contadores de todos los bienes con bienes filtrados.

### 7. El autocompletado de personas devuelve la ficha institucional completa

- Archivos: `repositorio/repositorio_persona_sql.py`, `buscar_personas`, y
  `presentacion/static/aplicacion.js`, `consultarPersonas`.
- Actual: reutiliza `CONSULTA`, que devuelve datos de persona y de sus tres tipos
  institucionales. El autocompletado consume DNI, nombres y apellidos.
- Recomendación: seleccionar solo esos campos; conservar el JOIN de estudiante si
  se necesita buscar también por CUI. No cambiar los campos de búsqueda actuales.
- Prioridad: media. Simplifica el resultado sin introducir nuevas capas.

### 8. Preparación y versión de políticas aparecen en dos capas

- Archivos: `presentacion/controladores/controlador_politica_prestamo.py` y
  `servicios/servicio_politica_prestamo.py`.
- Actual: el controlador prepara la matriz y calcula la versión excluyendo el nombre
  de categoría; la consulta individual calcula su versión en el servicio. Además,
  el controlador lee la política antes de comprobar si la petición es POST, y el
  servicio vuelve a consultarla con bloqueo al guardar.
- Recomendación: preparar la versión en un solo lugar y cargar los datos del
  formulario únicamente para GET. Conservar la lectura bloqueada del guardado.
- Prioridad: media. Elimina una lectura de presentación en cada POST de edición.

### 9. Estados y contratos tienen algunas fuentes repetidas

- La lista de estados de préstamo aparece en `servicio_prestamo.py`, en el catálogo
  de reportes y en `vista_prestamo.html`. Conviene compartir los estados válidos
  desde el dominio; los filtros adicionales PENDIENTES y PERDIDOS son opciones de
  seguimiento, no estados del préstamo.
- El estado se calcula en `dominio/gestion_prestamos/prestamo.py` y en `ESTADO_SQL`.
  Es una duplicación de una regla en Python y SQL. Para los filtros y para las
  escrituras se necesitan ambos recorridos actualmente; conviene probar que
  coinciden, no sustituirlos sin más por `prestamo.estado`, que puede quedar pendiente
  de actualización cuando pasa el tiempo.
- Varios contextos de préstamos siguen siendo diccionarios con claves implícitas.
  Documentar sus claves o tipar los contratos más importantes, siguiendo el caso de
  reservas, ayudaría a detectar cambios de nombre. No hace falta tipar cada diccionario
  ni crear una clase para cada consulta.
- Prioridad: media para los estados y gradual para los contratos.

### 10. Exportación y documentación de reportes aún tienen trabajo redundante

- `ServicioAplicacionReporte.exportar_reportes_csv` utiliza la consulta que también
  carga indicadores y calcula páginas, aunque el CSV solo escribe filas. Se puede
  estudiar un recorrido de filas sin resumen; hacerlo debe simplificar el contrato,
  no añadir numerosos parámetros de control.
- Préstamos, devoluciones y sanciones consultan integrantes cuando hay filas, aunque
  todas sean individuales. Puede evitarse esa consulta cuando no hay préstamos grupales,
  respetando la columna vacía `integrantes` del CSV.
- El SQL de estudio y el repositorio son dos lugares que pueden divergir. La consulta
  manual 02 ya resume directamente `detalle_prestamo`, mientras el repositorio
  conserva los JOIN necesarios para aplicar los filtros del resumen. Ambos producen
  los mismos totales sin filtros en la verificación, pero no son la misma consulta.
- Prioridad: media para las lecturas; alta para explicar correctamente el SQL al profesor.

## Repeticiones que conviene conservar

- Los permisos de una ruta HTTP y los del servicio protegen entradas diferentes.
- Volver a leer con bloqueo antes de editar evita sobrescribir cambios de otra operación.
  La segunda comprobación de versión de persona forma parte de esa protección.
- Los bloqueos amplios de cuentas protegen al último administrador. No deben retirarse
  solo porque una consulta parezca repetida; se puede estudiar una reducción para
  cambios que no afecten rol, estado o DNI con sus pruebas de concurrencia.
- Los distintos cambios de estado de bienes en entrega, reserva, devolución y pérdida
  tienen condiciones e historiales propios. Comparten escritura SQL, no todas las reglas.
- Métodos cortos que delegan al repositorio permiten mantener las capas y los nombres
  del caso de uso. Un CRUD genérico no está justificado por esas pocas líneas.
- Las macros de formularios, historial, indicadores y estados ya comparten presentación.
  El CSS está organizado y no requiere dividirse en muchos archivos por su extensión.

## Orden recomendado

1. Historial y guardados sin cambios de políticas y permisos.
2. Lecturas mínimas para devolución/pérdida, autocompletado e inicio.
3. Preparación de políticas y contadores de administración.
4. Estados compartidos y contratos importantes, a medida que se revisa cada recorrido.

La implementación autorizada de reportes se validó con 125 pruebas del proyecto y
128 combinaciones de consultas y filtros antes de estas correcciones. La validación
de las correcciones incluye la suite completa y pruebas de regresión específicas.
