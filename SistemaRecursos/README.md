# Sistema de préstamos escolares — versión simplificada

Aplicación local con Flask y MySQL. Esta versión conserva los casos de uso de la anterior y reduce los archivos intermedios para facilitar su lectura.

## Preparar MySQL sin modificar la base anterior

Requisitos: Python 3.10 o superior y MySQL 8. La aplicación utiliza por defecto `prestamos_escuela_rehecho`.

Los dos SQL conservan las mismas 19 tablas: `schema.sql` crea la estructura vacía y `datos_prueba.sql` incluye usuarios y datos de demostración. Para preparar una base separada, desde esta carpeta genera una copia local del SQL:

```powershell
New-Item -ItemType Directory -Force datos_locales | Out-Null
(Get-Content sql/datos_prueba.sql -Raw -Encoding UTF8).Replace('prestamos_escuela_pruebas', 'prestamos_escuela_rehecho') |
    Set-Content datos_locales/base_rehecha.sql -Encoding UTF8
```

Abre **`datos_locales/base_rehecha.sql`** en MySQL Workbench y ejecútalo para crear la base nueva. No ejecutes una recreación sobre una base con información que necesites conservar.

## Iniciar

El entorno virtual propio está en `..\.venv`. Desde esta carpeta configura:

```powershell
$env:DB_HOST = '127.0.0.1'
$env:DB_PORT = '3306'
$env:DB_USER = 'root'
$env:DB_PASSWORD = Read-Host 'Contraseña de MySQL'
$env:DB_NAME = 'prestamos_escuela_rehecho'
..\.venv\Scripts\python.exe app.py
```

Abre **http://127.0.0.1:5001**. Puedes cambiar el puerto mediante `PORT`.

También puedes ejecutar `run.ps1`: crea el entorno si falta e instala los requisitos. Opcionalmente carga las variables desde `config.local.ps1`, un archivo ignorado por Git. Para preparar manualmente un entorno nuevo en otro equipo:

```powershell
py -3 -m venv ..\.venv
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

En Linux: `python3 -m venv ../.venv`, `../.venv/bin/python -m pip install -r requirements.txt` y `../.venv/bin/python app.py`, definiendo las mismas variables de conexión.

`FLASK_SECRET_KEY` tiene prioridad para firmar sesiones. Si no se define, el desarrollo local conserva una clave en `datos_locales/clave_sesion.txt`; no se genera una diferente al reiniciar. Ese archivo está fuera de Git.

## Usuarios de demostración

| Usuario | Contraseña | Rol |
| --- | --- | --- |
| `admin` | `AdminPrueba2026!` | Administrador |
| `encargado1`, `encargado2` | `EncargadoPrueba2026!` | Encargado de préstamos |
| `usuario1`, `estudiante01` a `estudiante08` | `UsuarioPrueba2026!` | Usuario |

Estas contraseñas pertenecen a la demostración, no a MySQL. La aplicación conserva el comportamiento de acceso anterior: cuenta y persona activas, comprobación de contraseña, permisos actuales, CSRF y descarte de sesión si cambia la contraseña. No incluye límite de intentos ni revocación individual de cookies en el servidor.

## Cómo está organizado

```text
app.py                       Configuración, conexión de servicios y rutas
presentacion/
  controladores/             Reciben HTTP y renderizan las plantillas
  vistas/                    Solo plantillas HTML
  static/                    CSS, JavaScript e imágenes
  seguridad.py               Sesiones, CSRF y permisos
