# Sistema de préstamos de recursos

> [Guía de instalación](docs/GUIA_INSTALACION.md) · [Manual por rol](docs/MANUAL_POR_ROL.md).
> En Windows, `run.ps1` prepara el entorno e inicia el sistema.

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

`run.ps1` crea `.venv` si hace falta e instala las dependencias en la primera ejecución
o cuando cambia `requirements.txt`. Solicita la contraseña de MySQL si hace falta.
Puedes definir `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` y `DB_NAME` en el entorno
o en `config.local.ps1`, que está excluido de Git.

Abre http://127.0.0.1:5001. Los reportes permiten descargar CSV y PDF respetando los filtros.
El repositorio de reportes ejecuta las consultas de la aplicación. El archivo
`SistemaRecursos/sql/reportes_consultas_aplicacion.sql` contiene consultas de referencia.

### Instalación sin datos de demostración

Importa `SistemaRecursos/sql/schema.sql`. Desde `SistemaRecursos`, crea la primera
cuenta administradora e inicia el sistema con estos comandos.

```powershell
$env:DB_NAME = 'prestamos_escuela'
.\run.ps1 -CrearAdministrador
.\run.ps1
```

Introduce los datos del responsable cuando el comando te los pida. El código que muestra
sirve para elegir la contraseña en **Activar cuenta** dentro de 24 horas. Si usas
`config.local.ps1`, configura allí también `DB_NAME` como `prestamos_escuela`.

## Roles fijos

El sistema tiene tres roles: `USUARIO`, `ENCARGADO_PRESTAMOS` y `ADMINISTRADOR`.
Sus permisos están definidos en `SistemaRecursos/dominio/gestion_personas_usuarios/rol.py`
y se muestran en **Personas → Editar cuenta y rol**. El administrador asigna los roles
a las cuentas y cada rol aplica los permisos definidos en el código.

## Sanciones por gravedad

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

La revisión automática se ejecuta cada 30 segundos. `run.ps1` inicia la revisión y la web.
Con `run.ps1 -SoloProcesador` puedes operar la revisión en otra terminal y usar
`run.ps1 -SoloWeb` o un servidor que importe la fábrica Flask para la web.
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

La guía indica la ruta de Flask, la función del controlador y el recorrido por servicios, reglas y SQL para cada operación. [Guía completa de seguimiento del código](docs/SEGUIMIENTO_DEL_CODIGO.md)

- [Inicio y acceso](docs/SEGUIMIENTO_DEL_CODIGO.md#inicio-y-acceso) · [Personas, cuentas y roles](docs/SEGUIMIENTO_DEL_CODIGO.md#personas-cuentas-y-roles)
- [Catálogo, categorías, inventario y mantenimiento](docs/SEGUIMIENTO_DEL_CODIGO.md#catálogo-categorías-inventario-y-mantenimiento)
- [Préstamos y devoluciones](docs/SEGUIMIENTO_DEL_CODIGO.md#préstamos-y-devoluciones) · [Reservas y atención de solicitudes](docs/SEGUIMIENTO_DEL_CODIGO.md#reservas-y-atención-de-solicitudes) · [Ampliaciones de plazo](docs/SEGUIMIENTO_DEL_CODIGO.md#ampliaciones-de-plazo)
- [Políticas, horario y cupos](docs/SEGUIMIENTO_DEL_CODIGO.md#políticas-horario-y-cupos) · [Sanciones e incidencias](docs/SEGUIMIENTO_DEL_CODIGO.md#sanciones-e-incidencias)
- [Reportes, historiales y exportaciones](docs/SEGUIMIENTO_DEL_CODIGO.md#reportes-historiales-y-exportaciones) · [Operaciones automáticas y de instalación](docs/SEGUIMIENTO_DEL_CODIGO.md#operaciones-automáticas-y-de-instalación)

## Pruebas

Pruebas desde `SistemaRecursos`: `..\.venv\Scripts\python.exe -m unittest discover -s tests -v`.
Para ejecutar también las pruebas MySQL, configura `TEST_MYSQL_PORT` y, si corresponde,
`TEST_MYSQL_PASSWORD` para un servidor de pruebas. Cada caso crea y elimina su propia
base `pruebas_sanciones_*`; no utiliza la base de la aplicación.
