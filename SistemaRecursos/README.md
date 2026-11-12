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