servicios/                   Coordinación de los casos de uso
dominio/                     Datos, reglas y contratos por área
repositorio/                 Consultas, bloqueos y escrituras MySQL
sql/                         Los dos SQL
tests/                       Pruebas unitarias, de integración y arquitectura
```

| Dominio | Qué contiene |
| --- | --- |
| `personas.py` | Persona, tipos institucionales, validaciones, construcción de fichas y su contrato. |
| `cuentas.py` | Cuenta, identidad de acceso, credenciales, roles, permisos y contratos de acceso/administración. |
| `recursos.py` | Categorías, recursos, bienes, condiciones y estados, conversiones y contratos. |
| `prestamos.py` | Préstamo, detalles, participantes, entrega, devolución, ampliación y contratos transaccionales. |
| `reservas.py` | Estados y reglas de reserva, preparación y retiro, y su contrato. |
| `control.py` | Políticas, horario, límites, incidencias y sanciones. |
| `reportes.py` | Contrato y resultados tipados de los reportes. |
| `validaciones.py` | Texto, enteros, fechas y versiones de edición compartidas. |

Las conversiones `crear_recurso` y `crear_bien_material` están junto a sus entidades. `FabricaPersona` conserva la selección del tipo institucional; las construcciones que coordinan varios objetos o convierten entradas de políticas permanecen dentro de su área.

## Recorridos para explicar el código

**Login:** formulario HTML → `ControladorAcceso` → `ServicioAplicacionAcceso` → `IRepositorioAcceso` (en `dominio/cuentas.py`) → `RepositorioAccesoSQL`. La contraseña se comprueba en el servicio; la cuenta decide si tiene acceso. `seguridad.py` crea y recupera la sesión. El login solo carga cuenta e identidad básica; una ficha académica o laboral se consulta cuando se necesita.

**Administrar cuentas:** `ControladorPersona` → `ServicioAplicacionCuenta` → `IRepositorioCuenta` → el mismo adaptador SQL. Crear cuentas, editar contraseñas y activar/desactivar no amplía el contrato del login.

**Entregar un préstamo:** `ControladorPrestamo` → `ServicioAplicacionPrestamo` → operación transaccional del repositorio. El dominio comprueba persona, sanciones, cupo, disponibilidad, política y horario. Se confirman juntos préstamo, detalles, integrantes, inventario e historial. Una entrega desde reserva reutiliza esa misma operación, sin otra conexión independiente.

**Ampliar:** el usuario lo pide presencialmente. El personal abre el préstamo, elige un bien y añade horas o días. Se muestra el nuevo vencimiento; se validan política, horario y fecha vigente y se actualizan detalle e historial juntos. No hay solicitudes digitales ni tabla de ampliaciones.

**Reportes:** `ControladorReporte` → `ServicioAplicacionReporte` → `RepositorioReporteSQL`. La consulta y el CSV no escriben préstamos ni sanciones.

## Dónde hacer cada cambio

| Cambio | Punto de entrada |
| --- | --- |
| Diseño de una pantalla | Su HTML, CSS o JavaScript |
| Sesión, formularios protegidos y permisos | `presentacion/seguridad.py` |
| Autenticación | `servicios/servicio_acceso.py` y reglas de cuenta |
| Alta o edición de cuenta | `servicios/servicio_cuenta.py` |
| Matrícula, ciclo o datos de persona | `dominio/personas.py` y su servicio |
| Plazo, límite o horario | `dominio/control.py` y servicio de políticas |
| Entrega, devolución o ampliación | Servicio del caso y `dominio/prestamos.py` |
| Consulta SQL | Su repositorio |
| Bloqueo por sanción activa | Consulta compartida en `repositorio_sancion_sql.py` |

Una modificación del contrato de datos puede requerir varias capas. Las reglas tienen un propietario identificable y se prueban sin introducir clases adicionales por cada paso.

## Verificar

```powershell
$env:TEST_MYSQL_PORT = '3306'
$env:TEST_MYSQL_USER = 'root'
$env:TEST_MYSQL_PASSWORD = Read-Host 'Contraseña de MySQL de pruebas'
..\.venv\Scripts\python.exe verificar.py
```

Se crean bases `test_*` independientes y se eliminan al finalizar. La cuenta necesita permisos para crearlas y eliminarlas. El procesador de vencimientos está desactivado en los casos de prueba. `verificar.py` exige que no haya pruebas omitidas. Sin MySQL puedes ejecutar las unitarias con `python -m unittest discover -s tests -v`, pero ese resultado omitirá integración.

Las pruebas de arquitectura comprueban que dominio y servicios no importen presentación ni persistencia y que los módulos internos no formen ciclos.

## Alcance de esta copia

Se conserva el esquema y las funciones existentes. La pérdida y el daño siguen registrando inventario e historial; no se inventaron nuevas reglas de sanción. Las sanciones automáticas por retraso conservan su alcance sobre el responsable y los integrantes del grupo. Los diagramas heredados de la raíz son referencias de la versión anterior, no un mapa de estos archivos.
