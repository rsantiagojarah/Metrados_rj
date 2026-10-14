# Omitir empalmes

## Intent
El largo que el usuario ya midió (con empalmes incluidos) no debe volver a sumar empalmes. El cálculo por tramos de 9 m sigue siendo el valor inicial; una acción sobre la selección puede dejar la columna Empalme en 0 y restaurarla después.

## Scope
Detalles de acero en kg, con deshacer, guardado SQLite y fórmula de Excel. No cambia el catálogo global, los muros ni las filas antiguas hasta que el usuario aplique la acción. No es un editor libre de la columna Empalme.

## Checklist
- [x] Un detalle de más de 9 m con empalmes omitidos usa solo largo y ganchos; prueba: `dimensions` y el modelo dejan el empalme en 0 y el peso baja.
- [x] Volver a calcular y reaplicar ganchos conserva la elección; prueba: el empalme sigue en 0 tras aplicar ganchos y Ctrl+Z restaura el estado anterior.
- [x] Una obra anterior sin la columna se abre calculando empalmes y, al guardar la omisión, la recupera; prueba: lectura en esquema 7 y relectura en esquema 8.
- [x] Excel deja el empalme en 0 cuando la fila lo omite; prueba: la fórmula mira la marca y el valor cacheado es 0.

## Evidence
Python 3.12, `python -B -m unittest` sobre `tests.test_steel_config` y `tests.test_excel_export`: las seis pruebas nuevas y la de empalmes automáticos terminaron OK en 0,410 s. Incluyen empalme 0 por encima de 9 m, peso menor, ganchos que no reactivan el empalme, tres deshacer que restauran la fila, esquema 7 que sigue calculando hasta guardar la omisión en esquema 8, y Excel con `U=0` y caché 0. La regresión de atajos, barra y base histórica: 65 pruebas OK en 13,625 s. Antes, el lote de acero, Excel, muros, referencias y esponjamiento: 157 pruebas OK; dos módulos no arrancaron en ese lote solo por la forma de invocarlos y después sí pasaron dentro de los 65.

## Next
Probar en la planilla: seleccionar el detalle, Empalmes…, No considerar empalmes.
