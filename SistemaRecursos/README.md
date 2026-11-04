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

El archivo `run.ps1` ya configura la conexión local a MySQL (servidor, puerto, usuario, contraseña y base de datos `prestamos_escuela_pruebas`). Si tu configuración es diferente, edita esos valores directamente en `run.ps1`.

Desde PowerShell, dentro de `SISTEMA_RECURSOS`:

```powershell
.\run.ps1
```

El script espera que el entorno virtual esté en `..\.venv`, es decir, junto a la carpeta `SISTEMA_RECURSOS`, como se describe en **Instalación**.

La base `prestamos_escuela_pruebas` debe existir y contener las tablas compatibles con esta versión. Para una instalación nueva con registros ficticios utiliza `sql/datos_prueba.sql`; si ya tiene datos, conserva esa base y actualiza su esquema antes de ejecutar.

Abre `http://127.0.0.1:5000`. Para iniciar sesión se necesita una cuenta habilitada en la base de datos utilizada; el esquema limpio no agrega usuarios predeterminados.

**Seguridad:** `run.ps1` contiene una contraseña local en texto plano. No lo publiques ni lo compartas con contraseñas reales. Para un despliegue compartido, usa variables de entorno o una configuración local excluida del control de versiones.

## Código principal

- `app.py`: configuración y arranque de Flask.
- `dominio/`: entidades y reglas del negocio.
- `servicios/`: casos de uso y operaciones.
- `repositorio/`: acceso a MySQL.
- `presentacion/`: rutas, vistas HTML, JavaScript, CSS e imágenes.
- `sql/schema.sql`: esquema sin datos.
- `sql/datos_prueba.sql`: esquema con datos ficticios de demostración.
