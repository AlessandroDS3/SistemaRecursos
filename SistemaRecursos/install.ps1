$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'entorno.ps1')
$pythonProyecto = Obtener-PythonProyecto -Preparar

if (-not (Test-Path -LiteralPath $pythonProyecto)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv $rutaEntorno
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv $rutaEntorno
    }
    else {
        throw 'Instala Python 3.10 o superior y vuelve a ejecutar install.ps1.'
    }
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $pythonProyecto)) {
        throw 'No se pudo crear el entorno virtual. Revisa tu instalacion de Python.'
    }
}

& $pythonProyecto -c 'import sys; sys.exit(sys.version_info < (3, 10))'
if ($LASTEXITCODE -ne 0) {
    throw 'El entorno virtual requiere Python 3.10 o superior.'
}

& $pythonProyecto -m pip install --disable-pip-version-check -r (Join-Path $PSScriptRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) {
    throw 'No se pudieron instalar las dependencias. Revisa el mensaje de pip y la conexion a Internet.'
}

& $pythonProyecto -m pip check
if ($LASTEXITCODE -ne 0) {
    throw 'El entorno virtual tiene dependencias incompatibles. Revisa el resultado de pip check.'
}
