# Navegación y comandos por teclado

## Intent
Operar las dos vistas y formularios de Metrados sin depender del mouse; descubrir comandos sin memorizar todos los atajos.

## Scope
Atajos coherentes, menú Navegar, búsqueda de partidas, buscador de comandos y ayuda F1. Conservar los atajos existentes, edición de texto, confirmaciones, cálculos y persistencia. Recordar celda por partida durante la sesión. Master por instrucción vigente; no commit automático.

## Checklist
- [x] Paneles, partidas anterior/siguiente, selección y memoria: pruebas Qt de teclado.
- [x] Buscadores y ayuda: filtro sin tildes, aceptación/cancelación, comandos disponibles.
- [x] Acciones existentes y formularios: sin atajos duplicados ni interferencias con editores.
- [x] Regresión completa, revisión visual y documentación de uso.

## Evidence
Inventario revisado: atajos de archivo, creación, jerarquía, portapapeles e historial existentes. No había cambio directo de paneles, recorrido de partidas ni ayuda unificada. Repositorio limpio al empezar.

2026-09-27: suite completa, **263 pruebas OK en 38,713 s**. Incluye 25 pruebas nuevas con QTest y motor real. Se verificaron F6, Ctrl+1/2, Enter/Esc, Ctrl+RePág/AvPág, Shift+Espacio, Ctrl+Inicio/Fin, Ctrl+L, accesos a formularios, edición confirmada antes de cambiar de panel y Ctrl+Z textual sin interferencias. El registro compartido no contiene combinaciones duplicadas.

Se probaron búsquedas modales reales: Ctrl+F → escribir «areas» sin tilde → Enter abre ÁREAS; Ctrl+K → «bajar» → Enter mueve una fila y Ctrl+Z la devuelve. Sin coincidencias o con comandos desactivados no se ejecuta ninguna acción. Esc cierra el buscador; se restaura el foco anterior, incluido el nombre de la obra. Un primer test detectó falta de reactivación inmediata al cerrar el diálogo; se corrigió la restauración de foco y se comprobó con el ciclo de eventos de Qt.

La memoria usa identidades de filas, no posiciones: resiste reordenación y deshacer. Se probaron partidas vacías, títulos seleccionados, grupos contraídos, extremos sin vuelta circular y apertura de otra obra. No se modificaron fórmulas ni formato de archivos.

Capturas offscreen al 125 % revisadas: metrado_shortcuts_commands_final.png, metrado_shortcuts_help_final.png y metrado_shortcuts_find.png en el directorio temporal de Windows. Buscadores legibles, filas de 28 px, ayuda filtrable y botones visibles. Se documentaron todos los accesos en LEEME-Metrados.md. Git diff --check sin errores; solo avisos de conversión LF/CRLF.

## Next
Probar F6, Ctrl+F y Ctrl+K en una obra real. Cambios en master, sin commit; generar commit solo si el usuario lo solicita.
