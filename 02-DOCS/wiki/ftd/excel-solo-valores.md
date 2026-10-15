# Exportar Excel solo con valores

## Intent

Añadir una exportación a Excel que copie los números de Metrados, sin fórmulas. Así el archivo no se recalcula al abrirlo y un FE 0,80 no se convierte en Pendiente.

## Scope

- En: menú Archivo y paleta Ctrl+K; mismas hojas Desarrollo/Resumen y el mismo aspecto; celdas calculadas como número o «Pendiente».
- Fuera: quitar la exportación con fórmulas; importar el Excel de vuelta; PDF.

## Checklist

- [x] Prueba: el XLSX de valores no tiene celdas que empiecen por `=`; 2 915,28 × 0,80 es numérico.
- [x] `export_workbook(..., formulas=False)` escribe esos literales; la exportación con fórmulas no cambia.
- [x] Menú **Exportar metrados a Excel (solo valores)…** visible en Archivo y en Ctrl+K, sin botón extra.
- [x] LEEME indica cuándo usar cada exportación.

## Evidence

2026-10-15: `test_values_export_has_no_formulas_and_keeps_fe_below_one` y `test_menu_and_palette_only` en verde. Suite `app.tests.test_excel_export`: **31 pruebas OK** en 5,300 s. Atajos: **33 OK**.

## Next

En Metrados: **Archivo → Exportar metrados a Excel (solo valores)…** y abrir el archivo. El FE 0,80 debe verse como número.
