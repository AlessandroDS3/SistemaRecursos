# Auditoría de mantenibilidad

Fecha: 12 de noviembre de 2026. Proyecto revisado: `D:\TI_sistema_recursos\SistemaRecursos_local`.

## Dictamen

El proyecto tiene una separación de capas aprovechable. El análisis de los imports internos no encontró ciclos ni dependencias del dominio hacia servicios, presentación o repositorios. Tampoco encontró servicios importando repositorios concretos, ni controladores importando módulos de repositorios. Esta comprobación es estática y no demuestra por sí sola que todas las responsabilidades estén bien ubicadas.

La mantenibilidad está comprometida principalmente por tres problemas: la estructura SQL está desincronizada y una instalación de pruebas falla; hay decisiones de negocio que solo se aplicaron al diagrama; y parte de la coordinación entre reservas, préstamos, bienes y sanciones depende de detalles concretos de repositorios.

Conviene estabilizar esas partes antes de seguir añadiendo funciones. Una reorganización completa de carpetas ahora aumentaría el riesgo y dificultaría distinguir cambios de comportamiento de simples movimientos de archivos.

## Alcance y comprobaciones

| Comprobación | Resultado observado |
|---|---|
| Inventario de la aplicación | 129 archivos: 108 Python, 11 HTML, 6 JavaScript, 1 CSS, 2 SQL y 1 README. Se excluyeron entorno virtual, cachés y `datos_locales`. |
| Código Python de producción | 100 módulos analizados mediante AST, incluidos sus imports, clases, métodos y funciones. Las otras 8 unidades Python son archivos de pruebas. |
| Revisión detallada | Escritura y consulta de préstamos, devolución, pérdida, reservas, sanciones, configuración, acceso, permisos, recursos, validaciones y reportes. |
| Rutas y plantillas | La aplicación registra 66 rutas propias; las 11 plantillas HTML se analizan correctamente. Los 6 JavaScript pasan la comprobación de sintaxis. |
| SQL | Ambos archivos declaran 20 tablas, pero difieren en la definición de 4 de ellas. |
| Diagramas | Ambos MDJ tienen un gráfico. El MDJ simple omite `dni_solicitante`; el extendido y el código lo conservan. Se revisaron también las conexiones conceptuales con los actores. |
| Pruebas existentes | Se localizaron 49 métodos de prueba. La ejecución informó `Ran 35 tests` y `FAILED (errors=21)`, incluidos errores en `setUpClass` de dos clases. Las 16 pruebas sin dependencia de la base de integración terminaron correctamente. La preparación de datos impidió ejecutar normalmente el resto de escenarios. |
| Reproducciones independientes | MySQL 8.0.46 temporal en el puerto 13307: importación de ambos SQL, respuestas de error, pérdida, devolución dañada y consistencia de ampliaciones. |
| Integridad del trabajo previo | Se compararon hashes de los 129 archivos inventariados al terminar: ninguno fue cambiado por la auditoría. No se modificaron SQL, código de la aplicación, diagramas ni datos del servidor habitual. |

Los 21 errores no equivalen a 21 defectos funcionales distintos: muchas pruebas fallan antes de entrar en el caso que pretendían comprobar. No se midió rendimiento bajo carga ni se ejecutó una prueba exhaustiva de concurrencia o de todas las combinaciones de interfaz.

## Hallazgos prioritarios

### A01 — P1: el SQL de pruebas no puede importarse desde cero

**Evidencia:** [datos_prueba.sql:151](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/sql/datos_prueba.sql:151). El `CHECK` de `detalle_prestamo` comprueba `dni_encargado_devolucion`, que participa en una FK con `ON UPDATE CASCADE`.

La importación falla con:

```text
3823 (HY000): Column 'dni_encargado_devolucion' cannot be used in a check constraint
'detalle_prestamo_chk_1': needed in a foreign key constraint
'detalle_prestamo_ibfk_4' referential action.
```

**Consecuencia:** un compañero que siga las instrucciones del README no puede preparar la base de demostración. También quedan bloqueadas las pruebas de integración.

**Corrección recomendada:** resolver la compatibilidad entre esa restricción y la FK en los dos SQL. Si se conserva el cambio de DNI con cascada, mantener la consistencia de fecha/condición en el `CHECK` y validar el encargado en la aplicación, como ya hace `DetallePrestamo`. Si se decide que el DNI es inmutable, documentarlo y revisar las FK antes de retirar la cascada. No cambiar esta regla de forma distinta en cada SQL.

**Aceptación:** ambos archivos se importan en bases nuevas; una devolución sin encargado es rechazada por el flujo de aplicación; el conjunto de integración puede iniciar.

