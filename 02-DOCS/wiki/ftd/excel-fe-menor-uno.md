# Excel: FE menor que 1 deja Pendiente

## Intent

Al exportar a Excel, un factor de esponjamiento entre 0 y 1 (0,80 / 0,20) debe mostrar el volumen prorrateado, igual que en Metrados, no **Pendiente**.

## Scope

- En: la fórmula de la línea FE en `excel_export.py` y una prueba con 0,80 y 0,20.
- Fuera: el cálculo en pantalla (ya correcto), el diálogo, o un comando distinto de prorrateo.

## Checklist

- [x] Reproducir: FE 0,80 exporta fórmula con `J>=1` y el total de partida queda Pendiente al recalcular.
- [x] Prueba roja: 2 915,28 m³ × 0,80 y × 0,20 no salen Pendiente; la fórmula exige `J>0`.
- [x] Arreglo: la línea FE admite el mismo mínimo que el programa (`FE > 0`).
- [x] Prueba verde y suite de Excel sin regresiones de FE ≥ 1.

## Evidence

2026-10-15: la prueba falló con `J14>=1` en la fórmula. Excel recalcula al abrir y convierte 0,80 en Pendiente.

2026-10-15: `J>=1` → `J>0`. `test_fe_below_one_exports_prorated_volume_not_pending` y las otras 3 de FE en verde. Suite `app.tests.test_excel_export`: **30 pruebas OK** en 4,947 s. 2 915,28 × 0,80 = 2 332,224 y × 0,20 = 583,056.

## Next

En Metrados, volver a **Archivo → Exportar metrados a Excel…** y abrir el archivo nuevo (el .xlsx anterior no se actualiza solo).
