# Cambio de nivel de varias filas

## Intent
Aumentar/reducir nivel de toda la selección, en Partidas y en el desarrollo, con un solo Ctrl+Z.

## Scope
Botones, menú y atajos existentes. Conservar bloques, orden entre hermanos, identificadores y renumeración. Una selección inválida no produce cambios parciales. Sin modificar Subir/Bajar ni Mover a. Trabajo en master por indicación del usuario.

## Checklist
- [x] Operación múltiple con títulos, partidas, grupos y detalles, sin duplicar descendientes seleccionados.
- [x] Selección de ambos paneles, botones y Tab/Mayús+Tab; selección conservada para repetir la operación.
- [x] Deshacer/rehacer como una sola operación; validación atómica y referencias intactas.
- [x] Pruebas nuevas y suite completa aprobadas.

## Evidence
2026-09-27: 12 pruebas nuevas en `app/tests/test_level_selection.py`. Incluyen selección cuyo cursor está en la última fila, títulos seleccionados que deben permanecer hermanos, ancestro e hijos seleccionados simultáneamente, salida de grupos con hermanos no seleccionados, padres anidados con el mismo final, botones, Tab/Mayús+Tab, Alt+flechas, cancelación atómica, un solo Undo/Redo y referencias estables.

Suite completa: 324 pruebas aprobadas en 39,178 s, con el motor real y objetos Qt limpiados entre pruebas. `git diff --check` sin errores.

Prueba sintética de 9999 partidas seleccionadas en 10 000 filas: aumentar nivel 114,3 ms y reducir 137,0 ms, con orden y jerarquía verificados. Tiempo de la operación pura, sin repintado; no es garantía para otros equipos.

Se compartió la lectura de selección con Eliminar, se actualizó la habilitación de acciones según toda la selección y se evitó emitir una actualización de acciones por cada fila al restaurarla. Cambios previos preservados, en master y sin commit.

## Next
Probar en una obra real seleccionando varias partidas o detalles y alternando Tab/Mayús+Tab; confirmar el agrupamiento esperado.