### A02 — P1: los dos SQL ya no representan la misma estructura

**Evidencia:** comparación de las 20 sentencias `CREATE TABLE` en [schema.sql](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/sql/schema.sql) y [datos_prueba.sql](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/sql/datos_prueba.sql).

| Tabla | Diferencia actual |
|---|---|
| `detalle_prestamo` | El SQL de datos agrega las condiciones del encargado que provocan A01. |
| `ampliacion_prestamo` | Solo el SQL de datos exige `fecha_limite_nueva > fecha_limite_anterior`. |
| `bien_material` | Solo el SQL de datos declara `UNIQUE (id_bien, id_recurso)`. |
| `reserva` | El SQL vacío referencia el bien por `id_bien`; el de datos usa una FK compuesta para exigir que el bien pertenezca al recurso reservado. |

**Reproducción:** `schema.sql` importa 20 tablas. Sobre esa estructura, MySQL acepta una ampliación cuya fecha nueva es anterior a la fecha previa.

**Consecuencia:** el comportamiento depende del archivo con que se creó la base. Una corrección hecha solo en uno deja al otro entorno con reglas diferentes.

**Corrección recomendada:** conservar los dos SQL solicitados. Usar una definición de estructura como autoridad y generar o sincronizar la parte estructural del archivo con datos; añadir una comprobación de igualdad de las 20 definiciones. No hace falta introducir migraciones para esta etapa del proyecto.

**Aceptación:** los bloques de estructura coinciden, con las mismas FK y restricciones, y ambos se importan por separado.

### A03 — P2: las decisiones de los diagramas no están cerradas en la implementación

**Evidencia:** [ampliacion_prestamo.py:18](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/dominio/gestion_prestamos/ampliacion_prestamo.py:18), [schema.sql:213](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/sql/schema.sql:213), [MODELO_DOMINIO.mdj](D:/TI_sistema_recursos/SistemaRecursos_local/MODELO_DOMINIO.mdj) y [DDD_arquitectura_extendida_actualizada.mdj](D:/TI_sistema_recursos/SistemaRecursos_local/DDD_arquitectura_extendida_actualizada.mdj).

El MDJ simple obtiene al solicitante de la ampliación desde el préstamo. La clase Python y ambos SQL siguen guardando `dni_solicitante`. El extendido conserva ese campo porque reproduce el código existente. Las ediciones anteriores del diagrama no completaron ese cambio de implementación; esa es una responsabilidad pendiente de nuestro trabajo, no un defecto descubierto por añadir carpetas.

Los actores se expresan ahora mediante `UsuarioSistema` en el MDJ. El código toma el DNI de `g.usuario.persona`, y las FK de los actores siguen apuntando a `persona`: [schema.sql:148](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/sql/schema.sql:148), [schema.sql:173](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/sql/schema.sql:173), [schema.sql:237](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/sql/schema.sql:237) y [schema.sql:250](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/sql/schema.sql:250).

Una relación conceptual con la cuenta puede resolverse mediante su persona: no obliga por sí sola a cambiar todos los DNI por `id_usuario`. Hay que distinguir el modelo conceptual de un diagrama que pretende representar FK exactas. Actualmente esa distinción resulta ambigua.

**Corrección recomendada:** registrar la regla acordada —solo el responsable solicita la ampliación— y aplicarla conjuntamente al modelo, la clase, los dos SQL y las verificaciones correspondientes. Definir también cómo se representa y valida al actor de cada comando. Conservar claramente separadas las relaciones del solicitante, los integrantes y el personal que registra acciones.

**Aceptación:** ambos diagramas tienen un alcance declarado y no obligan al desarrollador a adivinar qué campos están implementados y cuáles son decisiones pendientes.

### A04 — P2: reservas utiliza capacidades concretas de préstamos que no están en su interfaz

**Evidencia:** [repositorio_reserva_sql.py:9](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/repositorio/repositorio_reserva_sql.py:9), [repositorio_reserva_sql.py:253](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/repositorio/repositorio_reserva_sql.py:253) e [i_repositorio_prestamo.py:10](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/dominio/gestion_prestamos/i_repositorio_prestamo.py:10).

`RepositorioReservaSQL` construye un `RepositorioPrestamoSQL`, llama a `validar_sin_prestamos_vencidos` y entrega una reserva pasando `cursor` e `id_bien_reservado` a `registrar_prestamo`. Esas capacidades adicionales no forman parte de `IRepositorioPrestamo`.

