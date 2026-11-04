# Sistema de préstamos escolares

Aplicación web Flask + MySQL para gestionar personas, usuarios, roles, permisos, recursos, bienes, políticas, reservas, préstamos y devoluciones.

## Requisitos

- Python 3.10 o superior.
- MySQL 8.

## Instalación

Desde PowerShell, en la carpeta `SISTEMA_RECURSOS`:

```powershell
py -m venv ..\.venv
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Base de datos

El proyecto incluye **dos archivos SQL completos** para instalaciones nuevas:

- `sql/schema.sql`: crea `prestamos_escuela` con las tablas vacías, el horario de atención y la política inicial de vencimientos. No crea cuentas de acceso.
- `sql/datos_prueba.sql`: crea `prestamos_escuela_pruebas` con las mismas tablas y datos ficticios, incluidos roles, permisos, bienes y cuentas de demostración. Este es el archivo que corresponde al nombre configurado en `run.ps1`.

**Elige uno** para instalar una base nueva. No ejecutes ambos sobre la misma base ni vuelvas a importar `datos_prueba.sql` en una base que ya contiene registros.

Ambos incluyen la tabla `politica_vencimiento_reserva` y los campos `reserva.fecha_preparacion` y `reserva.fecha_limite_vencimiento`. La configuración inicial es 2 días desde el retiro solicitado para solicitudes `EN_ESPERA` y 24 horas desde la preparación para reservas `LISTA_PARA_RETIRO`. Los registros de prueba abiertos reciben su fecha límite al cargarse.

**Una base MySQL existente no se modifica al actualizar estos archivos SQL.** Antes de usar esta versión con una base anterior que ya contiene datos, realiza un respaldo y actualiza su estructura una sola vez con los cambios de vencimientos. No uses `CREATE TABLE IF NOT EXISTS` para suponer que las columnas se agregan a tablas existentes. La ejecución y verificación de esta actualización dependen de tu instalación local.

El procesador del servidor revisa los vencimientos aproximadamente cada 30 segundos mientras la aplicación está activa. Los plazos configurados se guardan individualmente por solicitud; los cambios de política no alteran retroactivamente las fechas ya calculadas.

## Iniciar aplicación

Configura `DB_PASSWORD` en tu entorno antes de ejecutar `run.ps1`. El script respeta también `DB_HOST`, `DB_PORT`, `DB_USER` y `DB_NAME`. Para varias instancias de Flask, configura la misma `FLASK_SECRET_KEY` en todas ellas.

Si actualizas una instalación existente, ejecuta `sql/migracion_acceso.sql` con la base de la aplicación seleccionada antes de arrancar la nueva versión. La migración crea las tablas de sesiones e intentos de acceso y se puede repetir. Las sesiones anteriores a la actualización requieren un nuevo inicio de sesión.

Desde PowerShell, dentro de `SISTEMA_RECURSOS`:

```powershell
.\run.ps1
```

El script espera que el entorno virtual esté en `..\.venv`, es decir, junto a la carpeta `SISTEMA_RECURSOS`, como se describe en **Instalación**.

La base `prestamos_escuela_pruebas` debe existir y contener las tablas compatibles con esta versión. Para una instalación nueva con registros ficticios utiliza `sql/datos_prueba.sql`; si ya tiene datos, conserva esa base y actualiza su esquema antes de ejecutar.

Abre `http://127.0.0.1:5000`. Para iniciar sesión se necesita una cuenta habilitada en la base de datos utilizada; el esquema limpio no agrega usuarios predeterminados.

## Pruebas de personas y acceso

Dentro de la carpeta que contiene `app.py`, define `TEST_MYSQL_PORT` para una instancia local de pruebas y ejecuta `python -m unittest discover -s tests -v`. Las pruebas crean y eliminan una base temporal con nombre único. La cuenta de pruebas necesita esos permisos. Puedes indicar sus credenciales con `TEST_MYSQL_USER` y `TEST_MYSQL_PASSWORD`.

## Código principal

- `app.py`: configuración y arranque de Flask.
- `dominio/`: entidades y reglas del negocio.
- `servicios/`: casos de uso y operaciones.
- `repositorio/`: acceso a MySQL.
- `presentacion/`: rutas, vistas HTML, JavaScript, CSS e imágenes.
- `sql/schema.sql`: esquema sin datos.
- `sql/datos_prueba.sql`: esquema con datos ficticios de demostración.
