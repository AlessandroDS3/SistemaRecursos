# Recurso · Catálogo académico con MySQL

HTML, CSS, JavaScript y Python, con persistencia **MySQL**. Avance acumulado estimado: **25%**. Incluye catálogo de recursos y ejemplares, más registro, consulta, búsqueda y fichas de estudiantes, docentes y administrativos. Fechas automáticas y series aleatorias al guardar. Préstamos y los demás módulos siguen pendientes. Se añadió inicio de sesión local con cuentas en MySQL. La interfaz usa azul, verde claro y blanco y no muestra porcentajes ni avisos de entrega.

## Inicio en Windows

1. Enciende tu **MySQL Server** y comprueba que tu conexión de Workbench funciona. Workbench es el cliente; el servicio MySQL también debe estar iniciado.
2. Abre **configurar_mysql.cmd**. La primera vez crea `.venv` e instala el conector desde `requirements.txt` (requiere Internet).
3. Introduce host, puerto, usuario, contraseña y nombre de base. Usa los mismos datos que en Workbench. La contraseña no se muestra al escribirla. Si la base no existe, el asistente intenta crearla; el usuario necesita permisos para ello. Si existe, necesita permisos para crear tablas y leer/escribir sus datos.
4. Crea tu cuenta ejecutando **crear_usuario.cmd** (usuario y contraseña propios).
5. Abre **iniciar.cmd** y visita http://127.0.0.1:8000. Deja la terminal abierta.

Si ya tienes `config.ini`, edítalo para cambiar los datos: el asistente no lo sobrescribe. Para usar otro puerto web: `.venv\Scripts\python.exe server.py --port 8001`.

`config.ini` guarda la conexión local y está excluido de Git, al igual que `.venv` y las bases SQLite antiguas. El archivo `config.example.ini` solo contiene valores de ejemplo, sin contraseña. No publiques tu archivo local de configuración.

## Configuración manual

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe configurar_mysql.py
.venv\Scripts\python.exe server.py
```

El iniciador también detecta el Python incluido en Codex si `python` o `py` no están disponibles.

## Conservar registros anteriores de SQLite

Cierra el servidor antiguo y configura una base MySQL vacía de recursos y bienes. Después:

```powershell
.venv\Scripts\python.exe migrar_sqlite.py data\catalogo.sqlite3
```

La importación conserva IDs, categorías, códigos, fechas, series y estados. Abre SQLite en modo de solo lectura, no elimina el archivo original y confirma todos los registros en una transacción MySQL. Si ya hay recursos o bienes en el destino, se detiene para evitar duplicados. No ejecutes registros nuevos mientras importas. Si no tenías datos, no necesitas importar nada.

## Datos ficticios opcionales

Configura una base separada cuyo nombre termine en `_demo`:

```powershell
.venv\Scripts\python.exe configurar_mysql.py --config config.demo.ini
.venv\Scripts\python.exe demo.py --config config.demo.ini
.venv\Scripts\python.exe server.py --config config.demo.ini --port 8001
```

## Arquitectura

- `app/domain.py`: Recurso, BienMaterial y reglas de validación.
- `app/service.py`: casos de uso de registro.
- `app/repository.py`: RecursoMySQLRepository, consultas parametrizadas y transacciones.
- `app/config.py`: lectura de la conexión local.
- `sql/schema.sql`: tablas InnoDB, claves foráneas, identificadores AUTO_INCREMENT y código de inventario único.
- `server.py`: API HTTP local y archivos estáticos.
- `templates/`: páginas HTML (acceso, catálogo y personas).
- `static/css/`: hojas de estilo.
- `static/js/`: JavaScript y comunicación mediante fetch.
- `static/img/`: imágenes y logo de la escuela.
- `app/`: lógica Python, autenticación, configuración y persistencia.
- `tests/`: pruebas automatizadas.
- `docs/`: documentación.

Los archivos de inicio y utilidades Python se mantienen en la raíz junto con sus lanzadores CMD para facilitar la ejecución. El servidor publica únicamente rutas explícitas; no expone carpetas internas ni configuración.
- `migrar_sqlite.py`: importación opcional; es el único componente que lee SQLite.

Las fechas DATE de MySQL se convierten a texto ISO para mantener compatible la API. Las nuevas series y fechas se generan en Python y no se aceptan valores manuales del navegador. Los datos históricos se conservan al importar.

## Pruebas

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Sin servidor configurado se ejecutan las pruebas unitarias y se omiten explícitamente las pruebas de integración. Para ejecutar también las pruebas HTTP sobre MySQL real:

```powershell
$env:MYSQL_TEST_CONFIG = (Resolve-Path config.ini).Path
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