El repositorio de préstamos concentra 710 líneas con consultas, elegibilidad, políticas, cupo, entrega, devolución, pérdida, cambios de inventario, historial y aplicación de sanciones. El tamaño ayuda a localizar el punto de revisión; la dependencia de reservas sobre su API concreta explica la propagación de cambios.

**Consecuencia:** cambiar la implementación o sustituir el repositorio exige conocer llamadas externas no descritas por el contrato. Las pruebas necesitan comprender también el cursor y los bloqueos compartidos.

**Corrección recomendada:** establecer una entrada y un responsable explícitos para confirmar una entrega, sea directa o desde reserva. Mantener las consultas y los bloqueos en persistencia, y las decisiones puras en el dominio. Definir la colaboración transaccional con un contrato claro antes de mover métodos.

**Condición que debe preservarse:** préstamo, detalles, participantes, reserva, inventario e historial deben confirmarse o revertirse juntos. No separar esta operación en llamadas que abran y confirmen conexiones independientes. No se justifica añadir una clase por cada sentencia SQL.

### A05 — P2: varias reglas o consultas compartidas tienen más de un punto de mantenimiento

| Elemento | Evidencia | Efecto de mantenimiento |
|---|---|---|
| Estado actual del préstamo | [prestamo.py:76](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/dominio/gestion_prestamos/prestamo.py:76) y [repositorio_prestamo_sql.py:19](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/repositorio/repositorio_prestamo_sql.py:19) | El cálculo existe en Python y SQL. Los reportes importan la consulta del repositorio de préstamos. Una nueva regla debe conservar ambos cálculos equivalentes. |
| Personas bloqueadas por sanción grupal | [repositorio_prestamo_sql.py:210](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/repositorio/repositorio_prestamo_sql.py:210) y [repositorio_reserva_sql.py:142](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/repositorio/repositorio_reserva_sql.py:142) | La búsqueda del responsable o de un participante sancionado está repetida. Cambiar el alcance de la sanción obliga a revisar ambas rutas. |
| Lectura del horario | [repositorio_prestamo_sql.py:44](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/repositorio/repositorio_prestamo_sql.py:44) y [repositorio_politica_prestamo_sql.py:18](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/repositorio/repositorio_politica_prestamo_sql.py:18) | Se repiten consulta, validación de existencia y construcción del horario. |
| Validación de enteros positivos | [validacion_recurso.py:21](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/dominio/gestion_recursos/validacion_recurso.py:21) y [validacion_identificadores.py:1](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/servicios/validacion_identificadores.py:1) | Implementaciones prácticamente iguales, ubicadas en capas diferentes. |

**Corrección recomendada:** dar un propietario explícito a cada regla y reutilizar una API estable. Para los cálculos SQL/Python que se mantienen por razones de consulta, añadir casos de equivalencia de estados en lugar de asumir que se actualizan solos. La repetición de una validación de entrada y una restricción de integridad puede ser deliberada; lo que debe evitarse son dos definiciones divergentes de la regla.

### A06 — P2: ampliaciones e incidencias se representan con más capacidad de la que está conectada a la aplicación

**Evidencia:** [ampliacion_prestamo.py:25](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/dominio/gestion_prestamos/ampliacion_prestamo.py:25), [tipo_incidencia.py:8](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/dominio/gestion_prestamos/tipo_incidencia.py:8), [incidencia.py](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/dominio/gestion_prestamos/incidencia.py) y [repositorio_prestamo_sql.py:659](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/repositorio/repositorio_prestamo_sql.py:659).

`aprobar` y `rechazar` de la ampliación contienen `pass`. No se encontró un flujo activo de servicio/controlador/repositorio de ampliaciones. Los módulos `ampliacion_prestamo`, `incidencia` y el archivo separado `tipo_incidencia` no son alcanzables desde los imports estáticos de `app.py`; esto no implica que sus tablas estén sin uso. Las incidencias de retraso sí se escriben mediante SQL.

Hay dos `TipoIncidencia`: uno usa tres valores de texto, y el otro cinco valores numéricos. El SQL admite los tres tipos de texto. La duplicación deja dos respuestas posibles para quien busca el enum correcto.

**Reproducción:** sobre una base temporal creada con `schema.sql` y los INSERT originales, reportar una pérdida dejó el inventario en `PERDIDO` y creó **cero incidencias de pérdida**. Recibir después ese bien como `DANADO`, con plazo aún vigente, creó **cero incidencias de daño**. Esos flujos registran el inventario y el historial; no completan el recorrido conceptual `Detalle → Incidencia → Sanción` para esos dos tipos.

