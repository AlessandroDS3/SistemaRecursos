# Sistema de préstamos de recursos

Aplicación local reescrita en Python, Flask y MySQL. El código se organiza por casos de uso y capas, con nombres que permiten seguir una función desde su formulario hasta la base de datos.

## Preparación y arranque

Requisitos: Python 3.10 o superior y MySQL 8. Desde esta carpeta, crea un entorno propio si todavía no existe:

```powershell
py -3 -m venv ..\.venv
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

La base de esta copia es **`prestamos_escuela_pruebas`**, utilizada de forma predeterminada por `run.ps1` y `repositorio/conexion_mysql.py`. Si ya está cargada, no hace falta volver a importar datos. Para preparar una instalación nueva, ejecuta `sql/datos_prueba.sql` en MySQL Workbench: crea esa base con las tablas y los datos de demostración. `sql/schema.sql` conserva el esquema sin registros con el nombre `prestamos_escuela`; las pruebas lo importan bajo nombres temporales.

Configura la conexión y ejecuta:

```powershell
$env:DB_HOST = '127.0.0.1'
$env:DB_PORT = '3306'
$env:DB_USER = 'root'
$env:DB_PASSWORD = Read-Host 'Contraseña de MySQL'
$env:DB_NAME = 'prestamos_escuela_pruebas'
..\.venv\Scripts\python.exe app.py
```

Abre **http://127.0.0.1:5001**. `PORT` permite cambiar el puerto.

`run.ps1` crea el entorno e instala los requisitos cuando hace falta. Puede cargar las variables desde `config.local.ps1`, ignorado por Git. En Linux: `python3 -m venv ../.venv`, `../.venv/bin/python -m pip install -r requirements.txt` y `../.venv/bin/python app.py`, definiendo las mismas variables mediante `export`.

La clave de firma se toma de `FLASK_SECRET_KEY`. En desarrollo, si no se define, se conserva en `datos_locales/clave_sesion.txt` entre reinicios. El entorno virtual y los archivos locales quedan fuera del repositorio.

## Usuarios de demostración

| Usuario | Contraseña | Rol |
| --- | --- | --- |
| `admin` | `AdminPrueba2026!` | Administrador |
| `encargado1`, `encargado2` | `EncargadoPrueba2026!` | Encargado de préstamos |
| `usuario1`, `estudiante01` a `estudiante08` | `UsuarioPrueba2026!` | Usuario |

Son cuentas de `datos_prueba.sql`; sus contraseñas son distintas de la contraseña de conexión a MySQL.

## Organización

```text
app.py                         Conecta servicios, repositorios y controladores
dominio/
  gestion_personas_usuarios/    acceso, cuenta, persona, rol
  gestion_recursos/             recurso, bien_material
  gestion_prestamos/            prestamo, devolucion, reserva, ampliacion_prestamo
  gestion_control/              politica_prestamo, incidencia, sancion, reporte
  compartido/                   validacion, contratos transaccionales
servicios/                      Un servicio por caso de uso
repositorio/                    Un repositorio SQL por caso de uso
presentacion/
  controladores/                HTTP y conversión de formularios
  vistas/                       Plantillas HTML por función
  static/                       Estilos y comportamiento visual
  seguridad.py                  Sesión web, CSRF y permisos de rutas
