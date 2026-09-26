# Timeout del hook de memoria

## Intent
Corregir el aviso repetido «hook timed out after 5s» conservando la memoria de sesión y sus límites actuales.

## Scope
Únicamente el cálculo de huellas en .rsc/session-memory-core.mjs, su prueba y documentación. Sin cambios en Metrados, Gitbin, permisos de hooks ni límites de espera.

## Checklist
- [x] Reproducir el hook real con timeout de 5 segundos.
- [x] Ejecutar prueba de regresión antes y después de la corrección.
- [x] Sustituir Git por archivo por hashing en lote preservando resultados.
- [x] Verificar hooks reales y tiempos repetidos.

## Evidence
Reproducción directa del adaptador codex request: ETIMEDOUT, 5010 ms, sin salida. Hay 886 archivos sin seguimiento. fingerprintFiles invoca git hash-object una vez por archivo y capture realiza dos snapshots. El diagnóstico rsc 2.0.15 confirma hooks de memoria conectados y versión instalada vigente.
Prueba de regresión .rsc/tests/session-memory-performance.test.mjs: falló antes con ETIMEDOUT; pasa después. Usa 900 archivos, rutas con espacios/acentos/guion inicial, archivo vacío, binario y eliminado. Compara huellas contra Git y verifica que una edición se cuenta una sola vez.
Corrección: git hash-object --no-filters --stdin-paths en lotes de 1024, con escapado de rutas y aislamiento de archivos fallidos. Los archivos ausentes mantienen huella null. Se elimina el snapshot duplicado de capture, reutilizando la lectura inicial cuando corresponde al mismo HEAD.
Mediciones de la prueba aislada después: request 673 ms, edit 615 ms, turn 644 ms.
Verificación de los comandos commandWindows reales mediante PowerShell -NoProfile, desde domain/src: dos rondas de los siete handlers; 14/14 terminan con código 0 y JSON válido. Tiempos 1298–2588 ms; SessionEnd 1788 y 1311 ms, bajo su límite de 3 s. Los demás mantienen 5 s.
node --check y git diff --check pasan. No se cambió hooks.json, su confianza, sus eventos ni los límites. La memoria continúa activa.
Fuente de contrato del hook: https://learn.chatgpt.com/docs/hooks (entrada JSON por stdin, timeout en segundos y commandWindows).
La corrección es local sobre el archivo materializado por rsc 2.0.15; una regeneración futura del harness debe conservarla o incorporar una versión que resuelva el mismo problema.

## Next
Continuar el trabajo normal; si reaparece, registrar el evento concreto. Para verificar una actualización futura: node --test .rsc/tests/session-memory-performance.test.mjs.
