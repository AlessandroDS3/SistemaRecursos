param(
    [ValidateSet('Comprobar', 'Sanciones', 'Cierre', 'Horario', 'ReglasPrestamo')]
    [string[]]$Paso = @('Comprobar')
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'entorno.ps1')
$pythonProyecto = Obtener-PythonProyecto
Configurar-ConexionProyecto

$modulos = @{
    Comprobar = 'arranque.comprobar_esquema'
    Sanciones = 'arranque.esquema_sanciones'
    Cierre = 'arranque.esquema_cierre'
    Horario = 'arranque.esquema_horario'
    ReglasPrestamo = 'arranque.esquema_reglas_prestamo'
}

Push-Location $PSScriptRoot
try {
    foreach ($actual in $Paso) {
        & $pythonProyecto -m $modulos[$actual]
        if ($LASTEXITCODE -ne 0) {
            throw "Fallo el paso $actual. Revisa el mensaje anterior."
        }
    }
}
finally {
    Pop-Location
}
