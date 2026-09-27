# Sufijo automático en detalles de acero

## Intent
Terminar siempre la descripción del detalle kg con cantidad y diámetro, por ejemplo `VERTICAL INTERIOR 53 Ø1"`, sin duplicar anotaciones.

## Scope
Solo filas detail kg, incluidos detalles anidados; no títulos, partidas, grupos ni otras unidades. Cantidad igual a N.º de veces visible, excluyendo elementos similares. Datos incompletos se señalan con `?`, sin inventarlos. Actualizar al editar, pegar, abrir y crear; conservar coherencia al guardar y deshacer. Mantener master y todos los cambios previos.

## Checklist
- [x] Formato único al final; prueba de entradas sin sufijo, intermedio, repetido e incompleto.
- [x] Sincronización desde cantidad/diámetro y descripción; no alterar factores al renombrar.
- [x] Alcance exclusivo, pegado, unidades, undo/redo y persistencia verificados.
- [x] Regresiones y documentación comprobadas.

## Evidence
- Suite completa: 133 pruebas, OK, 91.382 s. Después de endurecer diámetros heredados inválidos y evitar operaciones sin efecto, suite de sufijos: 17 pruebas, OK, 0.070 s, salida 0.
- Pruebas del motor real: cantidad visible sin elementos similares; factores heredados intactos al renombrar; captura de cantidades y diámetros introducidos en la descripción; sufijo único al final, incluso al pegar cantidades/diámetros distintos.
- SQLite y JSON guardan la descripción completa; normalizar al importar no modifica el archivo original. Unidades no kg y títulos/grupos permanecen intactos. Undo/redo restaura sufijo y datos como una sola operación.
- Descripciones incompletas muestran `?` sin inventar medidas, cantidades o diámetros. Descripciones canónicas sin cambios no consumen historial.
- LEEME actualizado. `git diff --check` sin errores de espacios, solo avisos LF/CRLF. Rama master, sin commit nuevo; se preservan los cambios anteriores.

## Next
Commit de cierre solicitado por el usuario. Verificación conjunta final: 135 pruebas aprobadas en 45.652 s, salida 0. Preparar el commit local en master con las implementaciones anteriores; esponjamiento sigue siendo una propuesta sin código.
