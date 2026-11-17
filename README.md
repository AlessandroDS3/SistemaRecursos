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
