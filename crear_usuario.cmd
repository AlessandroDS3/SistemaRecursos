@echo off
setlocal
cd /d "%~dp0"
call preparar_python.cmd
if errorlevel 1 goto fin
"%RECURSO_PYTHON%" crear_usuario.py %*
:fin
pause