El usuario de prueba necesita CREATE/DROP DATABASE. Cada caso crea y elimina únicamente una base con nombre aleatorio `test_prestamos_...`; no modifica la base indicada en config.ini. Las pruebas simuladas no sustituyen la validación contra un servidor real.

## API

| Método | Ruta | Función |
|---|---|---|
| GET | `/api/catalogo` | Recursos, ejemplares, categorías y enumeraciones |
| POST | `/api/recursos` | Recurso y primer bien en una transacción |
| POST | `/api/recursos/{id}/bienes` | Añadir ejemplar |

La aplicación se ejecuta localmente en 127.0.0.1. Requiere inicio de sesión. No incorpora despliegue público.

Conector y transacciones basados en la [documentación oficial de MySQL](https://dev.mysql.com/doc/connectors/en/connector-python-example-cursor-transaction.html).

## Nuevo módulo de personas

Accede a **Personas** en el menú. Se registran nombres, apellidos, documento, correo, teléfono opcional y datos institucionales según el tipo. Estudiantes requieren código y ciclo; docentes requieren código docente; administrativos requieren código de empleado. Los demás campos institucionales son opcionales. La persona inicia ACTIVA y su fecha de registro se asigna automáticamente en MySQL. No se crean cuentas ni contraseñas en este avance.

`app/personas.py` contiene validaciones y servicio; `app/persona_repository.py` guarda Persona y su especialización en una sola transacción. El documento es único globalmente y el código es único dentro de cada tipo. Las reglas de formato propuestas no validan identidad con servicios externos.

Rutas nuevas: `GET /personas`, `GET /api/personas`, `POST /api/personas`.

Al iniciar, `sql/schema.sql` crea las tablas nuevas `persona`, `estudiante`, `docente` y `administrativo` si no existen, sin borrar el catálogo. No es necesario volver a importar SQLite. La cuenta MySQL necesita permiso CREATE TABLE para esta actualización.

## Inicio de sesión

Primero ejecuta `crear_usuario.cmd` en la carpeta del proyecto. Elige usuario y contraseña de 10 a 128 caracteres; no hay credenciales predeterminadas. Después inicia con `iniciar.cmd` y entra en la web. Las cuentas de acceso se guardan en `usuario_sistema`, separadas de las personas del directorio. Todas las cuentas tienen acceso a los dos módulos; roles y permisos diferenciados quedan pendientes.

Las contraseñas se almacenan como derivaciones scrypt con salt aleatorio. La sesión usa una cookie HttpOnly y SameSite=Strict, caduca a las 8 horas y se invalida al cerrar sesión o reiniciar el servidor. El catálogo, las personas y sus API requieren autenticación. Se limitan los intentos a cinco por minuto por dirección de cliente. La sesión permanece en memoria del proceso; este servidor continúa siendo de uso local por HTTP. Publicarlo requeriría HTTPS y cookies Secure, entre otras adaptaciones.

No se incluye registro público ni recuperación de contraseña. Para crear otra cuenta usa el asistente local. La fecha de creación es automática. Se retiraron emojis y pictogramas decorativos del código.
