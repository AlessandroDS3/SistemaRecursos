# Sistema de préstamos escolares

Aplicación web con Flask y MySQL para gestionar personas, usuarios, recursos, bienes, reservas, préstamos y devoluciones.

## Requisitos

- Python 3.10 o superior.
- MySQL 8 en ejecución.

## Preparar la base de datos

La carpeta `sql/` contiene dos archivos independientes:

| Archivo | Contenido | Base que crea |
| --- | --- | --- |
| `schema.sql` | Las 20 tablas, sus relaciones y restricciones, sin ningún registro. | `prestamos_escuela` |
| `datos_prueba.sql` | Las mismas 20 tablas, configuración inicial y datos de prueba, incluidos usuarios. | `prestamos_escuela_pruebas` |

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

- `app.py`: configura e inicia la aplicación.
- `dominio/`: entidades, validaciones y reglas del negocio.
- `servicios/`: coordina las operaciones del sistema.
- `repositorio/`: consulta y guarda los datos en MySQL.
- `presentacion/`: controladores, vistas y archivos de la interfaz.
- `sql/`: estructura de la base de datos y datos de prueba.

Los roles y el catálogo de permisos están definidos en el código. `usuario_sistema.rol` asigna el rol a cada cuenta y `rol_permiso` permite ajustar sus permisos desde la aplicación. El acceso de la cuenta se determina únicamente por `estado_cuenta`.

Las relaciones con categorías y recursos se identifican como `id_categoria` e `id_recurso`. Las descripciones de recursos y bienes y la fecha de adquisición son opcionales; si se dejan vacías se guardan como `NULL`. Los estados de préstamo y reserva se actualizan junto con sus operaciones en la misma transacción.

Cada fila de `detalle_prestamo` guarda la entrega y su devolución. Una fecha de devolución vacía indica que el bien sigue pendiente; al recibirlo se guardan juntos la fecha, el encargado, la condición (`BUENO` o `DANADO`) y las observaciones. Un bien perdido sigue pendiente. La tabla separada `devolucion` se eliminó.

Los cambios de estado de préstamos, bienes, reservas y sanciones se guardan en `historial_estado`. Los campos `entidad` e `id_entidad` identifican a qué registro corresponde cada cambio.

Cada sanción se relaciona con una incidencia, y esta con el detalle del préstamo. La incidencia distingue `RETRASO`, `DANIO` y `PERDIDA`, y permite registrar el DNI de quien la comunica; los retrasos automáticos dejan ese DNI vacío. Solo puede existir una incidencia de retraso por detalle y una sanción por incidencia. Las sanciones siguen activas hasta su levantamiento manual con justificación.

La sanción se obtiene a través de `sancion → incidencia → detalle_prestamo → prestamo`. En préstamos individuales afecta al solicitante; en préstamos grupales afecta al responsable y a todos los integrantes de `participante_prestamo`. No se guarda otro DNI de la persona sancionada en `sancion`. Una misma sanción bloquea nuevos préstamos y reservas para todos los afectados hasta que se levanta. El DNI de quien registra la incidencia y el de quien levanta la sanción identifican a quienes realizan esas operaciones.

## Ampliaciones

Desde el detalle del préstamo, su responsable puede solicitar una nueva fecha para cada bien pendiente. Los demás integrantes del grupo pueden consultar las solicitudes. El encargado o administrador con `PRESTAMOS_GESTIONAR` puede aprobarlas o rechazarlas; el rechazo exige un motivo.

La solicitud no cambia la fecha de devolución. Al aprobar, la nueva fecha y la resolución se guardan juntas, con la cuenta del encargado, la fecha y la observación. El historial del préstamo registra la solicitud y su resolución. Solo puede haber una solicitud pendiente por bien; una ampliación resuelta no se vuelve a resolver.

Cada ampliación puede añadir como máximo otro plazo de la política aplicada al bien. En préstamos por horas se respeta también el cierre de atención. Se vuelve a comprobar el plazo al aprobar: un bien devuelto, perdido, vencido o cuya fecha ya cambió no admite la aprobación de una solicitud antigua. Se puede rechazar una solicitud que haya quedado desactualizada.

El solicitante se obtiene por `ampliacion_prestamo → detalle_prestamo → prestamo`; ya no existe `dni_solicitante` en la ampliación. La resolución identifica al encargado mediante `id_usuario_resolucion`. Los dos SQL contienen la misma estructura actualizada; esta versión se carga en una base nueva o recreando la base de pruebas.

El permiso `AMPLIACIONES_SOLICITAR` se incluye para los tres roles en los datos de demostración. Si se administra una matriz de permisos distinta, debe habilitarse desde Roles y permisos para que el responsable pueda solicitar ampliaciones.

El recorrido de escritura está identificado en `controlador_ampliacion_prestamo.py → servicio_ampliacion_prestamo.py → i_repositorio_ampliacion_prestamo.py → repositorio_ampliacion_prestamo_sql.py`. La regla del plazo y las transiciones están en `dominio/gestion_prestamos/ampliacion_prestamo.py`. El controlador de préstamos consulta ese servicio para mostrar la sección; no ejecuta las decisiones de aprobación.

Las pruebas de este flujo se ejecutan con `python -m unittest discover -s tests -p test_ampliacion_prestamo.py -v`. Las de integración requieren `TEST_MYSQL_PORT`, `TEST_MYSQL_USER` y `TEST_MYSQL_PASSWORD`; crean y eliminan bases temporales propias. Sin MySQL se omiten esos casos y solo se ejecutan las comprobaciones del dominio.

## Reportes

El módulo **Reportes** permite consultar préstamos y devoluciones por fecha de entrega, estado del préstamo, tipo de solicitante, modalidad y búsqueda por persona o bien. Las fechas se interpretan en horario de Lima e incluyen ambos días. El tipo de persona corresponde al solicitante principal; la búsqueda también encuentra integrantes de préstamos grupales.

El resumen cuenta préstamos distintos y bienes sin duplicarlos por cada integrante. Presenta devueltos, pendientes y vencidos; los vencidos son parte de los pendientes. Los resultados muestran hasta 50 bienes por página y la descarga CSV incluye todas las coincidencias de los filtros, con fechas en Lima, separador `;` y codificación UTF-8. Al importar el CSV en Excel, selecciona formato texto para los DNI si necesitas conservar los ceros iniciales. Los campos de texto que podrían interpretarse como fórmulas se exportan como texto.

Se requiere el permiso `REPORTES_CONSULTAR`, incluido para Administrador y Encargado de préstamos en los datos de prueba. En una base ya instalada, un administrador puede habilitarlo desde **Roles y permisos** sin recrear las tablas. No se crean tablas de reportes ni se modifican los préstamos al consultarlos o descargarlos.
