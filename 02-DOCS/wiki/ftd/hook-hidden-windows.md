# Consolas auxiliares ocultas

## Intent
Evitar que los procesos auxiliares de la memoria de Codex abran consolas e interrumpan el escritorio.

## Scope
Inicialmente, lanzamientos de Git en .rsc/session-memory-core.mjs y prueba de regresión. Ampliación autorizada explícitamente por el usuario el 2026-09-26: pausar temporalmente solo los hooks de memoria del proyecto, conservando una copia exacta. No cambiar Gitbin, Metrados, perfiles de PowerShell, permisos ni hooks de otras fuentes.

## Checklist
- [x] Inspeccionar lanzamientos y perfiles de PowerShell.
- [x] Reproducir mediante instrumentación sin mostrar consolas al usuario.
- [x] Aplicar la opción de ventana oculta a todos los procesos del módulo.
- [x] Verificar la prueba nueva y la de rendimiento existente.
- [ ] Respaldar los siete handlers y retirarlos de la configuración activa del proyecto.
- [ ] Comprobar JSON y respaldo, y ejecutar una única instrucción de prueba.
- [ ] Confirmación visual del usuario: no aparecen ventanas.

## Evidence
El helper git() no establece windowsHide; hashBatch sí. Los perfiles inspeccionados no contienen lanzamientos automáticos Start-Process. La inspección puntual de procesos no identifica por sí sola el origen de una ventana fugaz. La prueba registrará opciones originales, pero forzará lanzamientos ocultos para no provocar la interrupción durante el diagnóstico.

Prueba RED: session-memory-windows.test.mjs falla porque 24 lanzamientos del helper carecen de windowsHide. Corrección mínima: windowsHide: true en git(). Prueba GREEN: 27/27 lanzamientos de captura y recuperación solicitan ocultamiento; se conserva la memoria y el conteo de ediciones. La prueba de rendimiento con 900 archivos también pasa: request 870 ms, edit 915 ms, turn 884 ms. Ambas pruebas: 2 aprobadas, 0 fallos. No se alteraron hooks.json ni sus permisos.

Límite: se verificaron las opciones enviadas a procesos reales de Git, no una captura visual del foco de Windows. Esto no prueba que el proceso PowerShell padre creado por Codex esté oculto. La corrección local debe conservarse al regenerar el harness.

## Next
El usuario confirmó varias ventanas tras Write-Output con login:false. El sondeo observó pwsh PID 3580, padre Codex 4400, ejecutando session-memory-adapter con -NoProfile -Command; la corrección interna no oculta el PowerShell padre. La captura no prueba que todas las ventanas procedan del hook.
Pausar únicamente los siete handlers de memoria con respaldo .codex/hooks.memory-paused-20260926.json.bak y configuración activa hooks vacía. Conservar memoria almacenada y confianza existente. No reactivar automáticamente mediante rsc repair/sync: la pausa es una decisión explícita del usuario. Si la sesión retiene configuración anterior, recargar Codex antes de otra prueba. Restauración futura: recuperar hooks.json desde la copia, previa autorización.
