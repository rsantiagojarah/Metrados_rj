# Coherencia de redondeo entre Metrados y reportes

## Intent

Hacer que las cantidades y totales que Metrados muestra a dos decimales sean los mismos que aparecen en todos los reportes Excel, incluidos los libros editables con fórmulas tras abrirlos en Excel.

## Scope

- En: un criterio único de valor visible para los resultados calculados y los totales en Desarrollo y Resumen; las exportaciones con fórmulas y solo valores deben usarlo.
- En: pruebas de regresión con 17,40 × 13,15 × 1,50 = 343,215, que hoy se muestra como 343,21 en Metrados y 343,22 al recalcularse en Excel.
- Fuera: cambios de las dimensiones ingresadas, reglas de ingeniería, importación desde Excel y precios.

## Checklist

- [x] Localizar las fórmulas y cachés que permiten que Excel aplique un redondeo distinto; prueba que reproduzca el desfase.
- [x] Aplicar la representación visible de Metrados a los resultados de los reportes, sin perder las fórmulas editables de sus entradas.
- [x] Comprobar con pruebas automatizadas que pantalla, Excel con fórmulas y Excel solo valores entregan 343,22 en el caso límite.
- [x] Ejecutar la suite de exportación y la comprobación de cambios sin errores de espacios.

## Evidence

- 2026-10-27: la prueba nueva falló inicialmente porque no existía el formateador común. Tras implementarlo, `17,40 × 13,15 × 1,50` muestra 343,22 tanto en la planilla como en Desarrollo y Resumen, con fórmulas y solo valores.
- 2026-10-27: `python -m unittest app.tests.test_direct_display app.tests.test_excel_export -v` terminó con **39 pruebas OK**. La batería relacionada de planilla, exportación, hoja y FE terminó antes con **113 pruebas OK**.
- 2026-10-27: `git diff --check` no encontró errores de espacios.

## Next

Cerrar y volver a abrir Metrados para que cargue el cambio, y exportar la misma partida de prueba para validarla visualmente en Excel.
