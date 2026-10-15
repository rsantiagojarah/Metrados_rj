@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Instalar-Metrados.ps1" %*
echo.
if errorlevel 1 (
  echo La instalacion no termino. Revisa el mensaje de arriba.
) else (
  echo Listo. Abre Metrados y despues AutoCAD 2021.
)
pause