sql/                            schema.sql y datos_prueba.sql
tests/                          Reglas, servicios, HTTP, MySQL y arquitectura
```

El dominio define los datos, las reglas y los contratos `IRepositorio...` que necesitan los servicios. Se utilizan `Protocol`: los adaptadores SQL cumplen esos métodos sin añadir clases intermedias que solo deleguen llamadas.

Los servicios coordinan los casos de uso. El repositorio controla la conexión, las consultas, los bloqueos y la escritura. Presentación recibe HTTP, llama al servicio y muestra su resultado. El dominio no importa Flask, MySQL, servicios ni repositorios concretos; los servicios tampoco importan presentación o persistencia.

En personas y cuentas, los controladores consultan los datos del formulario al mostrarlo mediante GET; los POST pasan directamente al servicio. `validar_nombre_usuario` y `validar_clave` validan sus valores por separado. El servicio de cuentas prepara los cambios antes de abrir la transacción y comparte la escritura protegida con la asignación de roles. Los catálogos de estados de persona, matrícula y cuenta se definen en el dominio y se pasan a las plantillas. Los códigos de docente y empleado tienen el mismo máximo de 20 caracteres en dominio y formulario.

Al editar una persona, una lectura inicial validada por su versión determina si cambia el estado o el DNI. Esos cambios mantienen el orden de bloqueo cuentas → persona para proteger a los administradores y las relaciones del DNI. Los cambios de nombre, correo, teléfono y otros datos de la ficha no bloquean el conjunto de cuentas. Dentro de la transacción se vuelve a leer la ficha con bloqueo y a comprobar la versión: si otra operación la modificó, se rechaza el guardado. La desactivación reutiliza este recorrido; no hay una escritura SQL alternativa que omita sus reglas.

En recursos e inventario, el servicio prepara los grupos y contadores de administración. Catálogo, inventario y administración buscan por nombre, marca, modelo o código de inventario y comparten la validación de filtros. El catálogo usa `EXISTS` para no duplicar recursos; al combinar inventario y estado, ambos deben corresponder al mismo bien. Los recursos sin bienes se conservan cuando cumplen los filtros.

Las ediciones de categorías, recursos y bienes exigen la versión enviada por el formulario y la comparan con la fila bloqueada. La versión descriptiva del bien excluye su estado; los campos omitidos se conservan y los opcionales enviados vacíos se limpian. El registro individual y el primer bien de un recurso utilizan `BienMaterial.desde_datos`, conservando la transacción conjunta. Las eliminaciones verifican existencia y relaciones y explican el impedimento; un bien con préstamos, reservas o historial no se elimina. Se mantienen las restricciones SQL sin cambios de esquema.

La presentación recupera la identidad institucional de la versión anterior: login con logo e ilustración junto al formulario, opción para mostrar contraseña y menú lateral granate en las pantallas internas. `base.html` comparte la estructura del sistema; `estilos.css` adapta tarjetas, tablas y formularios, y `aplicacion.js` controla el menú móvil. La lógica simplificada de servicios y dominio se conserva. En móvil, las dos columnas del login se apilan y el menú se abre desde el encabezado.

Tras iniciar sesión se muestra `inicio.html`, con las acciones disponibles según los permisos. El menú conserva el orden anterior: Inicio, Personas, Roles y permisos, Catálogo de recursos, Administrar recursos, Préstamos, Solicitudes y reservas, Políticas de préstamo y Reportes; Sanciones se mantiene al final para el personal autorizado. Registrar recursos, bienes y categorías se agrupa en Administrar recursos. Los usuarios ven Mis préstamos y Mis solicitudes y reservas.

Los estados de reserva, los estados pendientes y los estados admitidos por cada acción se definen en `dominio/gestion_prestamos/reserva.py`. El controlador los comparte con la plantilla y el repositorio utiliza sus valores como parámetros SQL. Añadir un estado también requiere actualizar el `ENUM` del esquema y migrar las bases existentes.

Los contratos `NuevaReserva`, `Reserva`, `DetalleReserva`, `ContextoReserva` y `CambiosReserva` describen los diccionarios del recorrido de reservas mediante `TypedDict`. No cambian los datos en ejecución; permiten comprobar sus claves y valores opcionales con mypy. El servicio separa preparación, entrega y cierre en métodos privados y conserva la transacción, los permisos y el historial en `_resolver_reserva`.

## Convención de nombres

Las operaciones públicas usan **verbo + entidad**, con el mismo vocabulario en controladores, servicios y contratos/repositorios:

| Acción | Convención | Ejemplo |
| --- | --- | --- |
| Obtener un registro | `consultar_<entidad>` | `consultar_cuenta` |
| Obtener un conjunto | `consultar_<plural>` | `consultar_personas` |
| Buscar por texto | `buscar_<plural>` | `buscar_cuentas` |
| Crear un registro | `registrar_<entidad>` | `registrar_cuenta` |
| Modificar un registro existente | `actualizar_<entidad>` | `actualizar_cuenta` |
| Registrar o actualizar según el identificador | `guardar_<entidad>` | `guardar_recurso` |
| Eliminar un registro | `eliminar_<entidad>` | `eliminar_recurso` |
| Operación propia del negocio | Verbo específico y entidad | `preparar_reserva`, `entregar_reserva`, `levantar_sancion` |
| Formulario que atiende consulta y envío | `gestionar_formulario_<entidad>` | `gestionar_formulario_persona` |

El acceso utiliza `autenticar_cuenta` y `consultar_cuenta_activa`. Las reservas exponen `preparar_reserva`, `entregar_reserva`, `cancelar_reserva`, `rechazar_reserva` y `expirar_reserva`; comparten un coordinador privado `_resolver_reserva`. Los identificadores de rutas utilizados desde las plantillas también indican la operación, por ejemplo `cuentas.registrar_cuenta`.

Los nombres técnicos compartidos (`transaccion`, `consultar_sql`, `__init__`) y las propiedades de los modelos conservan su significado técnico. Las pruebas de arquitectura impiden reintroducir operaciones públicas genéricas como `crear`, `guardar` o `actuar`.

## Recorridos por nombre

En cada fila, se utiliza el mismo nombre en los archivos `controlador_<nombre>.py`, `servicio_<nombre>.py` y `repositorio_<nombre>_sql.py`.

| Nombre | Archivo del dominio | Operaciones principales del servicio |
| --- | --- | --- |
| `acceso` | `gestion_personas_usuarios/acceso.py` | `autenticar_cuenta`, `consultar_cuenta_activa` |
| `cuenta` | `gestion_personas_usuarios/cuenta.py` | `consultar_cuenta`, `registrar_cuenta`, `actualizar_cuenta`, `asignar_rol_cuenta`, `buscar_cuentas` |
| `persona` | `gestion_personas_usuarios/persona.py` | `consultar_personas`, `consultar_persona`, `guardar_persona`, `desactivar_persona`, `buscar_personas` |
| `rol` | `gestion_personas_usuarios/rol.py` | `consultar_matriz_permisos`, `guardar_matriz_permisos` |
| `recurso` | `gestion_recursos/recurso.py` | `consultar_recursos`, `consultar_recurso`, `guardar_recurso`, `eliminar_recurso`, `consultar_categorias`, `guardar_categoria`, `eliminar_categoria` |
| `bien_material` | `gestion_recursos/bien_material.py` | `consultar_bien_material`, `consultar_bienes_materiales`, `guardar_bien_material`, `cambiar_estado_bien_material`, `consultar_historial_bien_material`, `eliminar_bien_material` |
| `politica_prestamo` | `gestion_control/politica_prestamo.py` | `consultar_politica_prestamo`, `consultar_politicas_prestamo`, `consultar_configuracion_general`, `consultar_limites_articulos`, `guardar_politica_prestamo`, `guardar_configuracion_general`, `guardar_limite_articulos`, `eliminar_politica_prestamo` |
| `prestamo` | `gestion_prestamos/prestamo.py` | `consultar_condiciones_prestamo`, `consultar_prestamos`, `consultar_prestamo`, `registrar_prestamo`, `registrar_prestamo_en_operacion`, `registrar_devolucion`, `registrar_perdida_bien_material`, `registrar_vencimientos_prestamos` |
| `ampliacion_prestamo` | `gestion_prestamos/ampliacion_prestamo.py` | `ampliar_prestamo` |
| `reserva` | `gestion_prestamos/reserva.py` | `consultar_recursos_para_reserva`, `consultar_reservas`, `consultar_reserva`, `registrar_reserva`, `preparar_reserva`, `entregar_reserva`, `cancelar_reserva`, `rechazar_reserva`, `expirar_reserva`, `expirar_reservas_vencidas` |
| `sancion` | `gestion_control/sancion.py` | `registrar_sancion_por_retraso`, `aplicar_sanciones_por_vencimiento`, `consultar_sanciones`, `levantar_sancion` |
| `reporte` | `gestion_control/reporte.py` | `consultar_reportes`, `exportar_reportes_csv` |

Por ejemplo, para cambiar una regla de bienes:

```text
vista_bien_material.html
  → ControladorBienMaterial.cambiar_estado_bien_material
    → ServicioAplicacionBienMaterial.cambiar_estado_bien_material
      → bien_material.validar_cambio_estado
      → IRepositorioBienMaterial
        → RepositorioBienMaterialSQL.cambiar_estado_bien_material