**Corrección recomendada:** señalar las ampliaciones como pendientes hasta implementar su operación completa; conservar un solo enum de incidencias; definir cuándo una pérdida o daño debe crear una incidencia y en qué condiciones genera sanción. La auditoría confirma la ausencia del registro automático, pero no inventa una regla de sanción que aún debe precisarse.

### A07 — P2: algunos fallos se presentan como respuestas exitosas

**Evidencia:** [app.py:168](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/app.py:168) y [app.py:172](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/app.py:172).

Los manejadores generales de `ValueError`/`LookupError` y de MySQL devuelven una plantilla sin estado HTTP explícito. El de MySQL tampoco registra la excepción original.

**Reproducción:** invocando los manejadores registrados dentro de un contexto Flask, tanto un error de validación como un `DatabaseError` produjeron estado **200**. El controlador de reportes ya trata sus filtros inválidos como 400, de modo que tampoco hay una convención uniforme.

**Consecuencia:** una prueba, un cliente o quien revisa registros puede interpretar un error como éxito; se pierde información necesaria para identificar el fallo de base de datos.

**Corrección recomendada:** establecer una convención de validación, ausencia, conflicto, permiso y error inesperado; registrar internamente los errores de infraestructura y devolver un mensaje apropiado al usuario. Corregir primero el error de base marcado como 200. La selección de estados para formularios debe quedar documentada y probada.

### A08 — P2: la preparación de pruebas hace que un fallo común oculte otras comprobaciones

**Evidencia:** [test_configuracion_general.py:19](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/tests/test_configuracion_general.py:19) y [test_configuracion_general.py:60](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/tests/test_configuracion_general.py:60).

El caso que debe comprobar que `schema.sql` se importa desde cero primero carga `datos_prueba.sql` en `setUp`. Por ello no alcanza a comprobar el esquema vacío cuando falla la base de demostración, aunque la reproducción independiente importó correctamente sus 20 tablas. Otras clases también dependen de esa misma preparación.

Las pruebas de MySQL se omiten si no existe `TEST_MYSQL_PORT`. El README no describe un comando de verificación con las variables necesarias. Un resultado local sin MySQL puede cubrir únicamente la parte unitaria.

**Corrección recomendada:** separar la comprobación de importación de cada SQL de las pruebas funcionales; preparar cada caso con los mínimos datos que necesita; documentar cómo ejecutar integración y exigir que se informe si fue omitida. Después de A01, volver a ejecutar las 49 pruebas para descubrir posibles fallos actualmente tapados por la preparación.

### A09 — P3: el seguimiento de una operación es desigual entre módulos

**Evidencia:** [controlador_reserva.py](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/presentacion/controladores/controlador_reserva.py), [controlador_reporte.py](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/presentacion/controladores/controlador_reporte.py), [servicio_rol.py:25](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/servicios/servicio_rol.py:25) y [validacion_recurso.py](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/dominio/gestion_recursos/validacion_recurso.py).

Seis módulos usan clases `Vista...`; acceso, reservas y reportes renderizan directamente desde sus controladores. El servicio de roles consume `formulario.getlist`, mientras otros servicios reciben diccionarios o datos de entrada. Las funciones genéricas `texto`, `entero` e `instante_utc` se ubican en `gestion_recursos`, aunque se importan desde numerosos contextos. Ese módulo y el de validación de personas tienen 20 módulos consumidores cada uno.

**Consecuencia:** acertar el prefijo del archivo no siempre basta para saber qué recorrido seguirá una operación ni qué formato debe recibir el servicio.

**Corrección recomendada:** adoptar una convención sencilla de presentación, de datos de entrada y de ubicación de validaciones comunes. No hace falta crear vistas vacías ni más capas. Mantener el mapa operativo siguiente, que explica también las excepciones actuales.

## Mapa para seguir las operaciones actuales

Todos los archivos de esta tabla están dentro de `SistemaRecursos/`. Se mantiene un nombre principal por función; la tabla identifica las colaboraciones que hoy no se deducen del nombre del controlador.

