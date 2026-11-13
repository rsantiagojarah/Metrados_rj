# Tabla de aceros única en planilla y Excel

## Intent
El kg/m, el gancho **base** y el empalme usan siempre la tabla global del programa. Sin ganchos aplicados la columna queda en 0; un gancho personalizado se conserva.

## Scope
- En: kg/m; longitud de un empalme (regla de 9 m); gancho de tabla si el usuario aplicó 1 o 2 y no escribió otro.
- Fuera: omitir empalmes a mano; ganchos personalizados; filas antiguas sin `steel_hooks` (siguen las celdas escritas).

## Checklist
- [x] Prueba: copia 0.10/9 y tabla 0.23/0.70 → gancho 0.23 y empalme 0.70; sin aplicar gancho = 0; override 0.31 se conserva.
- [x] Planilla y Excel sincronizan esas celdas al guardar la tabla.
- [x] Suites de chapa, acero y Excel en verde.

## Evidence
`test_hook_base_and_laps_come_from_program_table`: tabla 0.23/0.70 gana a la copia 0.10/9; override 0.31 se conserva; count=0 deja gancho 0 y empalme 0.70. `test_applied_hooks_use_table_and_custom_hook_is_kept`: aplicar 1 gancho escribe 0.50 de la tabla; 2 × 0.31 = 0.62; empalme 0.70. `test_saving_table_updates_laps_and_keeps_zero_hooks`: guardar lap 1.50 actualiza la columna y el gancho sigue en 0. `test_excel_hook_base_and_laps_use_program_table`: Excel F=0.23 y G=0.70. `uv run python -m unittest app.tests.test_excel_export app.tests.test_steel_config app.tests.test_sheet app.tests.test_steel_suffix app.tests.test_references`: **167 OK**.

## Next
Commit si lo pides. Actualizar aceros sigue sirviendo para partidas antiguas sin ganchos automáticos.
