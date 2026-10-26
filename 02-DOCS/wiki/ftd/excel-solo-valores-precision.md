# Precisión numérica al exportar Excel solo con valores

## Intent

Conservar en el Excel sin fórmulas los mismos valores numéricos que intervienen en los cálculos de la planilla. Así, una revisión que multiplique los valores exportados obtiene el mismo metrado, sin pérdida por redondeo de presentación.

## Scope

- En: todas las celdas numéricas calculadas por la exportación sin fórmulas, incluidos los pesos de acero; prueba de regresión que compruebe un cálculo con decimales.
- Fuera: cambiar el aspecto o los decimales visibles de la exportación con fórmulas; alterar las reglas de cálculo del metrado; importar Excel.

## Checklist

- [x] Reproducir el redondeo actual en una exportación sin fórmulas y registrar la celda/ruta que lo introduce.
- [x] Añadir una prueba que falle si una celda calculada conserva solo los dos decimales de presentación en vez de su valor de cálculo.
- [x] Sustituir la conversión que redondea por una copia del valor calculado, manteniendo las fórmulas desactivadas.
- [x] Ejecutar la prueba nueva y la suite de exportación; el proyecto no declara un comando de verificación completo.

## Evidence

2026-10-26: `python -m unittest app.tests.test_excel_export.ExcelExportTests.test_values_export_matches_planilla_two_decimals -v` pasó y confirmó la reproducción: el valor calculado `343.2149` se guarda como `343.21`. La ruta aislada es `ExcelReport._formula`: al exportar sin fórmulas llama a `display_round(cached)`, que aplica `format(value, '.2f')` a toda celda calculada.

2026-10-26: las tres pruebas nuevas/actualizadas fallaron antes del arreglo, mostrando `2332.22 != 2332.224`, `343.21 != 343.2149` y `0.99 != 0.994413`. Después de escribir directamente el valor calculado, `python -m unittest app.tests.test_excel_export.ExcelExportTests.test_values_export_preserves_full_steel_weight_precision app.tests.test_excel_export -v` terminó correctamente: **34 ejecuciones OK**. La prueba de acero comprueba además que `longitud × peso = total` en el archivo sin fórmulas.

2026-10-26: `git diff --check` no reportó errores de espacios. `02-DOCS/wiki/sdd/config.yaml` no declara una orden de verificación global, por lo que la suite específica de exportación es la comprobación automatizada disponible para este cambio.

## Next

Validación manual opcional: exportar una planilla real como «solo valores», insertar una multiplicación entre longitud y peso de acero y compararla con el total de la misma fila.
