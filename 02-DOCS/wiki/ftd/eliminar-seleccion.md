# Eliminar varias filas seleccionadas

## Intent
Corregir Eliminar para operar sobre toda la selección del panel activo, no solo la celda actual.

## Scope
Filas consecutivas y separadas, partidas/títulos con descendientes sin duplicados, confirmación con cantidad real y una operación de deshacer. No borrar filas ocultas de otras partidas por una selección de la planilla. Conservar los cambios pendientes de atajos y trabajar en master.

## Checklist
- [x] Reproducir selección múltiple ignorada en una prueba Qt.
- [x] Corregir cálculo de filas y selección posterior, también clic derecho.
- [x] Probar cancelar, deshacer/rehacer, grupos, FE y teclado.
- [x] Ejecutar regresiones y documentar.

## Evidence
2026-09-27: reproducción previa en Qt offscreen mediante test_delete_selection.py: seleccionar detalles 4 y 5 y eliminar dejaba 10 filas, en lugar de 9 (`AssertionError: 10 != 9`). Causa confirmada: remove_row utilizaba únicamente table.currentIndex(), sin consultar selectedIndexes/selectedRows.

La corrección toma las filas del panel activo, excluye filas ocultas de otras partidas, reúne subárboles sin duplicar descendientes y confirma la cantidad real. Un comando de historial elimina todo el conjunto. El foco permanece en una fila vecina de la misma partida o en la partida vaciada. Clic derecho dentro de una fila seleccionada conserva las demás filas.

Las regresiones detectaron una segunda causa relacionada: después de Ctrl+C, seleccionar una celda desde navegación podía sumar la selección anterior al quedar Ctrl activo en el evento. Prueba aislada roja: se seleccionaba {4,5} en vez de {5}. SheetView.setCurrentIndex ahora usa explícitamente ClearAndSelect, como el árbol; la selección real por Ctrl+clic y Mayús+flechas sigue funcionando (prueba con eventos Qt).

Verificación final: **279 tests OK en 64,353 s**, incluidos 16 nuevos. Cubren selección consecutiva y separada, títulos y descendientes, múltiples partidas, selección oculta, partida oculta como cursor con detalles visibles seleccionados, cancelación, cero selección, eliminación completa, FE parcial, deshacer/rehacer, Ctrl+A/Ctrl+Supr, selección con mouse y teclas, y menús contextuales reales mediante QTimer.

Git diff --check sin errores (solo avisos LF/CRLF). Documentación de uso en LEEME. Se conservaron los cambios pendientes de atajos y la caché de Python preexistente; no se borraron obras ni archivos del usuario.

## Next
Probar selección múltiple → Eliminar o Ctrl+Supr → Ctrl+Z en una copia de trabajo. Master, sin commit automático.
