# Corregir módulo nativo de cálculo

## Intent
Recompilar el enlace Rust/Python de Metrados para que coincida con Python 3.11 y mantener encabezados contextuales claros para metrados de acero.

## Scope
Incluye la reconstrucción del paquete local `metrado`, la verificación de importación del módulo `_enlace` y el ajuste de etiquetas de la tabla para acero. No cambia la lógica de cálculo ni la cantidad de columnas.

## Checklist
- [x] Recompilar `metrado` con el intérprete Python del entorno virtual; prueba: `uv sync --reinstall-package metrado` termina correctamente.
- [x] Verificar el módulo nativo; prueba: `uv run python -c "import metrado._enlace"` termina sin `ImportError`.
- [x] Actualizar las etiquetas contextuales de acero; prueba: la selección de una partida `kg` muestra `Gancho inicial`, `Empalme`, `Diámetro` y `kg/m` en las mismas columnas.
- [ ] Verificar el arranque de la aplicación; prueba: pendiente de ejecución interactiva.

## Evidence
- 2026-09-26: `uv sync --reinstall-package metrado` reconstruye e instala `metrado==0.1.0` correctamente.
- 2026-09-26: `uv run python -c "import metrado._enlace as e; print('ENLACE_OK', e.__file__)"` devuelve `ENLACE_OK` y carga `_enlace.cp311-win_amd64.pyd`.
- 2026-09-26: inspección del binario confirma dependencia `python311.dll`; antes dependía incorrectamente de `python312.dll`.
- 2026-09-26: `uv run pytest -q` no pudo recolectar pruebas porque `pytest` se ejecutó fuera del entorno del paquete y no encontró `metrado`; no indica un fallo del módulo nativo.
- La rama no pudo crearse porque los permisos del entorno no permiten escribir referencias bajo `.git/refs/heads`.
- 2026-09-26: `uv run --with pytest python -m pytest app/tests/test_sheet.py -q` pasa con `36 passed`.
- 2026-09-26: se elimina el reajuste a `STEEL_WIDTHS`; las 14 columnas conservan siempre `WIDTHS` al cambiar entre partidas normales y de acero.
- 2026-09-26: la misma prueba vuelve a pasar con `36 passed` después del ajuste de anchos.

## Next
Ejecutar `uv run metrado` desde una terminal interactiva y confirmar visualmente los encabezados contextuales de acero.
