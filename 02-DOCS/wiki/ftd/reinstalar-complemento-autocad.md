# Reinstalar complemento AutoCAD 2021

## Intent
Volver a instalar el `.dll` de AutoCAD 2021 con los comandos actuales, sin cambiar el código fuente.

## Scope
- En: ejecutar `autocad/Metrados.AutoCAD2021/install.ps1` (compila y copia el bundle del usuario).
- Fuera: editar C#, Python, LISP o el manifiesto; firmar el binario; comprobar los comandos dentro de AutoCAD.

## Checklist
- [x] Compilar e instalar el bundle; prueba: el SHA256 del `.dll` compilado coincide con el de `%APPDATA%\Autodesk\ApplicationPlugins\Metrados.AutoCAD2021.bundle`, y la DLL instalada no es la del 28/09/2026.

## Evidence
2026-11-04: AutoCAD 2021 tenía abierto `5.0 ESTRUCTURAS(VC)_v2.0.dwg` y bloqueaba el `.dll` anterior (35840 bytes, 28/09/2026, SHA256 `3D70AB68073604B4E273B51F10893A4DF354694EA51AB00A4D04ED8261008CF7`). `install.ps1` compiló el paquete nuevo. Se renombró el `.dll` en uso y se copió el compilado.

- Compilado e instalado: SHA256 `174ED19183DF4744740D651D202D7E05DAA7C5C38018E1A21A5A3AA4F99E28E3` (coinciden)
- DLL instalada: 37376 bytes, 04/11/2026 15:09:36
- Comandos presentes en el binario: `MTRCONEXION`, `MTRAREA`, `MTRLONGITUD`, `MTRACERO`, `MTRDISTANCIA`
- No se ejecutaron comandos dentro de AutoCAD: la sesión actual sigue con el módulo antiguo hasta reiniciar

## Next
Guardar el DWG, cerrar AutoCAD 2021 y volver a abrirlo para que cargue el complemento nuevo. Probar `MTRDISTANCIA`.
