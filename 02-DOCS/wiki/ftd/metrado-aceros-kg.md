# Metrado de aceros (unidad kg)

## Intent
Cuando una partida tiene unidad `kg` (metrado de aceros), esa partida —y solo esa— usa por defecto las columnas de la planilla de estribos: elem. n°, Largo, gancho, empalme, Ø, Long., n°, kg/m, Kg y Total. Las demás partidas siguen con Largo/Ancho/Alto.

## Scope
- Motor Rust: longitud desarrollada, peso por metro según Ø y peso total. Sin fórmulas en Python.
- Encabezado y celdas editables de la planilla solo para la partida en kg.
- Cantidad directa de kg se mantiene como alternativa.
- Sin presupuesto, sin catálogo de aceros editable y sin cambiar partidas en m, m², m³ u otras unidades.

## Checklist
- [x] `Long = Largo + gancho + empalme`; `Kg = elem × Long × n° × kg/m`; gancho y empalme pueden ser 0: `cargo test`.
- [x] Ø en pulgadas o mm produce kg/m (7850 kg/m³): prueba Rust del Ø1".
- [x] Detalle kg muestra Long., kg/m y Kg; partida m² no cambia de columnas: prueba Python.
- [x] Al elegir unidad kg, el encabezado pasa al formato de aceros; al salir, vuelve al genérico: prueba de selección.
- [x] Guardar/abrir conserva Largo, gancho, empalme, Ø y n°: prueba de persistencia.

## Evidence
Rama `feat/metrado-aceros-kg`.
`cargo test --manifest-path domain/Cargo.toml`: 9 unitarias + 12 de `calculo_partida` en verde. Incluye estribo 10,85 + 0,61 + 1,15 = 12,61 m, Ø1" ≈ 3,978 kg/m, gancho/empalme 0 y Ø 8 mm / 1 3/8".
`uv sync --reinstall-package metrado` reconstruyó el enlace.
`.venv\Scripts\python.exe -B app\tests\test_sheet.py`: 23 pruebas en verde (2,4 s). Añadidas `test_description_fills_bars_and_diameter` y `test_example_opens_on_steel_partida`. El ejemplo trae las 18 barras de la captura.
Decisión: N.º de veces vuelve a ser columna propia (no se reutiliza para el Ø). En kg el encabezado es elem. n°, DIMENSIONES (Largo, gancho, empalme, Ø, Long.), N.º de veces, METRADO (n°, kg/m, Kg) y Total. Kg = elem × Long × n° × kg/m × veces.

## Next
Cerrar Metrados si está abierto y volver a abrirlo con `Abrir Metrados.cmd`: debe entrar ya en `01.02.02.03 ESTRIBOS` con las columnas de la captura.
