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
Las consultas de reportes están en `SistemaRecursos/sql/reportes_consultas_aplicacion.sql`.

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

Para probar esta versión con los datos de demostración, importa
`SistemaRecursos/sql/datos_prueba.sql` en una base nueva. Si vas a reutilizar
`prestamos_escuela_pruebas`, recréala antes de importar el archivo.
Para partir de una base vacía, usa `SistemaRecursos/sql/schema.sql`.

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

Pruebas desde `SistemaRecursos`: `..\.venv\Scripts\python.exe -m unittest discover -s tests -v`.
Para ejecutar también las pruebas MySQL, configura `TEST_MYSQL_PORT` y, si corresponde,
`TEST_MYSQL_PASSWORD` para un servidor de pruebas. Cada caso crea y elimina su propia
base `pruebas_sanciones_*`; no utiliza la base de la aplicación.
