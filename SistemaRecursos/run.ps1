$ErrorActionPreference = 'Stop'

# Configuracion local: cada integrante coloca sus propios datos.
$env:DB_HOST = '127.0.0.1'
$env:DB_PORT = '3306'
$env:DB_USER = 'root'
$env:DB_PASSWORD = '20172351' # Contrasena local de MySQL; no compartir en repositorios publicos.
$env:DB_NAME = 'prestamos_escuela_pruebas'

if ($env:DB_PASSWORD -eq 'TU_CONTRASENA_REAL_DE_MYSQL' -or [string]::IsNullOrWhiteSpace($env:DB_PASSWORD)) {
    throw 'Completa DB_PASSWORD en run.ps1 con tu contrasena de MySQL antes de iniciar.'
}

$pythonProyecto = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonProyecto)) {
    throw 'No se encontro el entorno virtual en ..\.venv. Revisa README.md para instalarlo.'
}

Push-Location $PSScriptRoot
try {
    & $pythonProyecto (Join-Path $PSScriptRoot 'app.py')
    $codigoSalida = $LASTEXITCODE
}
finally {
    Pop-Location
}
exit $codigoSalida
