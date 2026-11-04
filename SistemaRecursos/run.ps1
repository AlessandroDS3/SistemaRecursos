$ErrorActionPreference = 'Stop'

if (-not $env:DB_HOST) { $env:DB_HOST = '127.0.0.1' }
if (-not $env:DB_PORT) { $env:DB_PORT = '3306' }
if (-not $env:DB_USER) { $env:DB_USER = 'root' }
if (-not $env:DB_NAME) { $env:DB_NAME = 'prestamos_escuela_pruebas' }
if ([string]::IsNullOrWhiteSpace($env:DB_PASSWORD)) {
    throw 'Configura DB_PASSWORD en tu entorno antes de iniciar.'
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
