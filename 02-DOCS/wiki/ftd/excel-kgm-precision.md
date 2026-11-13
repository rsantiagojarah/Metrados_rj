# kg/m de acero en Excel sin el float binario

## Intent
En el Excel, el kg/m de filas de acero antiguas (sin tabla de la partida) deja de mostrarse como `2.23743021238989` / `########`. Debe verse con la misma precisión de seis decimales que el catálogo de referencia. Los kg del detalle no cambian.

## Scope
- En: exportación Excel (con fórmulas y solo valores) del kg/m legado; formato visible de esa columna.
- Fuera: aplicar la tabla global 2.235 a obras ya guardadas; cambiar el motor Rust; cambiar ganchos o empalmes.

## Checklist
- [x] Prueba que reproduce 3/4" legado: Excel escribe el float largo y el total sigue 311,45.
- [x] Escribir kg/m legado a 6 decimales y un formato que quepa en la columna; la prueba pasa.
- [x] Suite de exportación y de acero: sin regresiones. Catálogo 2.235 / 0.994 se sigue exportando tal cual.

## Evidence
La fila de la captura (1 × 5,00 × 0,80 × 24 Ø3/4") produce 139,20 m y 311,45 kg. Antes del cambio, kg/m en Excel era `2.237430212389888` (peso teórico de Rust). La prueba `test_legacy_three_quarter_kg_per_m_uses_six_decimals` falló con `2.237430212389888 != 2.23743`. Tras escribir el peso legado a 6 decimales y formato `0.######`, esa prueba y `test_catalog_steel_weight_is_kept_verbatim` pasaron. `python -m unittest app.tests.test_excel_export app.tests.test_steel_config -v`: **74 OK**.

## Next
Volver a exportar el Excel de la obra. Si se necesita 2.235 (tabla global), usar **Acero → Actualizar aceros de esta obra…** y exportar de nuevo; eso sí cambia los kg.
