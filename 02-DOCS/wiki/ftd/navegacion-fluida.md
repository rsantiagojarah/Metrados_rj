# Navegación fluida de la planilla

## Intent
Evitar que un cambio de celda fuerce el repintado de toda la tabla.

## Scope
Actualizar la selección con el repintado parcial de Qt. Mantener cabecera contextual, edición, datos y fórmulas.

## Checklist
- [x] La selección entre celdas no repinta filas ajenas: prueba de pintura real.
- [x] Encabezado contextual y edición siguen funcionando: suite existente.
- [x] Comparar latencia con el diagnóstico previo.

## Evidence
Diagnóstico previo: mediana 64,3 ms por movimiento; experimento sin repintado completo 1,5 ms. Rama feat/metrado-aceros-kg.

Prueba de regresión observada fallando antes del cambio: al mover una celda se repintaban las filas visibles 1 a 20. Tras el cambio se repinta únicamente la fila de selección.
Suite: 32 pruebas aprobadas en 4,663 s; git diff --check sin errores.
Medición posterior con la misma secuencia de 64 movimientos y ventana offscreen: mediana 1,46 ms; p95 2,11 ms. La mediana anterior fue 64,3 ms. Esta comparación mide navegación dentro de acero, sin cambiar de tipo de encabezado.
Eliminada la llamada incondicional viewport().update(); el encabezado y los anchos se actualizan únicamente cuando cambia el modo de partida. Qt gestiona las áreas de selección y las columnas redimensionadas.

## Next
Reabrir Abrir Metrados.cmd para usar la navegación optimizada.
