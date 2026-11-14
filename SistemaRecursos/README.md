# Sistema de préstamos de recursos

Aplicación local reescrita en Python, Flask y MySQL. El código se organiza por casos de uso y capas, con nombres que permiten seguir una función desde su formulario hasta la base de datos.

## Preparación y arranque

Requisitos: Python 3.10 o superior y MySQL 8. Desde esta carpeta, crea un entorno propio si todavía no existe:

```powershell
py -3 -m venv ..\.venv
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Para trabajar con una base separada, genera una copia local del SQL de demostración:

```powershell
New-Item -ItemType Directory -Force datos_locales | Out-Null
(Get-Content sql/datos_prueba.sql -Raw -Encoding UTF8).Replace('prestamos_escuela_pruebas', 'prestamos_escuela_rehecho') |
    Set-Content datos_locales/base_rehecha.sql -Encoding UTF8
```

Ejecuta `datos_locales/base_rehecha.sql` en MySQL Workbench. `sql/schema.sql` contiene únicamente las tablas; `sql/datos_prueba.sql` contiene las mismas tablas y datos de demostración. Sus definiciones se conservan respecto al proyecto anterior.

Configura la conexión y ejecuta:

```powershell
$env:DB_HOST = '127.0.0.1'
$env:DB_PORT = '3306'
$env:DB_USER = 'root'
$env:DB_PASSWORD = Read-Host 'Contraseña de MySQL'
$env:DB_NAME = 'prestamos_escuela_rehecho'
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
