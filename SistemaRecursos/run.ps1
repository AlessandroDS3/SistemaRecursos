[CmdletBinding(DefaultParameterSetName = 'Completo')]
param(
    [Parameter(ParameterSetName = 'Procesador')][switch]$SoloProcesador,
    [Parameter(ParameterSetName = 'Web')][switch]$SoloWeb
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'entorno.ps1')
$pythonProyecto = Obtener-PythonProyecto
Configurar-ConexionProyecto

Push-Location $PSScriptRoot
try {
    if ($SoloProcesador) {
        & $pythonProyecto -m arranque.procesador_vencimientos
    }
    elseif ($SoloWeb) {
        & $pythonProyecto app.py --sin-procesador
    }
    else {
        & $pythonProyecto app.py
    }
    $codigoSalida = $LASTEXITCODE
}
finally {
    Pop-Location
}
exit $codigoSalida