| Operación | Presentación | Servicio | Contrato → implementación de persistencia |
|---|---|---|---|
| Iniciar/cerrar sesión | `controlador_acceso.py` → `vista_acceso.html` | `servicio_acceso.py` | `IRepositorioAcceso` → `repositorio_acceso_sql.py` |
| Registrar/editar personas | `controlador_persona.py` → `VistaPersona` → `vista_persona.html` | `servicio_persona.py` | `IRepositorioPersona` → `repositorio_persona_sql.py` |
| Crear/editar/activar cuentas | **`controlador_persona.py`** → `VistaPersona` | **`servicio_acceso.py`** | `IRepositorioAcceso` → `repositorio_acceso_sql.py`; también consulta personas y roles |
| Asignar rol a una cuenta | `controlador_rol.py` → `VistaRol` | `servicio_rol.py` | Consulta roles mediante `IRepositorioRol`; cambia la cuenta mediante `IRepositorioAcceso` |
| Cambiar la matriz de permisos | `controlador_rol.py` → `VistaRol` | `servicio_rol.py` | `IRepositorioRol` → `repositorio_rol_sql.py` |
| Recursos y categorías | `controlador_recurso.py` → `VistaRecurso` | `servicio_recurso.py` | `IRepositorioRecurso` → `repositorio_recurso_sql.py`; colabora con bienes |
| Bienes e inventario | `controlador_bien_material.py` → `VistaBienMaterial` | `servicio_bien_material.py` | `IRepositorioBienMaterial` → `repositorio_bien_material_sql.py`; consulta recursos |
| Horario, cupo y políticas | `controlador_politica_prestamo.py` → `VistaPoliticaPrestamo` | `servicio_politica_prestamo.py` | `IRepositorioPoliticaPrestamo` → `repositorio_politica_prestamo_sql.py`; reserva usa además el helper SQL de vencimiento |
| Entrega directa y devolución | `controlador_prestamo.py` → `VistaPrestamo` | `servicio_prestamo.py` | `IRepositorioPrestamo` → `repositorio_prestamo_sql.py` |
| Reportar pérdida | `controlador_prestamo.py` | `servicio_prestamo.py` | `RepositorioPrestamoSQL.reportar_perdida`; cambia inventario e historial |
| Solicitud/reserva y entrega de reserva | `controlador_reserva.py` → `vista_reserva.html` | `servicio_reserva.py` | `IRepositorioReserva` → `repositorio_reserva_sql.py`; la entrega reutiliza el repositorio concreto de préstamos |
| Levantar una sanción de retraso | **`controlador_prestamo.py`** | **`servicio_sancion.py`** | `IRepositorioSancion` → `repositorio_sancion_sql.py` |
| Aplicar sanciones automáticas | `procesador_vencimientos.py`, iniciado en `app.py` | `servicio_sancion.py` | `repositorio_sancion_sql.py` → `sanciones_vencimiento_sql.py` |
| Expirar reservas automáticamente | El mismo procesador | `servicio_reserva.py` | `repositorio_reserva_sql.py` |
| Reportes y CSV | `controlador_reporte.py` → `vista_reporte.html` | `servicio_reporte.py` | `IRepositorioReporte` → `repositorio_reporte_sql.py`; reutiliza la consulta de estado de préstamos |
| Ampliaciones | No existe un recorrido activo completo | Pendiente | Entidad y tabla existentes; métodos de aprobación pendientes |

Buscar archivos para auditar no demuestra desorden. El criterio de mantenibilidad es poder localizar al responsable de una operación y comprender sus entradas, salidas y efectos sin reconstruir reglas escondidas entre módulos.

## Qué cambios deberían afectar a pocos archivos

| Cambio | Alcance razonable |
|---|---|
| Cambiar un texto o la apariencia | Su plantilla, vista o CSS. No debería exigir tocar SQL ni reglas del dominio. |
| Cambiar la fórmula de un plazo | La regla del dominio y sus pruebas. Revisar la representación SQL únicamente si también calcula esa regla. |
| Cambiar a quién bloquea una sanción grupal | Una regla/consulta con propietario explícito, sus consumidores estables y las pruebas del préstamo y reserva. Hoy hay dos búsquedas SQL que deben sincronizarse. |
| Añadir un campo persistido que el usuario edita | SQL, lectura/escritura, entidad o contrato de datos, formulario y pruebas: afectar varias capas es esperable porque cambia el contrato completo. |
| Añadir un tipo institucional de persona | Reglas, persistencia y presentación deben reconocerlo. Lo importante es tener una lista clara de puntos de extensión y evitar listas incompatibles. |

El objetivo es limitar los cambios accidentales y hacer explícitos los necesarios. Reducir el número de archivos por sí solo no garantiza menor complejidad.

## Orden recomendado de corrección

### 1. Recuperar una base verificable

Corregir A01, sincronizar A02 y separar la prueba de importación del esquema de la preparación con datos. Mantener los dos SQL, sin introducir migraciones. Reejecutar las 49 pruebas y revisar cualquier error nuevo antes de reorganizar archivos.

**Terminado cuando:** ambos SQL importan de cero y no queda una ejecución de integración parcialmente bloqueada por los datos iniciales.

### 2. Cerrar las reglas y su trazabilidad

