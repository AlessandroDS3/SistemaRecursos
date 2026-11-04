# Sistema de préstamos escolares

Aplicación web con Flask y MySQL para gestionar personas, usuarios, recursos, bienes, reservas, préstamos y devoluciones.

## Requisitos

- Python 3.10 o superior.
- MySQL 8 en ejecución.

## Preparar la base de datos

Para probar el sistema, abre `sql/datos_prueba.sql` en MySQL Workbench u otro cliente de MySQL y ejecútalo. Crea la base `prestamos_escuela_pruebas` con datos de ejemplo y las cuentas indicadas más abajo.

Ejecuta ese archivo solo en una instalación nueva; no lo vuelvas a importar sobre una base que ya contiene datos.

Si tienes una base de una versión anterior, ejecuta `sql/migracion_acceso.sql` con esa base seleccionada para crear las tablas de sesiones e intentos de acceso.

También está disponible `sql/schema.sql` para crear la base `prestamos_escuela` sin cuentas ni datos de demostración. Para utilizarla, cambia `DB_NAME` en la configuración de conexión.

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

Si `run.ps1` tiene valores de conexión asignados al inicio, esos valores reemplazan las variables anteriores; ajústalos también si tu configuración es diferente.

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

## Organización del código

- `app.py`: configura e inicia la aplicación.
- `dominio/`: entidades, validaciones y reglas del negocio.
- `servicios/`: coordina las operaciones del sistema.
- `repositorio/`: consulta y guarda los datos en MySQL.
- `presentacion/`: controladores, vistas y archivos de la interfaz.
- `sql/`: estructura de la base de datos, migraciones y datos de prueba.
