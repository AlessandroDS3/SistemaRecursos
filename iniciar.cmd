@echo off
setlocal
cd /d "%~dp0"
call preparar_python.cmd
if errorlevel 1 goto fin
if not exist config.ini (
  echo Primero configura la conexion a tu servidor MySQL.
  "%RECURSO_PYTHON%" configurar_mysql.py
  if errorlevel 1 goto fin
)
"%RECURSO_PYTHON%" server.py %*
:fin
pause