Resolver A03 y A06: solicitante de ampliación derivado del préstamo, significado del actor que registra, alcance de las incidencias de daño/pérdida y estado real de las ampliaciones. Las sanciones grupales afectan al responsable y a los integrantes; el cupo y la política de préstamo hoy se calculan con el responsable ([repositorio_prestamo_sql.py:114](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/repositorio/repositorio_prestamo_sql.py:114) y [repositorio_prestamo_sql.py:702](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/repositorio/repositorio_prestamo_sql.py:702)). Confirmar si esa diferencia de alcance es la regla deseada; no cambiarla por suposición.

**Terminado cuando:** una tabla de reglas distingue lo implementado de lo pendiente, y código, SQL y diagramas reflejan las mismas decisiones.

### 3. Reducir el costo de los siguientes cambios

Abordar A04 y A05 una operación a la vez, preservando las transacciones. Después unificar el tratamiento de errores y las convenciones de entrada/presentación de A07 y A09. Evitar renombrar toda la aplicación a la vez, añadir una arquitectura distribuida o crear interfaces sin consumidores reales.

**Terminado cuando:** entrega directa y entrega de reserva usan un contrato conocido, una regla compartida tiene un propietario identificable, y las pruebas de regresión siguen cubriendo devolución, grupos, sanciones e inventario.

## Partes que conviene conservar

Las interfaces de repositorio tienen implementaciones e inyección reales; no son solo nombres en el gráfico. El dominio evita dependencias de Flask y MySQL. Existen reglas de transición y objetos de entrada. El contexto de conexión confirma o revierte las escrituras, y las entregas/devoluciones utilizan bloqueos. El acceso comprueba permisos y vigencia en cada petición; existen pruebas de protección del último administrador. Las consultas de préstamos calculan el estado sin escribir durante la lectura, y el reporte consulta integrantes aparte para no multiplicar los bienes.

Estas piezas permiten corregir por etapas. La auditoría no propone reconstruir el sistema completo ni eliminar las capas.

## Estado al entregar esta auditoría

Los hallazgos están documentados y reproducidos donde se indica. No se aplicaron correcciones a la aplicación ni se hicieron commits. Las modificaciones que ya existían al comenzar la revisión permanecen intactas. La siguiente intervención debe empezar por los SQL y por recuperar la ejecución completa de las pruebas; los cambios de carpetas vienen después de aclarar las responsabilidades.

## Seguimiento posterior: sincronización de los SQL

El 12 de noviembre de 2026 se corrigió `datos_prueba.sql` por indicación del usuario, tomando `schema.sql` como autoridad. Se modificaron únicamente las cuatro definiciones divergentes: `bien_material`, `detalle_prestamo`, `reserva` y `ampliacion_prestamo`. `schema.sql`, los datos insertados y las consultas de control se conservaron. Los hallazgos **A01 y A02 quedan resueltos** para estos archivos.

Se añadió [test_estructura_sql.py](D:/TI_sistema_recursos/SistemaRecursos_local/SistemaRecursos/tests/test_estructura_sql.py), independiente de los datos de preparación de las otras clases. Sus dos comprobaciones pasan: igualdad de las 20 definiciones, e importación de ambos SQL en bases nuevas de MySQL, con estructura vacía en el primero y personas y cuentas en el segundo.

La repetición de la suite existente permitió superar el error 3823 y encontró otro bloqueo de preparación: sus cargadores usan cursores sin consumir los resultados de las consultas de control al final del SQL. Esa ejecución informó `Ran 36 tests` y `FAILED (errors=63)`, incluyendo errores repetidos de limpieza derivados del mismo problema. No equivale a 63 defectos de aplicación. No se modificaron esos cargadores ni los escenarios de demostración en esta intervención; la ejecución funcional completa sigue pendiente de resolver ese problema de las pruebas, relacionado con A08.

## Seguimiento posterior: flujo de ampliaciones

Se implementó el recorrido de solicitud, aprobación y rechazo de ampliaciones, por detalle del préstamo. El usuario confirmó que el responsable solicita y que cada ampliación puede añadir como máximo otro plazo de la política. La entidad ya implementa las transiciones; existe un contrato de repositorio y sus capas de servicio, persistencia y controlador, con una sección en la vista del préstamo.

Se eliminó `dni_solicitante` de la clase, de los dos SQL y de los datos de demostración. Se obtiene al responsable desde el préstamo. La resolución registra cuenta del encargado, fecha y observación; aprobar actualiza la fecha del detalle en la misma transacción. Se revalidan propiedad, permisos, plazo actual, política y estado del bien. Una solicitud pendiente bloquea otra para ese mismo detalle.

