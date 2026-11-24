# Sistema de préstamos de recursos

Aplicación en Python, Flask y MySQL. Esta rama contiene los archivos necesarios
para ejecutar el sistema: código, plantillas, estilos, imágenes de la interfaz,
dependencias, script de arranque y SQL.

## Arranque

Requisitos: Python 3.10 o superior y MySQL 8.

1. Para una instalación nueva, importa `SistemaRecursos/sql/datos_prueba.sql`.
   La aplicación usa por defecto la base `prestamos_escuela_pruebas`.
   `schema.sql` contiene el esquema vacío para preparar una base sin datos de demostración.
2. Abre PowerShell y ejecuta:

```powershell
cd SistemaRecursos
.\run.ps1
```

El script crea el entorno virtual, instala `requirements.txt` y solicita la contraseña
de MySQL. Puedes definir `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` y `DB_NAME`
en el entorno o en `config.local.ps1`, que está excluido de Git.

Abre http://127.0.0.1:5001. Los reportes permiten descargar CSV y PDF respetando los filtros.
El repositorio de reportes ejecuta las consultas de la aplicación. El archivo
`SistemaRecursos/sql/reportes_consultas_aplicacion.sql` contiene consultas de referencia.

### Instalación sin datos de demostración

Importa `SistemaRecursos/sql/schema.sql` y configura la conexión de MySQL en el
entorno. Desde `SistemaRecursos`, con las dependencias ya instaladas, ejecuta:

```powershell
$env:DB_NAME = 'prestamos_escuela'
..\.venv\Scripts\python.exe -m arranque.inicializar_administrador --dni 12345678 --nombres "Ana" --apellidos "Pérez" --correo "ana@unsa.edu.pe" --codigo-empleado ADM001 --area "Administración" --usuario ana
.\run.ps1
```

Usa los datos reales del responsable. El comando crea su ficha administrativa y
muestra una contraseña temporal que debe cambiar al entrar. Solo funciona cuando
la base todavía no tiene cuentas. Conserva el mismo `DB_NAME` al iniciar el sistema
y, si usas `config.local.ps1`, comprueba que apunte a esa base.

## Roles fijos

El sistema tiene tres roles: `USUARIO`, `ENCARGADO_PRESTAMOS` y `ADMINISTRADOR`.
Sus permisos están definidos en `SistemaRecursos/dominio/gestion_personas_usuarios/rol.py`
y se muestran como consulta en **Roles y permisos**. El administrador puede asignar
estos roles a las cuentas; los permisos de cada rol no se editan desde la aplicación.
Las instalaciones nuevas ya no crean la tabla `rol_permiso`.
Para eliminarla de una base existente, selecciona la base del sistema y ejecuta
`SistemaRecursos/sql/migraciones/20261119_eliminar_rol_permiso.sql`.
La migración conserva los roles asignados en `usuario_sistema.rol`; no es necesario
volver a importar los datos de prueba.

## Sanciones por gravedad

En otra máquina, para una base nueva, importa uno de los dos archivos SQL:
`schema.sql` crea solo las tablas, sin registros; `datos_prueba.sql` crea una base
separada con las mismas tablas y datos ficticios. Ambos incluyen las sanciones
por gravedad y no necesitan ejecutar la migración.

Para actualizar una instalación existente, detén la aplicación, haz una copia de
seguridad y ejecuta `.\run.ps1 -MigrarSanciones` desde `SistemaRecursos`. El script
actualiza la base configurada en `DB_NAME` y luego inicia la aplicación. Si usas
MySQL Workbench, selecciona esa base y ejecuta
`SistemaRecursos/sql/migraciones/20261123_sanciones_por_gravedad.sql`.
La migración conserva las cuentas, préstamos, reservas, sanciones e historiales.
Si aparece `Unknown column 'fecha_regularizacion'`, corresponde a esta actualización.

Para una instalación nueva, usa `SistemaRecursos/sql/datos_prueba.sql` si quieres
datos de demostración o `SistemaRecursos/sql/schema.sql` si prefieres partir de cero.

En **Sanciones → Configurar plazos**, el administrador configura la leve
(14 días iniciales), la grave (180 días como referencia inicial del semestre) y
la espera adicional para revisar posibles pérdidas (7 días iniciales). Cada
sanción conserva una copia de estos valores. Cambiarlos no modifica sanciones anteriores.

