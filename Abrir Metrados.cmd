@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\pythonw.exe" (
  echo No se encontro el entorno de la aplicacion. Consulta LEEME-Metrados.md.
  pause
  exit /b 1
)
set "PYTHONPATH=%~dp0app"
start "" "%~dp0.venv\Scripts\pythonw.exe" -m metrado
