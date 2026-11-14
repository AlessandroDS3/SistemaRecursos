# Sistema de préstamos escolares

Aplicación web con Flask y MySQL para gestionar personas, usuarios, recursos, bienes, reservas, préstamos y devoluciones.

## Requisitos

- Python 3.10 o superior.
- MySQL 8 en ejecución.

## Preparar la base de datos

La carpeta `sql/` contiene dos archivos independientes:

| Archivo | Contenido | Base que crea |
| --- | --- | --- |
| `schema.sql` | Las 19 tablas, sus relaciones y restricciones, sin ningún registro. | `prestamos_escuela` |
| `datos_prueba.sql` | Las mismas 19 tablas, configuración inicial y datos de prueba, incluidos usuarios. | `prestamos_escuela_pruebas` |

Para probar la aplicación, abre `sql/datos_prueba.sql` en MySQL Workbench u otro cliente y ejecútalo sobre una base nueva. No necesitas ejecutar primero `schema.sql`.

Si solo quieres la estructura vacía, utiliza `sql/schema.sql`. No incluye usuarios, roles, permisos ni configuración inicial. Para conectarte a ella, cambia `DB_NAME` a `prestamos_escuela`.

Durante el desarrollo actualizamos estos dos archivos directamente. Para cargar una nueva versión de los datos de prueba, se recrea la base de desarrollo en lugar de aplicar migraciones.

## Iniciar la aplicación

Puedes iniciar con `run.ps1` o directamente con `app.py`. Primero, desde PowerShell, en la raíz del repositorio, entra en la carpeta de la aplicación y configura MySQL:

```powershell
cd .\SistemaRecursos
$env:DB_HOST = '127.0.0.1'
$env:DB_PORT = '3306'
$env:DB_USER = 'root'
$env:DB_PASSWORD = 'tu_contrasena_mysql'
$env:DB_NAME = 'prestamos_escuela_pruebas'
```

Reemplaza `tu_contrasena_mysql` por tu contraseña de MySQL. Ejecuta la opción que prefieras en esa misma ventana de PowerShell.

### Opción 1: con `run.ps1`

```powershell
.\run.ps1
```

El script crea el entorno virtual en `..\.venv` si falta e instala las dependencias automáticamente. No necesitas activar el entorno manualmente.

Opcionalmente, puedes guardar las variables de conexión en `config.local.ps1`, junto a `run.ps1`. El script carga ese archivo antes de iniciar; está excluido de Git para mantener las credenciales solo en tu computadora.

### Opción 2: directamente con `app.py`

Si todavía no preparaste el entorno, ejecuta:

