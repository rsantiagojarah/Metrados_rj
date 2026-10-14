# Instalar complemento AutoCAD 2021

## Intent

Compilar e instalar el paquete `Metrados.AutoCAD2021.bundle` en el directorio de complementos del usuario actual para que AutoCAD 2021 cargue `MTRCONEXION`, `MTRAREA`, `MTRLONGITUD` y `MTRACERO`.

## Scope

- En: ejecutar `autocad/Metrados.AutoCAD2021/install.ps1` con AutoCAD cerrado.
- Fuera: firmar el binario, cambiar `SECURELOAD`/`TRUSTEDPATHS`, comprobar `MTRCONEXION` dentro de AutoCAD (requiere sesión interactiva).

## Checklist

- [x] Compilar e instalar el bundle; prueba: el script imprime la ruta de destino y el SHA256, y el DLL existe en `%APPDATA%\Autodesk\ApplicationPlugins\Metrados.AutoCAD2021.bundle`.

## Evidence

2026-09-28: el disco C: estaba en 0 bytes libres; se liberaron ~854 MB vaciando temporales del usuario (`%TEMP%`). AutoCAD no estaba en ejecución. `install.ps1` compiló e instaló sin error.

- Complemento: `target\autocad\Metrados.AutoCAD2021.bundle\Contents\Windows\Metrados.AutoCAD2021.dll`
- Instalado en: `C:\Users\CARMEN\AppData\Roaming\Autodesk\ApplicationPlugins\Metrados.AutoCAD2021.bundle`
- SHA256 coincidente (compilado e instalado): `3D70AB68073604B4E273B51F10893A4DF354694EA51AB00A4D04ED8261008CF7`
- DLL instalada: 35840 bytes, 28/09/2026 09:08:33
- Manifiesto registra `MTRCONEXION`, `MTRAREA`, `MTRLONGITUD` y `MTRACERO`

No se pudo ejecutar `MTRCONEXION` aquí: hace falta abrir Metrados y AutoCAD 2021 a mano.

## Next

Abrir Metrados, luego AutoCAD 2021, aceptar la carga si lo pide, y escribir `MTRCONEXION`.
