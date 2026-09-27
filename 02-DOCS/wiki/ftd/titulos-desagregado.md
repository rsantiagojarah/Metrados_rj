# Títulos y subtítulos en el desagregado

## Intent
Agrupar mediciones dentro de una misma partida con títulos como VEREDAS y VEREDAS 2, sin convertirlos en partidas ni sumar cantidades propias.

## Scope
Grupos de detalle anidables, alta contextual, movimiento, tabulación, portapapeles, guardado y apertura. Títulos en negrita con sangría, sin ÍTEM ni valores numéricos visibles. Conservar la suma de todos los detalles de la partida, el cálculo incremental y los anchos. Trabajo en master por instrucción vigente del usuario.

## Checklist
- [x] Cálculo y cambio de unidad recorren todos los detalles, incluidos grupos anidados.
- [x] Alta, selección, Tab/Mayús+Tab, movimientos y eliminación respetan la partida propietaria.
- [x] Portapapeles y archivos preservan títulos/subtítulos, niveles y datos de medición.
- [x] Pruebas y revisión visual del caso de la imagen aprobadas.

## Evidence
Inicio sobre master, commit 6faf9f1. Se preservan cambios previos en archivos .pyc y documento codex-0-156-1.md.

- `.venv/Scripts/python.exe -B -m unittest discover -s app/tests -v`: 84 pruebas aprobadas en 43,154 s (65 anteriores y 19 nuevas).
- Caso de referencia: 24 + 37,73 × 0,06 + 129,59 × 0,06 + 141,39 × 0,06 = 42,5226 m³; encabezados sin valores propios. La interfaz muestra 42,52 en el total de partida.
- Cálculo incremental: editar una medición anidada recalcula únicamente sus cuatro detalles hermanos de partida; la otra partida no se recalcula. Compatibilidad con encabezado, diámetros y cantidades de acero verificada.
- Guardado en formato 3 cuando existen grupos internos; formatos 1 y 2 siguen siendo admitidos. Se rechazan encabezados sin partida, cantidades en encabezados y destinos de unidad incompatible.
- Verificados botones, creación contextual, Ctrl+C/V, Tab/Mayús+Tab, selección de destino, movimientos completos y eliminación con confirmación. Los grupos no consumen códigos ÍTEM. Anchos originales conservados.
- Captura Qt offscreen revisada con fuentes Segoe UI/Consolas: `metrado_desagregado_qa.png` en la carpeta temporal de Windows. Títulos y subtítulos legibles, sangría correcta y columnas numéricas vacías en los encabezados internos.
- `git diff --check`: sin errores. Uso y atajos documentados en LEEME-Metrados.md. Sin commit ni push nuevos.

## Next
Commit de cierre solicitado por el usuario junto con SQLite, deshacer/rehacer y sufijo de acero. Verificación conjunta: 135 pruebas aprobadas en 45.652 s, salida 0. Preparar el commit local en master, excluyendo cachés y el documento ajeno codex-0-156-1.md.