Las 13 pruebas nuevas de ampliaciones pasan con MySQL temporal, incluidas las de propiedad en préstamos grupales, permisos revocados, CSRF, máximo por política, cierre de atención, solicitudes duplicadas, rechazo, resolución repetida, devolución/pérdida y rollback si falla el historial. La parte de ampliaciones de A03 y A06 queda resuelta; los hallazgos sobre tipos de incidencia, daño y pérdida siguen pendientes. No se modificaron sus reglas de sanción en esta intervención.

## Seguimiento posterior: coordinación de préstamos y ampliaciones

Se separó la coordinación de las escrituras de su persistencia. `ServicioAplicacionPrestamo` coordina entrega, devolución, pérdida y registro de vencimientos. `ContextoEntrega` reúne datos de elegibilidad, cupo, inventario, política y horario y evalúa las reglas sin MySQL. `Prestamo` valida la recepción y la pérdida. `ServicioAplicacionAmpliacionPrestamo` comprueba la autorización y coordina la solicitud y resolución; la entidad conserva las reglas y transiciones.

Los repositorios abren una transacción y crean una operación SQL privada para esa ejecución. Las interfaces `IOperacionPrestamo`, `IOperacionAmpliacionPrestamo` e `IOperacionEntregaReserva` permiten cargar y guardar sin exponer cursores al servicio. Los adaptadores mantienen SQL, bloqueos, mapeo y comprobaciones de concurrencia. La entrega de reserva reutiliza el servicio de préstamos y ambos adaptadores comparten el mismo cursor y confirmación. Se eliminó la dependencia del repositorio de reservas hacia la clase concreta `RepositorioPrestamoSQL`.

Se cubren reglas sin base de datos, confirmación y reversión del conjunto, aprobación desactualizada y dos entregas concurrentes del mismo bien. La devolución tardía conserva el alcance de la sanción para todo el grupo; un fallo al cerrar debe revertir también incidencia, sanción e inventario. Se reutiliza una preparación mínima de pruebas independiente de los datos de demostración.

El alcance es préstamos, ampliaciones y entrega de reservas. El registro, preparación, cancelación y expiración de reservas, así como el procesador y el auxiliar SQL de sanciones, no se reorganizaron. Persisten reglas anteriores en esos recorridos. No se modificaron los dos SQL ni se considera reparada la preparación de las pruebas antiguas descrita en A08. El mapa inicial de esta auditoría documenta la versión revisada originalmente; para el recorrido actualizado se debe consultar la sección de escrituras del README.

Validación de esta intervención: pasan las 26 pruebas enfocadas en préstamos y ampliaciones, ejecutadas con MySQL temporal, y las 15 pruebas de acceso y protección de administradores. La prueba nueva de fallo durante una devolución tardía confirma que también se revierten su incidencia y sanción. Estos 41 resultados no sustituyen la ejecución de la suite histórica completa, que conserva el problema de preparación ya documentado.

## Seguimiento posterior: ampliación presencial y directa

El usuario precisó que pide más tiempo presencialmente y que el encargado o administrador modifica el plazo en ese momento. Esa decisión sustituye el flujo digital anterior de solicitud, aprobación y rechazo. El formulario recibe cantidad y unidad, muestra el vencimiento calculado y modifica directamente el detalle, conservando el máximo de otro plazo de la política y el horario de atención. Los usuarios consultan su nueva fecha y no acceden al formulario de ampliación.

Se eliminan la tabla de ampliaciones de ambos SQL (quedan 19 tablas), sus INSERT de solicitudes y el permiso de solicitud digital. Se retiran los contratos y el adaptador SQL exclusivos de ampliaciones: el servicio reutiliza la transacción y operación del préstamo. La clase de dominio queda como regla pura de ampliación directa. La nueva fecha y su historial se confirman o revierten juntos; una fecha anterior desactualizada impide duplicar el aumento al reenviar un formulario. No se ejecutaron cambios destructivos en bases instaladas ni se modificaron diagramas en esta intervención.

Validación: pasan 26 pruebas de préstamos y ampliaciones (13 de ampliación directa y 13 de coordinación), más las dos pruebas de estructura e importación de los SQL en bases vacías. Se verificaron los 117 archivos Python, las 12 plantillas HTML y la sintaxis del nuevo JavaScript. La suite histórica completa conserva la limitación de preparación descrita en A08.

## Seguimiento posterior: preparación de la suite completa (A08)

