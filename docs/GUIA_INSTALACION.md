# Guía de instalación

Sistema de Recursos · Escuela Profesional de Ciencia de la Computación · UNSA

Esta guía cubre la instalación desde cero en Windows. Ejecuta los comandos en **PowerShell**.

## 1. Requisitos

| Programa | Versión | Comprobar con |
|---|---|---|
| Python | 3.10 o superior | `python --version` |
| MySQL Server | 8.0.13 o superior (probado con 8.4) | `mysql --version` o el servicio `MySQL84` en *Servicios* |
| Navegador | Chrome, Edge o Firefox recientes | — |

Para descargar las dependencias de Python se requiere internet. Las fuentes y estilos
están incluidos en el repositorio para el uso cotidiano.

## 2. Instalación nueva

### 2.1 Crear la base de datos

Elige un archivo. En MySQL Workbench, ábrelo con **File → Open SQL Script** y ejecuta
el contenido completo.

| Archivo | Para qué | Base que crea |
|---|---|---|
| `SistemaRecursos/sql/datos_prueba.sql` | Demostración con datos ficticios y cuentas de prueba | `prestamos_escuela_pruebas` |
| `SistemaRecursos/sql/schema.sql` | Base nueva para uso real | `prestamos_escuela` |

Ambos archivos crean el esquema completo. Usa `datos_prueba.sql` para una base de demostración nueva.

Cuentas de la base de demostración:

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `AdminPrueba2026!` | Administrador |
| `encargado1`, `encargado2` | `EncargadoPrueba2026!` | Encargado de préstamos |
| `usuario1`, `estudiante01` … `estudiante08` | `UsuarioPrueba2026!` | Usuario |

### 2.2 Configurar la conexión

`run.ps1` usa MySQL local y pide la contraseña cuando hace falta. Puedes configurar la conexión
en PowerShell o guardar estos valores en `SistemaRecursos/config.local.ps1`, un archivo local
ignorado por Git.

```powershell
$env:DB_PASSWORD = 'tu_contraseña_de_mysql'
$env:DB_NAME = 'prestamos_escuela_pruebas'   # o 'prestamos_escuela' para uso real
# Opcionales: $env:DB_HOST, $env:DB_PORT (3306), $env:DB_USER (root), $env:PORT (5001)
```

### 2.3 Crear el administrador con `schema.sql`

Si elegiste `schema.sql`, crea la primera cuenta desde la carpeta `SistemaRecursos`.

```powershell
$env:DB_NAME = 'prestamos_escuela'
.\run.ps1 -CrearAdministrador
```

El script pide los datos del responsable y muestra un código de un solo uso. Después de iniciar
la web, entra a **Activar cuenta** dentro de las próximas 24 horas para elegir la contraseña.
Esta opción solo está disponible mientras la base no tenga cuentas. Usa `prestamos_escuela`
también en `config.local.ps1` si configuraste la conexión allí.

### 2.4 Iniciar el sistema

```powershell
.\run.ps1
```

Desde `SistemaRecursos`, el script prepara `.venv` e instala las dependencias la primera vez
o cuando cambia `requirements.txt`. Luego inicia la web y la revisión automática de vencimientos.
Abre <http://127.0.0.1:5001>.

Para operarlos por separado, usa PowerShell en dos terminales:

```powershell
.\run.ps1 -SoloProcesador
.\run.ps1 -SoloWeb
```

Si usas `flask run` o un servidor WSGI que importe `create_app`, ejecuta el procesador
independiente. Ambos deben apuntar a la misma base. El procesador revisa cada 30 segundos,
coordina la ejecución por base y vuelve a intentar los ciclos que fallan. Inicio muestra
la última revisión correcta y un aviso si queda desactualizada.

## 3. Pruebas automáticas

Desde `SistemaRecursos`:

```powershell
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas con MySQL se saltan si no hay un servidor de pruebas. Para ejecutarlas, apunta a
un servidor **que no tenga datos reales** (cada prueba crea y borra su propia base
`pruebas_sanciones_*`):

```powershell
$env:TEST_MYSQL_PORT = '3306'
$env:TEST_MYSQL_PASSWORD = 'contraseña_del_servidor_de_pruebas'
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 4. Problemas frecuentes

| Mensaje o síntoma | Causa | Solución |
|---|---|---|
| `la ejecución de scripts está deshabilitada en este sistema` | Política de ejecución de PowerShell | Usa `powershell -ExecutionPolicy Bypass -File .\run.ps1` (solo afecta a esa ejecución) |
| `Unknown database` o falta una tabla o columna | La conexión apunta a una base sin el esquema vigente | Importa el SQL completo en una base nueva y comprueba `DB_NAME` |
| `Access denied for user 'root'` | Contraseña o usuario de MySQL incorrectos | Revisa `config.local.ps1` |
| `Can't connect to MySQL server` | El servicio de MySQL está detenido | Inicia el servicio `MySQL84` en *Servicios* de Windows |
| El navegador muestra el diseño antiguo | Caché del navegador | Recarga con Ctrl + F5 |
| «Demasiados intentos fallidos» al iniciar sesión | 5 intentos fallidos seguidos de esa cuenta (o 20 del mismo equipo) | Espera 15 minutos; reiniciar la aplicación también borra el contador |
| «Tu sesión terminó» | 30 minutos sin actividad u 8 horas desde el ingreso | Vuelve a iniciar sesión |
| Aviso en Inicio: «La revisión automática … no se está ejecutando» | Procesador detenido o error de MySQL | Revisa el proceso y el último error que muestra Inicio |
| `Puerto 5001 en uso` | Otra instancia sigue abierta | Cierra la otra ventana o define `$env:PORT = '5002'` |

## 5. Seguridad al publicar en red

Para una demostración local no hace falta nada más. Si el sistema se usará desde otras
computadoras:

- Define `FLASK_SECRET_KEY` con un valor largo y aleatorio (si no, se usa `clave_sesion.txt`).
- Sirve la aplicación detrás de HTTPS y activa `SESSION_COOKIE_SECURE`.
- Usa un usuario de MySQL con permisos solo sobre la base del sistema, no `root`.
- El límite de intentos de acceso vive en la memoria del proceso: con varias instancias,
  cada una lleva su propio contador.