```powershell
py -3 -m venv ..\.venv
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Luego inicia la aplicación:

```powershell
..\.venv\Scripts\python.exe app.py
```

`app.py` utiliza las variables de conexión definidas en esa ventana. Si ya activaste el entorno virtual, puedes usar `python app.py`.

Abre [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Usuarios de prueba

Estas cuentas se crean al importar `sql/datos_prueba.sql`:

| Usuario | Contraseña | Rol |
| --- | --- | --- |
| `admin` | `AdminPrueba2026!` | Administrador |
| `encargado1`, `encargado2` | `EncargadoPrueba2026!` | Encargado de préstamos |
| `usuario1` | `UsuarioPrueba2026!` | Usuario |
| `estudiante01` a `estudiante08` | `UsuarioPrueba2026!` | Usuario |

Son cuentas de demostración para pruebas locales. La contraseña de inicio de sesión es distinta de la contraseña de conexión a MySQL.

El sistema comprueba la contraseña, el estado de la cuenta y sus permisos. La sesión vence a las 8 horas y se descarta si cambia la contraseña o la cuenta deja de tener acceso. Cerrar sesión elimina la cookie del navegador; no hay revocación individual en el servidor ni límite de intentos de inicio de sesión.

## Organización del código

El login conserva el recorrido `vista_acceso.html → controlador_acceso.py → servicio_acceso.py → IRepositorioAcceso → repositorio_acceso_sql.py`. La cuenta contiene credenciales, estado, rol, permisos y una `IdentidadAcceso` (DNI, nombres, apellidos y estado), definida en `usuario_sistema.py`. Esa identidad no es la ficha completa de la persona.

La consulta principal de acceso une únicamente `usuario_sistema` y `persona`; los permisos se consultan aparte. No carga CUI, ciclo, matrícula, correo, teléfono ni datos de docente o administrativo, ni utiliza `FabricaPersona`. Las fichas completas siguen perteneciendo al módulo de personas. El formulario de reserva consulta su tipo de persona mediante `ServicioAplicacionPersona` al abrirse, en lugar de depender de datos académicos cargados durante el login.

- `app.py`: configura e inicia la aplicación.
- `dominio/`: entidades, validaciones y reglas del negocio.
- `servicios/`: coordina las operaciones del sistema.
- `repositorio/`: consulta y guarda los datos en MySQL.
- `presentacion/`: controladores, vistas y archivos de la interfaz.
- `sql/`: estructura de la base de datos y datos de prueba.

Los roles y el catálogo de permisos están definidos en el código. `usuario_sistema.rol` asigna el rol a cada cuenta y `rol_permiso` permite ajustar sus permisos desde la aplicación. El acceso de la cuenta se determina únicamente por `estado_cuenta`.

### Escrituras de préstamos y ampliaciones

El controlador recibe la petición y llama al servicio. El servicio abre una transacción mediante la interfaz del repositorio, carga los datos, consulta las reglas del dominio y solicita las escrituras. El repositorio SQL mantiene la conexión y los bloqueos hasta confirmar todo o revertirlo si ocurre un error. Los servicios y el dominio no reciben conexiones ni cursores de MySQL.

| Operación | Quién coordina | Dónde están las decisiones | Quién carga y guarda |
| --- | --- | --- | --- |
| Entregar un préstamo | `servicio_prestamo.py` | `contexto_entrega.py`, `solicitud_prestamo.py` y políticas | `OperacionPrestamoSQL` en `repositorio_prestamo_sql.py` |
| Recibir una devolución, reportar pérdida y registrar vencimientos | `servicio_prestamo.py` | `prestamo.py`, `devolucion.py` y la condición de retraso en el servicio | La misma operación SQL del préstamo |
| Ampliar directamente un plazo | `servicio_ampliacion_prestamo.py` | Autorización en el servicio; duración, plazo vigente y horario en `ampliacion_prestamo.py` | `OperacionPrestamoSQL` en `repositorio_prestamo_sql.py` |
| Entregar una reserva | `servicio_reserva.py`, reutilizando el servicio de préstamos | `reserva.py` y las mismas reglas de entrega | `OperacionEntregaReservaSQL`, que comparte la transacción con la operación del préstamo |

Los contratos `i_operacion_prestamo.py` e `i_operacion_reserva.py` describen lo que cada servicio puede cargar y guardar durante esa transacción. Cada ejecución obtiene su propia operación. La entrega de reserva no abre una segunda conexión para registrar el préstamo.

Para probar estos recorridos: `python -m unittest discover -s tests -p "test_*prestamo*.py" -v`. Las pruebas puras funcionan sin MySQL. Las de integración necesitan las variables `TEST_MYSQL_*` y crean bases temporales propias. Otros recorridos de reservas y el procesador de sanciones conservan su implementación anterior.

Las relaciones con categorías y recursos se identifican como `id_categoria` e `id_recurso`. Las descripciones de recursos y bienes y la fecha de adquisición son opcionales; si se dejan vacías se guardan como `NULL`. Los estados de préstamo y reserva se actualizan junto con sus operaciones en la misma transacción.

Cada fila de `detalle_prestamo` guarda la entrega y su devolución. Una fecha de devolución vacía indica que el bien sigue pendiente; al recibirlo se guardan juntos la fecha, el encargado, la condición (`BUENO` o `DANADO`) y las observaciones. Un bien perdido sigue pendiente. La tabla separada `devolucion` se eliminó.

Los cambios de estado de préstamos, bienes, reservas y sanciones se guardan en `historial_estado`. Los campos `entidad` e `id_entidad` identifican a qué registro corresponde cada cambio.

Cada sanción se relaciona con una incidencia, y esta con el detalle del préstamo. La incidencia distingue `RETRASO`, `DANIO` y `PERDIDA`, y permite registrar el DNI de quien la comunica; los retrasos automáticos dejan ese DNI vacío. Solo puede existir una incidencia de retraso por detalle y una sanción por incidencia. Las sanciones siguen activas hasta su levantamiento manual con justificación.

La sanción se obtiene a través de `sancion → incidencia → detalle_prestamo → prestamo`. En préstamos individuales afecta al solicitante; en préstamos grupales afecta al responsable y a todos los integrantes de `participante_prestamo`. No se guarda otro DNI de la persona sancionada en `sancion`. Una misma sanción bloquea nuevos préstamos y reservas para todos los afectados hasta que se levanta. El DNI de quien registra la incidencia y el de quien levanta la sanción identifican a quienes realizan esas operaciones.

## Ampliaciones

El usuario pide la ampliación presencialmente. El encargado o administrador con `PRESTAMOS_GESTIONAR` abre el préstamo y, en **Ampliar plazo**, selecciona el bien e introduce una cantidad de horas o días. El formulario muestra el nuevo vencimiento en Lima. Al confirmar, el cambio se aplica inmediatamente; el usuario puede consultar su nueva fecha.

Se actualiza `detalle_prestamo.fecha_limite_devolucion`. Cada ampliación añade como máximo otro plazo de la política aplicada al bien; los préstamos por horas respetan el cierre de atención. Un bien vencido, perdido o devuelto no puede ampliarse. Si otro encargado ya cambió el plazo, el formulario antiguo se rechaza y exige recargar el préstamo, evitando sumar dos veces al reenviar.

La fecha anterior, la nueva, el detalle, el encargado y una observación opcional se guardan en `historial_estado` dentro de la misma transacción. Un fallo al guardar el historial revierte la nueva fecha.

Se eliminó la tabla `ampliacion_prestamo`, el permiso `AMPLIACIONES_SOLICITAR` y las rutas de solicitud, aprobación y rechazo. Los dos SQL crean ahora 19 tablas. Se actualizaron los archivos para instalaciones nuevas; no se borró ninguna tabla de una base ya instalada. Una base anterior puede conservar esa tabla sin que la aplicación la consulte. Como el resto de cambios estructurales de esta etapa, una instalación limpia se prepara recreando la base de pruebas.

Recorrido: `controlador_ampliacion_prestamo.py → servicio_ampliacion_prestamo.py → IRepositorioPrestamo / IOperacionPrestamo → repositorio_prestamo_sql.py`. `dominio/gestion_prestamos/ampliacion_prestamo.py` contiene únicamente la regla de cálculo y validación, sin representar una tabla.

Pruebas: `python -m unittest discover -s tests -p test_ampliacion_prestamo.py -v`. Las de integración requieren `TEST_MYSQL_PORT`, `TEST_MYSQL_USER` y `TEST_MYSQL_PASSWORD`; crean y eliminan bases temporales propias. Sin MySQL se ejecutan solo las comprobaciones del dominio.

## Reportes

El módulo **Reportes** permite consultar préstamos y devoluciones por fecha de entrega, estado del préstamo, tipo de solicitante, modalidad y búsqueda por persona o bien. Las fechas se interpretan en horario de Lima e incluyen ambos días. El tipo de persona corresponde al solicitante principal; la búsqueda también encuentra integrantes de préstamos grupales.

El resumen cuenta préstamos distintos y bienes sin duplicarlos por cada integrante. Presenta devueltos, pendientes y vencidos; los vencidos son parte de los pendientes. Los resultados muestran hasta 50 bienes por página y la descarga CSV incluye todas las coincidencias de los filtros, con fechas en Lima, separador `;` y codificación UTF-8. Al importar el CSV en Excel, selecciona formato texto para los DNI si necesitas conservar los ceros iniciales. Los campos de texto que podrían interpretarse como fórmulas se exportan como texto.

Se requiere el permiso `REPORTES_CONSULTAR`, incluido para Administrador y Encargado de préstamos en los datos de prueba. En una base ya instalada, un administrador puede habilitarlo desde **Roles y permisos** sin recrear las tablas. No se crean tablas de reportes ni se modifican los préstamos al consultarlos o descargarlos.

## Verificar toda la aplicación

Desde esta carpeta y con el entorno virtual activado, configura la conexión a un MySQL local de pruebas y ejecuta:

```powershell
$env:TEST_MYSQL_PORT = '3306'
$env:TEST_MYSQL_USER = 'root'
$env:TEST_MYSQL_PASSWORD = Read-Host 'Contraseña de MySQL de pruebas'
python verificar.py
```

Cambia el puerto si usas una instancia independiente. La cuenta necesita permisos para crear y eliminar bases de pruebas. Las pruebas usan nombres aleatorios con prefijo `test_`; no cargan ni modifican `prestamos_escuela` o `prestamos_escuela_pruebas`. El proceso crea los escenarios a partir de `schema.sql` y los limpia al terminar, incluso si una comprobación falla. Los datos de demostración solo se cargan en su prueba de importación independiente.

`verificar.py` devuelve éxito únicamente si se ejecutan todas las pruebas sin errores ni omisiones. Si falta `TEST_MYSQL_PORT`, termina con un mensaje y código 2; si alguna prueba falla o se omite, termina con código distinto de cero. El procesador automático de vencimientos está desactivado durante las pruebas.

También puedes ejecutar `python -m unittest discover -s tests -v` para trabajar en casos concretos, pero sin las variables de MySQL se omiten las pruebas de integración: ese resultado no equivale a verificar toda la aplicación.
