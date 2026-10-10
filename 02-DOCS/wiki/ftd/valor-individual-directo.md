# Valor individual de área y volumen directos

## Intent
Mostrar ÁREA o VOLUMEN en Largo y el valor individual en Ancho cuando se aplica Cantidad directa.

## Scope
Valor de solo lectura, modificado desde Cantidad directa. Conservar Metrado → Área para volumen por área y dimensión. Reflejar la presentación en Excel.

## Checklist
- [x] Comprobar etiquetas, valor exacto, solo lectura y actualización desde Cantidad directa.
- [x] Verificar factores, deshacer y volumen por área.
- [x] Verificar exportación y pruebas de regresión relacionadas.

## Evidence
El valor directo ya está guardado por separado; no requiere migrar proyectos.
Las nuevas pruebas reprodujeron 3 fallos antes de la corrección y pasan después.
74 pruebas aprobadas: test_direct_display (3), test_area* (8), test_excel_export (27), test_sheet (36), ejecutadas con unittest y el motor real.
Revisión visual del widget en modo compacto: ÁREA y VOLUMEN completos, valores individuales visibles al costado y resultados correctos. Captura local en tmp/direct-display.png.
Se conserva la precisión del valor ingresado. Cambiar N.º de veces conserva la cantidad directa de m²/m³; antes la borraba.
La celda del valor individual es de solo lectura. Se conserva la edición de dimensiones existente para salir del modo directo, y Metrado → Área permanece editable para volumen por área.

## Next
Terminado. Reabrir la aplicación para usar la presentación actualizada.