Las pruebas funcionales antiguas ya no cargan `datos_prueba.sql`: crean bases con nombres aleatorios a partir de `schema.sql` y preparan sus propios escenarios. `soporte_mysql.py` centraliza creación, consumo de todos los resultados SQL y limpieza; el soporte de préstamos lo reutiliza. Configuración prepara solo sus ajustes y una cola mínima; devoluciones y reportes usan dos préstamos definidos para esos casos. Personas y recursos dejan de compartir una base entre métodos, y la prueba de paginación crea expresamente suficientes personas. El procesador automático queda desactivado en las aplicaciones de prueba.

La importación de ambos SQL se mantiene exclusivamente en `test_estructura_sql.py`, independiente de los escenarios funcionales. Se actualizó el recuento a las 19 tablas actuales. La pantalla de edición de cuenta prepara explícitamente la cuenta necesaria para ese recorrido.

Se añadió `SistemaRecursos/verificar.py` y se documentó el comando en el README. Requiere `TEST_MYSQL_PORT` y devuelve un resultado incompleto si se omite cualquier prueba; no presenta una ejecución sin integración como verificación completa. No se modificaron tablas, datos de demostración, reglas de negocio ni diagramas durante esta corrección.

Resultado final: `python verificar.py`, ejecutado con MySQL 8.0.46 temporal en el puerto 13307, completó **76 pruebas en 117,811 segundos: OK, sin fallos, errores ni pruebas omitidas**. También se comprobó que la ausencia de `TEST_MYSQL_PORT` devuelve código 2 con una explicación. El hallazgo **A08 queda resuelto** para la preparación y ejecución de la suite actual; los otros hallazgos no se consideran resueltos por este resultado.

## Prueba local: desacoplar el login de la ficha de persona

En la rama `modificacion-de-archivos-login`, partiendo del commit local `1b24d49`, se sustituyó la construcción de la ficha completa en el repositorio de acceso por `IdentidadAcceso`, definida en el mismo archivo que `UsuarioSistema`. Guarda DNI, nombres, apellidos y estado. Se conservan los contratos y el recorrido de formulario, controlador, servicio y repositorio; no se añadieron archivos de producción ni se modificó SQL estructural.

La consulta principal pasó de cinco tablas a dos (`usuario_sistema` y `persona`); la carga de permisos sigue siendo una consulta independiente. El repositorio de acceso ya no utiliza `FabricaPersona`. La pantalla de reserva obtiene el tipo desde el servicio de personas al necesitarlo. Los formularios de cuenta y la navegación conservan el acceso a los datos básicos de identidad.

La adaptación afecta a seis archivos de producción y dos de pruebas, además de esta documentación. Se añadieron casos que impiden construir fichas durante login y recuperación de sesión, que separan la validación del correo de la autenticación y que verifican la carga del tipo al abrir una reserva. Se mantienen las comprobaciones de contraseñas, estados, CSRF, permisos y revocación de sesión por cambio de contraseña.

Verificación completa con MySQL temporal: **79 pruebas en 145,434 segundos, OK y sin omisiones**. El cambio queda local y sin commit para revisar la comparación con `1b24d49`. No demuestra una mejora de tiempos bajo carga: se comprobó la reducción de dependencias y la conservación de los comportamientos cubiertos por las pruebas.

## Seguimiento: organización de acceso y administración de cuentas

La prueba anterior se guardó en el commit local `05cd63e` antes de esta reorganización. `ServicioAplicacionAcceso` conserva únicamente autenticación, versión de credenciales y recuperación de sesión. Las consultas administrativas, creación, edición, contraseña y activación se trasladaron a `ServicioAplicacionCuenta`, en `servicio_cuenta.py`.

`usuario_sistema.py` agrupa los tipos de cuenta, `Credenciales`, los contratos y las reglas de protección del último administrador. Se eliminaron los archivos independientes `credenciales.py` e `i_repositorio_acceso.py`. El contrato de acceso exige tres operaciones; el de cuentas, seis. El adaptador SQL implementa ambos y conserva sus transacciones y consultas. El controlador de personas utiliza el servicio de cuentas; el de acceso y el control de sesión utilizan el servicio de acceso. El servicio de roles depende del contrato de cuentas.

El README contiene el recorrido de cada operación y una tabla de ubicación de cambios para explicar el código. Las pruebas en memoria implementan directamente el contrato de acceso de tres operaciones. No se modificaron las tablas ni las reglas de autenticación o protección de administradores.

Resultado de la reorganización: `python verificar.py` completó **79 pruebas en 145,824 segundos, OK y sin omisiones**, con MySQL temporal. Se comprobaron también la dirección de dependencias, las tres operaciones del contrato de acceso y las seis del contrato de cuentas. Se eliminaron dos archivos Python y se añadió uno: el balance es un archivo de producción menos. Esta reorganización queda sin commit, posterior al punto de comparación `05cd63e`.
