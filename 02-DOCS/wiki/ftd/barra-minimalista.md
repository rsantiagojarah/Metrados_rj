# Barra única y pie contextual

## Intent
Dar protagonismo a Partidas y Planilla retirando la segunda fila de botones y las líneas de aclaraciones separadas.

## Scope
Una barra de acciones plana con símbolos y rótulos breves, mismos comandos y atajos. Una línea inferior contextual con ayuda, fórmulas y estado; avisos prioritarios. Mantener alineación de tablas y anchos. En ventanas pequeñas, comandos sobrantes accesibles en el desbordamiento de la barra. Master, sin commit solicitado.

## Checklist
- [x] Barra única y todos los comandos conservados, incluidos Deshacer/Rehacer de ancho estable.
- [x] Ayuda y estado en una línea inferior; errores sin ocultarlos.
- [x] Pruebas de botones, atajos, adaptación a ventanas pequeñas y alineación.
- [x] Revisión visual y suite de regresión aprobadas.

## Evidence
2026-09-27: seis pruebas nuevas en `app/tests/test_minimal_chrome.py` verifican barra única, ausencia de las etiquetas antiguas, todas las acciones representadas, botón Deshacer funcional y de ancho fijo, pie contextual con avisos temporizados, menú de desbordamiento activado mediante clic real a 900 px y alineación vertical de tablas.

Suite completa: 330 pruebas aprobadas en 54,938 s. Después del ajuste visual del botón de desbordamiento, las seis pruebas específicas volvieron a pasar (1,073 s). `git diff --check` sin errores.

Capturas Qt revisadas al 125 % en tamaños lógicos de 1536 y 900 px: `metrado_minimal_wide.png` y `metrado_minimal_narrow.png` en la carpeta temporal. Una sola barra de acciones de 38 px y pie de 24 px. A 1536 px todos los botones caben; en ventanas estrechas se usa Más acciones sin expandir la barra en otra fila. El pie recorta con puntos suspensivos y conserva el texto completo en su aviso al pasar el cursor.

Los comandos reutilizan sus QAction originales: no cambian cálculos, persistencia, selección múltiple ni atajos. Se trasladó también la aclaración F2 de la cabecera Partidas al pie. Cambios previos preservados; sin commit.

## Next
Revisar con el usuario el equilibrio visual en su tamaño habitual de ventana.
