# Área con dos dimensiones elegibles

## Intent
Permitir largo × ancho, largo × alto o ancho × alto en los detalles de m².

## Scope
Edición en plantilla, cálculo, persistencia y fórmulas de Excel. Conservar el contrato del motor: enviar las dos medidas seleccionadas como los dos lados del rectángulo.

## Checklist
- [x] Aceptar las tres parejas y rechazar una o tres dimensiones; comprobar con el motor real.
- [x] Conservar dimensiones al guardar y generar Excel con las mismas reglas.
- [x] Ejecutar las pruebas de regresión.

## Evidence
La plantilla restringe m² a columnas 4 y 5; Excel también toma únicamente esas columnas.
Las pruebas nuevas reprodujeron la restricción antes de modificar el código (5 fallos y 2 errores en subcasos).
Tras la corrección, los 3 casos de prueba pasan: parejas, factores, deshacer, datos inválidos, guardado y fórmulas/caché de Excel.
La suite completa (`.venv/Scripts/python.exe -B -m unittest discover -s app/tests`, comprobación automatizada de la aplicación) ejecutó 449 pruebas en 284,151 segundos: OK.
`git diff --check`, revisión de espacios del cambio, terminó sin errores.

## Next
Corrección terminada. Reabrir la aplicación para utilizar las tres columnas de dimensiones en m².
