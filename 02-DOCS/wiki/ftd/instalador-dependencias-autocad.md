# Instalador de dependencias y complemento AutoCAD

## Intent

Un solo paso deja este proyecto listo para usarse: instala lo que falte del entorno, sincroniza las dependencias con uv y copia el complemento para que AutoCAD 2021 cargue `MTRCONEXION`, `MTRAREA`, `MTRLONGITUD` y `MTRACERO`.

## Scope

- En: `installer/Instalar-Metrados.cmd` y `installer/Instalar-Metrados.ps1`. Comprueban AutoCAD 2021, espacio libre y que AutoCAD y Metrados estén cerrados. Si Windows PowerShell no puede calcular SHA256, el script sigue en PowerShell 7. Si faltan uv, Python 3.12 o Rust, los instalan para el usuario actual. `uv sync --frozen` instala la plantilla y el módulo de cálculo. Se reutiliza `autocad/Metrados.AutoCAD2021/install.ps1`. Crea accesos directos en el escritorio y el menú Inicio.
- Fuera: un instalador gráfico para un equipo que no tiene este repositorio. Firmar el binario. Cambiar `SECURELOAD` o `TRUSTEDPATHS`. Instalar AutoCAD. Comprobar `MTRCONEXION` dentro de AutoCAD.

El instalador es un script de preparación, no un segundo programa: Metrados sigue abriéndose desde este proyecto. Un ejecutable aparte exigiría enmendar la constitución, y la spec de empaquetado dejó fuera el instalador para quien no tiene el proyecto.

## Checklist

- [x] Rechaza una ruta de AutoCAD que no existe; prueba: el script termina con error en español y el complemento ya instalado no cambia.
- [x] Rechaza la instalación si AutoCAD o Metrados están abiertos; prueba: con esos procesos en marcha, el script termina con error y el complemento no cambia.
- [ ] Con las aplicaciones cerradas, instala dependencias y el complemento; prueba: imprime `ENLACE_OK`, el SHA256 de la DLL compilada coincide con la de `%APPDATA%\Autodesk\ApplicationPlugins\Metrados.AutoCAD2021.bundle` y existen los dos accesos directos.

## Evidence

2026-10-15: AutoCAD 2021 y Metrados estaban abiertos (`acad.exe` 20256 y 9880; `pythonw.exe -m metrado` 11880 y 9716). El instalador se lanzó con Windows PowerShell y continuó en PowerShell 7. No copió el complemento.

- Ruta `C:\no-existe-autocad`: código 1, avisó que falta `acad.exe`.
- Ruta real de AutoCAD 2021: código 1, listó los cuatro procesos y pidió cerrarlos.
- El complemento ya instalado no cambió: SHA256 `3D70AB68073604B4E273B51F10893A4DF354694EA51AB00A4D04ED8261008CF7`, 35840 bytes, 2026-09-28 09:08:33.

La instalación completa no se ejecutó porque esas aplicaciones siguen abiertas.

## Next

Cerrar AutoCAD y Metrados, y ejecutar `installer\Instalar-Metrados.cmd`.
