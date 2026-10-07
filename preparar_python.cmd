@echo off
rem Se invoca mediante CALL para compartir RECURSO_PYTHON con el iniciador.
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto verificar
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if not errorlevel 1 (
  py -3 -m venv .venv
  goto verificar
)
python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if not errorlevel 1 (
  python -m venv .venv
  goto verificar
)
set "RECURSO_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%RECURSO_PYTHON%" (
  echo Instala Python 3.10 o posterior para continuar.
  exit /b 1
)
"%RECURSO_PYTHON%" -m venv .venv
:verificar
set "RECURSO_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%RECURSO_PYTHON%" exit /b 1
"%RECURSO_PYTHON%" -c "import mysql.connector; assert mysql.connector.__version__ == '26.7.0'" >nul 2>nul
if not errorlevel 1 exit /b 0
echo Instalando el conector MySQL en el entorno del proyecto...
"%RECURSO_PYTHON%" -m pip install -r requirements.txt
exit /b %errorlevel%
