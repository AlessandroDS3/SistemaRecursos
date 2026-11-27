[CmdletBinding(DefaultParameterSetName = 'Completo')]
param(
    [Parameter(ParameterSetName = 'Procesador')][switch]$SoloProcesador,
    [Parameter(ParameterSetName = 'Web')][switch]$SoloWeb,
    [Parameter(ParameterSetName = 'Administrador')][switch]$CrearAdministrador
)

$ErrorActionPreference = 'Stop'
$rutaEntorno = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\.venv'))

function Obtener-HuellaSha256([byte[]]$contenido) {
    $sha256 = [Security.Cryptography.SHA256]::Create()
    try {
        return [BitConverter]::ToString($sha256.ComputeHash($contenido)).Replace('-', '')
    }
    finally {
        $sha256.Dispose()
    }
}

function Obtener-EjecutablePythonDelProyecto {
    $ejecutable = Join-Path $rutaEntorno 'Scripts\python.exe'
    $requisitos = Join-Path $PSScriptRoot 'requirements.txt'
    $marcaInstalacion = Join-Path $rutaEntorno 'requirements.sha256'
    $huellaEntorno = Obtener-HuellaSha256 ([Text.Encoding]::UTF8.GetBytes($rutaEntorno.ToUpperInvariant()))

    # Dos terminales pueden iniciar la web y el procesador al mismo tiempo.
    $bloqueo = [Threading.Mutex]::new($false, "Local\SistemaRecursosEntorno-$huellaEntorno")
    try {
        try { [void]$bloqueo.WaitOne() }
        catch [Threading.AbandonedMutexException] { }

        try {
            $entornoNuevo = $false
            if (-not (Test-Path -LiteralPath $ejecutable -PathType Leaf)) {
                if (Get-Command py -ErrorAction SilentlyContinue) {
                    & py -3 -m venv $rutaEntorno | Out-Host
                }
                elseif (Get-Command python -ErrorAction SilentlyContinue) {
                    & python -m venv $rutaEntorno | Out-Host
                }
                else {
                    throw 'Instala Python 3.10 o superior y vuelve a ejecutar run.ps1.'
                }
                if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $ejecutable -PathType Leaf)) {
                    throw 'No se pudo crear el entorno virtual. Revisa tu instalacion de Python.'
                }
                $entornoNuevo = $true
            }

            & $ejecutable -c 'import sys; sys.exit(sys.version_info < (3, 10))'
            if ($LASTEXITCODE -ne 0) {
                throw 'El entorno virtual requiere Python 3.10 o superior.'
            }

            $huellaRequisitos = Obtener-HuellaSha256 ([IO.File]::ReadAllBytes($requisitos))
            if ($entornoNuevo -or -not [IO.File]::Exists($marcaInstalacion) -or
                [IO.File]::ReadAllText($marcaInstalacion) -ne $huellaRequisitos) {
                & $ejecutable -m pip install --disable-pip-version-check -r $requisitos | Out-Host
                if ($LASTEXITCODE -ne 0) {
                    throw 'No se pudieron instalar las dependencias. Revisa la salida de pip.'
                }
                & $ejecutable -m pip check | Out-Host
                if ($LASTEXITCODE -ne 0) {
                    throw 'El entorno virtual tiene dependencias incompatibles. Revisa la salida de pip check.'
                }
                [IO.File]::WriteAllText($marcaInstalacion, $huellaRequisitos, [Text.Encoding]::ASCII)
            }
        }
        finally {
            $bloqueo.ReleaseMutex()
        }
    }
    finally {
        $bloqueo.Dispose()
    }
    return $ejecutable
}

function Configurar-ConexionMySqlDelProyecto {
    $configLocal = Join-Path $PSScriptRoot 'config.local.ps1'
    if (Test-Path -LiteralPath $configLocal) { . $configLocal }

    if (-not $env:DB_HOST) { $env:DB_HOST = '127.0.0.1' }
    if (-not $env:DB_PORT) { $env:DB_PORT = '3306' }
    if (-not $env:DB_USER) { $env:DB_USER = 'root' }
    if (-not $env:DB_NAME) {
        $env:DB_NAME = if ($CrearAdministrador) { 'prestamos_escuela' } else { 'prestamos_escuela_pruebas' }
    }
    if (-not $env:DB_PASSWORD) {
        $clave = Read-Host 'Contrasena de MySQL' -AsSecureString
        $env:DB_PASSWORD = [System.Net.NetworkCredential]::new('', $clave).Password
    }
    if ([string]::IsNullOrWhiteSpace($env:DB_PASSWORD)) {
        throw 'Define DB_PASSWORD en el entorno o en config.local.ps1.'
    }
}

$pythonProyecto = Obtener-EjecutablePythonDelProyecto
Configurar-ConexionMySqlDelProyecto

Push-Location $PSScriptRoot
try {
    if ($CrearAdministrador) {
        Write-Host "Crear primer administrador en $env:DB_NAME"
        $argumentosAdministrador = @(
            '--dni', (Read-Host 'DNI'),
            '--nombres', (Read-Host 'Nombres'),
            '--apellidos', (Read-Host 'Apellidos'),
            '--correo', (Read-Host 'Correo'),
            '--codigo-empleado', (Read-Host 'Codigo de empleado'),
            '--area', (Read-Host 'Area'),
            '--usuario', (Read-Host 'Nombre de usuario')
        )
        & $pythonProyecto -m arranque.inicializar_administrador @argumentosAdministrador
    }
    elseif ($SoloProcesador) {
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