```

Las devoluciones son una operación del préstamo: `ControladorPrestamo.registrar_devolucion` → `ServicioAplicacionPrestamo.registrar_devolucion` → reglas de `Devolucion` en `devolucion.py` → `RepositorioPrestamoSQL.registrar_devolucion`. El horario, los límites y los plazos de reserva se administran en Políticas y utilizan `servicio_politica_prestamo.py` y `repositorio_politica_prestamo_sql.py`.

## Reglas y transacciones

- **Acceso:** consulta una cuenta mínima y sus permisos. Cuenta y persona deben estar activas. Usa una cookie de sesión del navegador, sin temporizador propio de ocho horas. El cierre de sesión borra la sesión y el cambio de contraseña invalida las credenciales de las cookies anteriores. Cada petición vuelve a cargar permisos y estados. Los formularios de escritura usan CSRF.
- **Personas y cuentas:** los datos institucionales pertenecen a persona; contraseña y acceso pertenecen a cuenta. Las ediciones de persona y la matriz de permisos detectan formularios desactualizados. Se protege la propia cuenta y la existencia de un administrador activo.
- **Entrega:** el formulario consulta cupo, plazos y permiso de salida antes de confirmar. `SolicitudPrestamo.planificar` comprueba a los integrantes, sanciones, vencimientos, cupo total del responsable, inventario, política y horario. El repositorio carga esos hechos bajo bloqueo. Préstamo, detalles, integrantes, inventario e historial se confirman juntos.
- **Reservas:** la persona solicita un recurso; el personal prepara un ejemplar y confirma la entrega al recogerlo. Se comprueban solicitudes duplicadas, elegibilidad y turno. La posición se calcula al consultar. Entregar una reserva reutiliza `ServicioAplicacionPrestamo.registrar_prestamo_en_operacion` con la misma conexión y transacción.
- **Devolución y pérdida:** se pueden recibir bienes parcialmente. Un daño requiere observación. La pérdida deja el detalle pendiente y el inventario en `PERDIDO`; recuperarlo se registra como devolución `BUENO` o `DANADO`.
- **Ampliación:** la petición es presencial. El personal añade horas o días a un detalle pendiente y no vencido. Cada ampliación admite como máximo otro plazo de la política aplicada y respeta el cierre cuando corresponde. La fecha anterior evita aplicar dos veces un formulario. Se actualizan detalle e historial juntos.
- **Sanciones:** el retraso genera una incidencia y una sanción por detalle; afecta al responsable y a todos los integrantes. Una sanción levantada no se reactiva automáticamente. Daño y pérdida mantienen el registro de inventario e historial; no se añadieron reglas nuevas de sanción para esos casos.
- **Reportes:** consultas sin escrituras, filtros por fechas de Lima, estado, modalidad, persona, integrantes, recurso o inventario. Cada bien ocupa una fila aunque el préstamo sea grupal. La pantalla pagina de 50 en 50 y el CSV incluye todos los resultados, usa UTF-8 con BOM y protege las celdas que podrían interpretarse como fórmulas.

`RepositorioSQL.transaccion()` entrega una instancia de operación con un cursor propio. Los repositorios relacionados reutilizan ese cursor internamente. Los servicios no reciben conexiones ni cursores y no coordinan escrituras mediante conexiones independientes.

`procesador_vencimientos.py` ejecuta los servicios de sanciones y reservas cada 30 segundos. Se inicia al ejecutar `app.py`. Si se usa `create_app()` desde otro servidor, se habilita con `INICIAR_PROCESADOR_VENCIMIENTOS=True`; en las pruebas permanece desactivado. Las pantallas calculan el estado actual del préstamo y el botón de vencimientos permite dejar constancia en su historial.

El esquema conserva sus restricciones anteriores: la aplicación evita entregas pendientes duplicadas mediante bloqueos y comprobaciones dentro de la transacción, y comprueba que el bien de una reserva corresponda a su recurso. Esas dos reglas no tienen una restricción adicional en el SQL contra modificaciones directas externas.

## Qué cambió en esta reescritura

Se reemplazaron los módulos agrupados `personas.py`, `cuentas.py`, `recursos.py`, `prestamos.py`, `reservas.py`, `control.py` y `reportes.py` por archivos identificables por función. Las decisiones de entrega, devolución y ampliación se implementan como reglas que se pueden probar sin MySQL. También se reescribieron los servicios, adaptadores SQL, controladores y formularios, con una interfaz más sencilla.

Frente al commit de respaldo `438ec36`, el Python de producción pasó de **7133 a 4078 líneas**, incluyendo comentarios y líneas en blanco, y de **58 a 67 módulos**, contando los inicializadores vacíos de paquetes. Los nombres separados por función explican el aumento de módulos. Las cifras no incluyen pruebas, SQL, HTML, CSS, el entorno ni archivos locales. La comparación con el contenido actual de `SistemaRecursos_local` figura en [COMPARACION_COPIAS.md](../COMPARACION_COPIAS.md); utiliza esa otra base de comparación.

El esquema sigue teniendo 19 tablas. No se modificó el proyecto anterior ni se publicaron los cambios. Las pruebas de la API anterior quedan conservadas en el commit de respaldo; la suite actual comprueba los nuevos contratos y sus recorridos.

## Verificación y formato

Para ejecutar toda la suite, configura una cuenta MySQL de pruebas con permiso para crear y eliminar bases temporales:

```powershell
$env:TEST_MYSQL_PORT = '3306'
$env:TEST_MYSQL_USER = 'root'
$env:TEST_MYSQL_PASSWORD = Read-Host 'Contraseña de MySQL de pruebas'
..\.venv\Scripts\python.exe verificar.py
```

Se crean bases `test_*` y se eliminan al terminar. `verificar.py` falla si hay pruebas omitidas. Las unitarias de reglas y servicios se pueden ejecutar sin MySQL:

```powershell
..\.venv\Scripts\python.exe -m unittest discover -s tests -p test_dominio.py -v
..\.venv\Scripts\python.exe -m unittest discover -s tests -p test_servicios_sin_mysql.py -v
..\.venv\Scripts\python.exe -m unittest discover -s tests -p test_arquitectura.py -v
```

Las pruebas cubren transacciones y reversión ante fallos, entregas simultáneas del mismo bien, sanciones grupales, devolución parcial y recuperación de pérdidas, ampliaciones, reservas, ediciones concurrentes, acceso/CSRF, permisos actuales, formularios HTTP, filtros/CSV y la importación de ambos SQL. Las de arquitectura impiden ciclos y saltos entre las capas.

Verificación de esta reescritura: **77 pruebas correctas, sin omisiones, en 135,503 segundos**, sobre MySQL temporal en el puerto 13307. Los dos SQL son idénticos a los del proyecto anterior por comparación SHA-256. El registro local está en `datos_locales/reescritura_completa.log`.

Después se corrigió la validación de contraseñas en actualizaciones sin nombre de usuario. Se verificó con las **10 pruebas de personas y cuentas**, incluidas tres nuevas, en 21,812 segundos. Esta comprobación fue específica de la corrección; su registro está en `datos_locales/correccion_claves.log`.

Tras unificar los nombres de operaciones y de los identificadores utilizados por las plantillas, la suite completa terminó con **81 pruebas correctas, sin omisiones, en 140,158 segundos**. Incluye la corrección de contraseñas y una comprobación que impide nombres genéricos en las operaciones públicas de negocio. Registro: `datos_locales/nombres_uniformes_final.log`.

El formato opcional de desarrollo utiliza `requirements-dev.txt` y `pyproject.toml`: Black para Python y djLint para las plantillas. No son dependencias de ejecución de la aplicación.

Para comprobar los contratos de reservas, instala `requirements-dev.txt` y ejecuta desde esta carpeta:

```powershell
..\.venv\Scripts\python.exe -m mypy
```

La configuración de `pyproject.toml` limita por ahora el análisis al dominio, servicio y repositorio de reservas. Los demás módulos se pueden incorporar gradualmente.

Validación de estas mejoras de mantenibilidad (14/11/2026): **87 pruebas correctas, sin omisiones, en 105,078 segundos**, con MySQL aislado. Mypy terminó sin errores en los tres módulos configurados. Se conservaron las comprobaciones CSRF de `presentacion/seguridad.py` y se retiró la segunda validación de Flask-WTF, incompatible con los tokens propios de los formularios.

La reorganización de presentación toma como referencia la copia local anterior, conservada antes de este trabajo en el commit `25840a1`. Inicio muestra indicadores calculados con los permisos de la cuenta. `/recursos/administracion` reúne el registro de recursos, las categorías y el inventario por recurso. Personas incorpora filtros por tipo, estado y existencia de cuenta. Los préstamos tienen búsqueda de personas, selección de bienes y resumen antes de confirmar; las políticas se editan en una matriz por categoría y tipo de persona. El horario y los vencimientos comparten un único formulario de configuración.

`componentes.html` contiene los indicadores y estados compartidos; `fragmentos_recursos.html` reutiliza los formularios de recursos y categorías. Las pantallas conservan los servicios, las validaciones y las transacciones existentes. Validación de presentación (14/11/2026): **91 pruebas correctas, sin omisiones**, con MySQL aislado, y revisión en Chrome de escritorio y móvil, incluyendo la selección de persona/bienes y la configuración de políticas.

## Reportes disponibles

El commit `af9767d` conserva la presentación anterior a esta ampliación. `/reportes` ofrece un selector con ocho reportes. Al cambiar de reporte se reinician los filtros; al consultar, paginar o descargar CSV se conservan los filtros activos.

| Reporte | Fechas y filtros específicos | Contenido |
| --- | --- | --- |
| Préstamos | Fecha de entrega, estado del préstamo, modalidad y tipo de solicitante | Una fila por bien y su situación actual. Un préstamo vencido puede incluir bienes ya devueltos. |
| Devoluciones y cumplimiento | Fecha de devolución, puntualidad, estado del préstamo, modalidad y tipo de solicitante | Condición, cumplimiento y retraso de cada devolución; porcentaje puntual y retraso promedio de las tardías. |
| Bienes atrasados | Fecha límite, modalidad y tipo de solicitante | Exclusivamente bienes pendientes vencidos, integrantes del grupo y tiempo de retraso al consultar. |
| Inventario | Estado actual y ubicación; sin filtro de fechas | Bienes, categoría, marca, modelo, serie, ubicación y fecha de adquisición. |
| Uso de recursos | Fecha de entrega, modalidad y tipo de solicitante | Cantidades agrupadas por mes de Lima y recurso. El total de préstamos distintos no suma los grupos: un préstamo puede contener varios recursos. |
| Solicitudes y reservas | Fecha de solicitud, estado, tipo de gestión y tipo de solicitante | Solicitudes del período con su estado actual, recurso, retiro solicitado y vencimiento. |
| Sanciones | Fecha de sanción, estado, modalidad y tipo de solicitante | Motivo, responsable y grupo, bien y levantamiento. La fecha de una sanción automática corresponde al vencimiento que la originó. |
| Daños y pérdidas | Fecha del evento y tipo de evento | Historial de bienes dañados o perdidos, incluso si fueron recuperados; operador registrador y observación. El registrador no se presenta como causante del daño. |

Todos permiten filtrar por categoría y buscar texto. La búsqueda se adapta a los datos de cada reporte. Los intervalos incluyen ambos días en horario de Lima. Los estados de préstamo, reserva, sanción e inventario reflejan la situación actual; no reconstruyen un cierre histórico de inventario o de estados.

`dominio/gestion_control/catalogo_reportes.py` centraliza títulos, columnas de salida, filtros admitidos, estados e indicadores. `reporte.py` valida y normaliza los filtros. `repositorio_reporte_sql.py` comparte las condiciones y las consultas de movimientos, y mantiene una función por consulta específica. `servicio_reporte.py` reutiliza la misma consulta para pantalla y CSV. `vista_reporte.html` dibuja los filtros, indicadores y columnas definidos en el catálogo; el controlador reutiliza el servicio de recursos para consultar las categorías.

La consulta y la exportación requieren `REPORTES_CONSULTAR` y solo leen las tablas existentes. No se crean tablas ni se modifican operaciones de préstamos, reservas o sanciones. La pantalla pagina de 50 en 50; los indicadores abarcan todo el resultado filtrado y el CSV incluye todas sus páginas. El CSV conserva UTF-8 con BOM, separador `;`, fechas de Lima y protección contra fórmulas. Los campos de retraso se exportan en minutos y se muestran en pantalla como días, horas y minutos.

Validación de esta ampliación (15/11/2026): **104 pruebas correctas, sin omisiones, en 123,001 segundos**, sobre MySQL aislado. Incluye 13 pruebas nuevas de filtros, puntualidad en el límite exacto, atrasos, grupos, agregación mensual en Lima, paginación, exportación, permisos e historial de bienes recuperados. También se revisaron los ocho reportes y sus CSV en Chrome de escritorio y móvil.

## Revisión del aviso CSRF de SonarQube

La aplicación utiliza la protección CSRF de `presentacion/seguridad.py`, instalada por `configurar_seguridad` al crear la aplicación. Un `before_request` comprueba el token de la sesión en POST, PUT, PATCH y DELETE antes de ejecutar el controlador. El token se genera con `secrets.token_urlsafe(32)`, se renueva al iniciar sesión y se compara con `hmac.compare_digest`. Los formularios lo envían en `csrf_token`; no hay una configuración que desactive esta comprobación.

La prueba `test_csrf_rechaza_tokens_ausentes_anteriores_al_login_y_de_otra_sesion` comprueba que esos tokens se rechazan y que la persona permanece activa. Solo con el token vigente se permite la desactivación. Se conserva también la prueba de login sin CSRF.

S4502 es un aviso de revisión de seguridad. La [documentación de SonarQube sobre su revisión](https://docs.sonarsource.com/sonarqube-for-vs-code/using/security-hotspots) explica cómo registrar el resultado como Safe cuando existe una protección válida. Esta revisión está documentada aquí; el estado del aviso en SonarQube se gestiona por separado. No se silenció la regla ni se añadió una segunda validación CSRF.

Verificación después de corregir los literales repetidos y los constructores de diccionarios (15/11/2026): **105 pruebas correctas, sin omisiones, en 138,198 segundos**, con MySQL aislado. Incluye la nueva comprobación de CSRF entre sesiones y tras el inicio de sesión.

## Claridad del acceso y dependencias de permisos

`ControladorAcceso.iniciar_sesion` atiende el formulario y llama a `establecer_sesion(cuenta_acceso)` para guardar la identidad y renovar el token CSRF. El servicio utiliza el nombre `cuenta_acceso` para el objeto `CuentaAcceso`, selecciona el hash que se comprobará en un paso separado y devuelve explícitamente una cuenta activa o `None`. Al recuperar la sesión, presentación confía en esa garantía del servicio y comprueba la versión de credenciales sin repetir la validación de estados.

En las operaciones SQL se mantiene el diccionario `cuenta_actor`, que `exigir_permiso` valida y devuelve. Los nombres y las descripciones distinguen ambos datos sin añadir una representación nueva ni cambiar los contratos de los servicios.

`DEPENDENCIAS_PERMISOS`, en `dominio/gestion_personas_usuarios/rol.py`, define los permisos de consulta necesarios:

| Permiso que se concede | Permiso que debe estar marcado en el mismo rol |
| --- | --- |
| Gestionar personas | Consultar personas |
| Administrar cuentas | Consultar personas |
| Administrar roles y permisos | Consultar roles |
| Gestionar recursos y bienes | Consultar catálogo |

La pantalla de roles muestra estos requisitos a partir del mismo catálogo. Guardar una matriz incompleta devuelve un error antes de escribir en MySQL e indica el permiso que falta; no se conceden permisos automáticamente. Se conserva la obligación de que el administrador mantenga la consulta y gestión de roles.

Verificación de estos ajustes (15/11/2026): **109 pruebas correctas, sin omisiones, en 127,738 segundos**, con MySQL aislado. Las cuatro pruebas nuevas comprueban la recuperación de cuentas activas, las dependencias de consulta, el rechazo de matrices incompletas sin escrituras y la navegación y el guardado con permisos personalizados. Mypy continúa sin errores en los tres módulos de reservas configurados. También se comprobó, sin modificar datos, que la matriz actual de `prestamos_escuela_pruebas` cumple las dependencias y que sus pantallas de login y roles renderizan correctamente.
