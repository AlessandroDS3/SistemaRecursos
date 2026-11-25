$rutaEntorno = Join-Path $PSScriptRoot '..\.venv'

function Obtener-PythonProyecto {
    param([switch]$Preparar)

    $ejecutable = Join-Path $rutaEntorno 'Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $ejecutable) -and -not $Preparar) {
        throw 'Falta el entorno virtual del proyecto. Ejecuta install.ps1 primero.'
    }
    return $ejecutable
}

function Configurar-ConexionProyecto {
    $configLocal = Join-Path $PSScriptRoot 'config.local.ps1'
    if (Test-Path -LiteralPath $configLocal) { . $configLocal }

    if (-not $env:DB_HOST) { $env:DB_HOST = '127.0.0.1' }
    if (-not $env:DB_PORT) { $env:DB_PORT = '3306' }
    if (-not $env:DB_USER) { $env:DB_USER = 'root' }
    if (-not $env:DB_NAME) { $env:DB_NAME = 'prestamos_escuela_pruebas' }
    if (-not $env:DB_PASSWORD) {
        $clave = Read-Host 'Contrasena de MySQL' -AsSecureString
        $env:DB_PASSWORD = [System.Net.NetworkCredential]::new('', $clave).Password
    }
    if ([string]::IsNullOrWhiteSpace($env:DB_PASSWORD)) {
        throw 'Define DB_PASSWORD en el entorno o en config.local.ps1.'
    }
}
