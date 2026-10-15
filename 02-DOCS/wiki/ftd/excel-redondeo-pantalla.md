# Excel de valores con los 2 decimales de la planilla

## Intent

En **Exportar metrados a Excel (solo valores)**, cada total y cantidad calculada debe verse con los mismos 2 decimales que Metrados (343,21), no con el redondeo de Excel (343,22).

## Scope

- En: redondear los números que escribe `_formula` cuando `formulas=False`, con `format(valor, '.2f')` como la planilla.
- Fuera: cambiar el motor, el redondeo en pantalla, o las fórmulas de la otra exportación.

## Checklist

- [x] Prueba roja: un total interno 343,2149 sale 343,21 en el XLSX de valores, no 343,2149.
- [x] `_formula` aplica ese redondeo solo en modo valores; Pendiente y textos no se tocan.
- [x] La exportación con fórmulas y el FE 0,80 en valores siguen verdes.

## Evidence

2026-10-15: `test_values_export_matches_planilla_two_decimals` falló con `343.2149 != 343.21`. Tras `display_round` en `_formula` (solo `formulas=False`), esa prueba y el FE 0,80 (2332,22) pasaron. Suite `app.tests.test_excel_export`: **32 pruebas OK** en 5,062 s.

## Next

Cerrar Metrados, volver a abrir y **Archivo → Exportar metrados a Excel (solo valores)…**. Comprobar que `02.02.01.02` sale 343,21.
