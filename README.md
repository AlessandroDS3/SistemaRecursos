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
