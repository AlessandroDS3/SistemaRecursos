# Guía de instalación y actualización

Sistema de Recursos · Escuela Profesional de Ciencia de la Computación · UNSA

Esta guía sirve para instalar el sistema en una computadora con Windows, actualizar una
instalación existente y resolver los problemas más comunes. Los comandos se escriben en
**PowerShell**.

## 1. Requisitos

| Programa | Versión | Comprobar con |
|---|---|---|
| Python | 3.10 o superior | `python --version` |
| MySQL Server | 8.0.13 o superior (probado con 8.4) | `mysql --version` o el servicio `MySQL84` en *Servicios* |
| Navegador | Chrome, Edge o Firefox recientes | — |

No hace falta internet para usar el sistema: las fuentes y los estilos están incluidos.
Sí hace falta la primera vez, para que `run.ps1` instale las dependencias de Python.

## 2. Instalación nueva

### 2.1 Crear la base de datos

Elige **una** de estas dos opciones e impórtala en MySQL (Workbench → *Server → Data Import*
o desde la consola con `mysql -u root -p < archivo.sql`):

| Archivo | Para qué | Base que crea |
|---|---|---|
| `SistemaRecursos/sql/datos_prueba.sql` | Demostración con datos ficticios y cuentas de prueba | `prestamos_escuela_pruebas` |
| `SistemaRecursos/sql/schema.sql` | Uso real, sin datos | `prestamos_escuela` |

Ambos archivos ya incluyen todas las tablas actuales (sanciones por gravedad, sesiones,
mantenimientos, solicitudes de ampliación y procesador). **No** necesitan migraciones.

> No importes `datos_prueba.sql` sobre una base con datos reales.

Cuentas de la base de demostración:

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `AdminPrueba2026!` | Administrador |
| `encargado1`, `encargado2` | `EncargadoPrueba2026!` | Encargado de préstamos |
| `usuario1`, `estudiante01` … `estudiante08` | `UsuarioPrueba2026!` | Usuario |

### 2.2 Configurar la conexión

Crea el archivo `SistemaRecursos/config.local.ps1` (Git lo ignora, no se sube al repositorio):

```powershell
$env:DB_PASSWORD = 'tu_contraseña_de_mysql'
$env:DB_NAME = 'prestamos_escuela_pruebas'   # o 'prestamos_escuela' para uso real
# Opcionales: $env:DB_HOST, $env:DB_PORT (3306), $env:DB_USER (root), $env:PORT (5001)
```

Si no creas el archivo, `run.ps1` pide la contraseña cada vez.

### 2.3 Crear el administrador (solo con `schema.sql`)

Con una base vacía no existe ninguna cuenta. Desde la carpeta `SistemaRecursos`:

```powershell
..\.venv\Scripts\python.exe -m arranque.inicializar_administrador --dni 12345678 --nombres "Ana" --apellidos "Pérez" --correo "ana@unsa.edu.pe" --codigo-empleado ADM001 --area "Administración" --usuario ana
```

El comando muestra una contraseña temporal; el sistema pedirá cambiarla al entrar.
Solo funciona si la base todavía no tiene cuentas. (La primera vez ejecuta antes `run.ps1`
para que se cree el entorno `.venv`.)

### 2.4 Iniciar el sistema

```powershell
cd SistemaRecursos
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Abre <http://127.0.0.1:5001>. El script crea el entorno virtual, instala las dependencias,
comprueba que la base tenga el esquema correcto y arranca la aplicación junto con la
**revisión automática de vencimientos** (cada 30 segundos).

> **Importante:** inicia siempre con `run.ps1`. Si la aplicación se levanta de otra forma
> (por ejemplo `flask run` o un servidor como waitress importando `create_app`), la revisión
> automática **no** se inicia; el administrador verá un aviso en Inicio.

## 3. Actualizar una instalación existente

1. Detén la aplicación (Ctrl + C en la ventana donde corre).
2. Haz una copia de seguridad de la base:

   ```powershell
   & "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe" -u root -p prestamos_escuela_pruebas > "$HOME\Desktop\respaldo_antes_de_actualizar.sql"
   ```

3. Actualiza el código (`git pull`).
4. Aplica las migraciones que falten y arranca:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\run.ps1 -MigrarSanciones -MigrarCierre
   ```

   | Opción | Archivo | Qué agrega |
   |---|---|---|
   | `-MigrarSanciones` | `sql/migraciones/20261123_sanciones_por_gravedad.sql` | Sanciones leve/grave/muy grave y regularización |
   | `-MigrarCierre` | `sql/migraciones/20261124_cierre_pendientes.sql` | Identificador del sistema y fecha de registro de bienes, sesiones, mantenimientos, solicitudes de ampliación y estado del procesador |

   Las migraciones **se pueden ejecutar varias veces**: si un cambio ya existe, lo saltan.
   No borran datos. También se pueden ejecutar desde MySQL Workbench seleccionando la base
   y abriendo el archivo `.sql`.

5. La aplicación revisa el esquema al iniciar. Si falta una migración, se detiene con un
   mensaje que indica qué opción usar.

### Qué hacer si una migración se interrumpe

Cada bloque de la migración es independiente. Vuelve a ejecutarla: los bloques ya aplicados
se saltan y los pendientes se completan. Si el error persiste, restaura la copia del paso 2
en una base nueva y revisa el mensaje de MySQL.

## 4. Pruebas automáticas

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

## 5. Problemas frecuentes

| Mensaje o síntoma | Causa | Solución |
|---|---|---|
| `la ejecución de scripts está deshabilitada en este sistema` | Política de ejecución de PowerShell | Usa `powershell -ExecutionPolicy Bypass -File .\run.ps1` (solo afecta a esa ejecución) |
| `La base tiene un esquema anterior … run.ps1 -MigrarSanciones` o `-MigrarCierre` | Falta una migración | Sigue la sección 3 |
| `Unknown column 'fecha_regularizacion'` | Falta `-MigrarSanciones` | Sección 3 |
| `Access denied for user 'root'` | Contraseña o usuario de MySQL incorrectos | Revisa `config.local.ps1` |
| `Can't connect to MySQL server` | El servicio de MySQL está detenido | Inicia el servicio `MySQL84` en *Servicios* de Windows |
| El navegador muestra el diseño antiguo | Caché del navegador | Recarga con Ctrl + F5 |
| «Demasiados intentos fallidos» al iniciar sesión | 5 intentos fallidos seguidos de esa cuenta (o 20 del mismo equipo) | Espera 15 minutos; reiniciar la aplicación también borra el contador |
| «Tu sesión terminó» | 30 minutos sin actividad u 8 horas desde el ingreso | Vuelve a iniciar sesión |
| Aviso en Inicio: «La revisión automática … no se está ejecutando» | La aplicación no se inició con `run.ps1` o MySQL falló | Reinicia con `run.ps1`; el aviso muestra el último error |
| `Puerto 5001 en uso` | Otra instancia sigue abierta | Cierra la otra ventana o define `$env:PORT = '5002'` |

## 6. Seguridad al publicar en red

Para una demostración local no hace falta nada más. Si el sistema se usará desde otras
computadoras:

- Define `FLASK_SECRET_KEY` con un valor largo y aleatorio (si no, se usa `clave_sesion.txt`).
- Sirve la aplicación detrás de HTTPS y activa `SESSION_COOKIE_SECURE`.
- Usa un usuario de MySQL con permisos solo sobre la base del sistema, no `root`.
- El límite de intentos de acceso vive en la memoria del proceso: con varias instancias,
  cada una lleva su propio contador.
