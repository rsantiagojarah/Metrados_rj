# Conexión base con AutoCAD 2021

## Intent
Crear una única conexión local, segura y reutilizable entre Metrados y AutoCAD 2021 para que las futuras operaciones de distancia, acero, áreas y referencias compartan la misma infraestructura.

## Scope
Servidor de tubería local en Metrados, protocolo JSON versionado, autenticación por sesión, confirmaciones, prevención de duplicados, reconexión, diagnóstico y complemento C# para AutoCAD 2021/.NET Framework 4.8. Incluye comandos de estado y prueba de conexión; no incluye todavía mediciones, lectura de textos, áreas ni escritura de filas en la planilla. Se preservan los cambios pendientes anteriores sin incorporarlos a esta función.

## Checklist
- [x] Definir y probar el protocolo y la seguridad de sesión; prueba: casos unitarios de validación, autenticación, límites y duplicados.
- [x] Implementar el servidor local y su ciclo de vida en Metrados; prueba: conexión, reconexión, cierre limpio y exclusión de una segunda instancia.
- [x] Implementar el complemento de AutoCAD 2021; prueba: compilación contra las DLL instaladas de AutoCAD 2021 y cliente de integración.
- [x] Empaquetar instalación `.bundle` y documentar diagnóstico; prueba: estructura y manifiesto validados.
- [x] Ejecutar regresión completa y revisión de cambios; prueba: suite aprobada y `git diff --check` sin errores nuevos.

## Evidence
2026-09-27: complemento C# compilado con `AcMgd.dll`, `AcDbMgd.dll` y `AcCoreMgd.dll` de la instalación real de AutoCAD 2021; paquete limitado a R24.0/Win64. La sonda .NET se autenticó contra la tubería Python, recibió `pong` y volvió a conectarse después de detener el servidor y publicar una sesión distinta. Nueve pruebas específicas aprobadas en 3,543 s.

La aplicación real iniciada desde `metrado.__main__` publicó su descriptor temporal y aceptó al cliente .NET. Al finalizar la prueba se invalidó y retiró ese descriptor. El complemento final quedó instalado para el usuario actual en `%APPDATA%\Autodesk\ApplicationPlugins\Metrados.AutoCAD2021.bundle`. No se cambió `SECURELOAD`, `TRUSTEDPATHS` ni ningún DWG. La automatización visual de Windows no estuvo disponible, por lo que queda como comprobación manual escribir `MTRCONEXION` una vez que AutoCAD confirme la carga del binario de desarrollo sin firma.

Regresión observada: 407 pruebas Python aprobadas en 162,777 s antes de añadir la novena prueba específica de reconexión; esa prueba nueva y las otras ocho específicas aprobaron después sin cambios en la aplicación. Motor Rust: 21 pruebas aprobadas. Manifiesto XML leído correctamente, serie R24.0 confirmada y `git diff --check` sin errores en archivos modificados ya registrados; archivos nuevos revisados y compilados sin errores.

## Next
Abrir Metrados y AutoCAD 2021, aceptar la carga del complemento de desarrollo si AutoCAD lo solicita y ejecutar `MTRCONEXION`. Después, implementar `MTRDIST` sobre esta misma conexión.
