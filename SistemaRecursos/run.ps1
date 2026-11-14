$ErrorActionPreference = 'Stop'

$configLocal = Join-Path $PSScriptRoot 'config.local.ps1'
if (Test-Path -LiteralPath $configLocal) {
    . $configLocal
}

if (-not $env:DB_HOST) { $env:DB_HOST = '127.0.0.1' }
if (-not $env:DB_PORT) { $env:DB_PORT = '3306' }
if (-not $env:DB_USER) { $env:DB_USER = 'root' }
if (-not $env:DB_NAME) { $env:DB_NAME = 'prestamos_escuela_pruebas' }
if (-not $env:DB_PASSWORD ) {$env:DB_PASSWORD = Read-Host 'Contraseña de MySQL'}
if ([string]::IsNullOrWhiteSpace($env:DB_PASSWORD)) {
    throw 'Configura DB_PASSWORD en tu entorno antes de iniciar.'
}

$rutaEntorno = Join-Path $PSScriptRoot '..\.venv'
$pythonProyecto = Join-Path $rutaEntorno 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonProyecto)) {
    Write-Host 'Creando el entorno virtual en ..\.venv...'
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv $rutaEntorno
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv $rutaEntorno
    }
    else {
        throw 'Instala Python 3.10 o superior y vuelve a ejecutar este script.'
    }
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $pythonProyecto)) {
        throw 'No se pudo crear el entorno virtual. Comprueba tu instalacion de Python.'
    }
}

Write-Host 'Instalando las dependencias del proyecto...'
& $pythonProyecto -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) {
    throw 'No se pudieron instalar las dependencias. Revisa la conexion a Internet y vuelve a intentarlo.'
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