- **Leve:** se genera por retraso, sin tolerancia automática. Después de recibir
  el bien, el encargado puede levantarla anticipadamente con justificación.
- **Grave:** el encargado confirma pérdida, daño, salida no autorizada o falta
  de custodia. Deben cumplirse tanto su duración como la regularización del bien.
- **Muy grave:** solo el administrador puede aplicarla y rehabilitarla, después
  de regularizar el incidente. No vence automáticamente.

La revisión automática, iniciada por `run.ps1`, se ejecuta cada 30 segundos.
Cumple leves y graves únicamente si terminó su periodo y el bien fue regularizado.
Los posibles casos de pérdida o custodia se muestran como alertas para revisión;
el tiempo transcurrido no confirma una pérdida ni aplica una muy grave.
Elevar una sanción inicia el periodo del nuevo nivel desde su confirmación.
Los préstamos grupales conservan la aplicación a todos los participantes.

La reparación, recuperación o reposición se acepta desde la ficha de sanción.
Una reposición requiere equivalencia verificada y un código de inventario nuevo;
el original conserva su estado y el pendiente se cierra sin registrar una falsa devolución.
Los accesorios que deban controlarse por separado se registran y entregan como
bienes individuales, usando el inventario existente.

Se mantienen cuatro capas: reglas en `dominio`, transacciones y casos de uso en
`servicios`, SQL en `repositorio` y rutas/formularios en `presentacion`.

## Cómo seguir una operación

Dentro de `SistemaRecursos/`, los controladores, las vistas, los servicios y los
repositorios se agrupan por módulo. En `dominio/`, los archivos
`contratos_<modulo>.py` declaran las operaciones que necesitan los casos de uso.
`crear_servicios()` y `registrar_controladores()` en [app.py](SistemaRecursos/app.py)
muestran cómo se conectan las clases.

| Acción | Controlador | Caso de uso | Dominio y persistencia |
|---|---|---|---|
| Registrar persona | [`ControladorPersona.registrar_persona()`](SistemaRecursos/presentacion/controladores/personas_usuarios/controlador_persona.py) | [`ServicioAplicacionPersona.registrar_persona()`](SistemaRecursos/servicios/personas_usuarios/servicio_persona.py) | [`Persona.desde_datos()`](SistemaRecursos/dominio/gestion_personas_usuarios/persona.py) y [`RepositorioPersonaSQL.guardar_persona()`](SistemaRecursos/repositorio/personas_usuarios/repositorio_persona_sql.py) |
| Registrar bien material | [`ControladorBienMaterial.registrar_bien_material()`](SistemaRecursos/presentacion/controladores/recursos/controlador_bien_material.py) | [`ServicioAplicacionBienMaterial.registrar_bien_material()`](SistemaRecursos/servicios/recursos/servicio_bien_material.py) | [`BienMaterial.desde_datos()`](SistemaRecursos/dominio/gestion_recursos/bien_material.py) y [`RepositorioBienMaterialSQL.guardar_bien_material()`](SistemaRecursos/repositorio/recursos/repositorio_bien_material_sql.py) |
| Consultar personas | [`ControladorPersona.consultar_personas()`](SistemaRecursos/presentacion/controladores/personas_usuarios/controlador_persona.py) | [`ServicioAplicacionPersona.consultar_personas()`](SistemaRecursos/servicios/personas_usuarios/servicio_persona.py) | [`RepositorioPersonaSQL.consultar_personas()`](SistemaRecursos/repositorio/personas_usuarios/repositorio_persona_sql.py) aplica los filtros, ordena y pagina. |

Desde una pantalla, busca el botón en la plantilla y sigue `url_for()` hasta
`add_url_rule()`. Por ejemplo, **Registrar persona** sale de
[`vista_persona.html`](SistemaRecursos/presentacion/vistas/personas_usuarios/vista_persona.html)
y llega a `personas.registrar_persona`. Para una consulta, vuelve a la plantilla
después de ver el SQL para ubicar dónde se presenta cada dato.

## Pruebas

Pruebas desde `SistemaRecursos`: `..\.venv\Scripts\python.exe -m unittest discover -s tests -v`.
Para ejecutar también las pruebas MySQL, configura `TEST_MYSQL_PORT` y, si corresponde,
`TEST_MYSQL_PASSWORD` para un servidor de pruebas. Cada caso crea y elimina su propia
base `pruebas_sanciones_*`; no utiliza la base de la aplicación.
