# Referencias actualizables entre partidas

## Intent
Referenciar el total de cualquier partida escribiendo `/` en la descripción del detalle, sin botones adicionales.

## Scope
Identidad estable, actualización encadenada, factores explícitos entre unidades distintas, cantidades con signo, persistencia, copiar/pegar y deshacer. Misma unidad: sin factor visible ni sufijo. Sin expresiones que combinen referencias. Trabajo en master por indicación del usuario.

## Checklist
- [x] Cálculo de dependencias, negativos, cero, pendientes y rechazo de ciclos: pruebas automatizadas.
- [x] Selector por `/` y formulario solo para unidades distintas: pruebas de interfaz.
- [x] Valor original, factor condicional y sufijo; columnas conservadas: verificación visual.
- [x] SQLite, JSON, copiar/pegar y Ctrl+Z: pruebas de integración.
- [x] Suite previa y motor Rust sin regresiones no previstas.

## Evidence
- 2026-09-27: 33 pruebas específicas de referencias aprobadas (motor real y QTest), incluidas cancelación, conversión, movimientos que producirían ciclos, signos, FE, fuentes eliminadas y cadenas de 1500 partidas.
- Suite completa: 312 pruebas aprobadas en 34,690 s; limpieza de objetos Qt diferidos entre pruebas. Motor Rust: 21 pruebas aprobadas mediante `cargo test --workspace`.
- Motor recompilado e instalado con `uv sync --offline --reinstall-package metrado` una vez liberado el archivo por la aplicación. No se cerró ningún proceso del usuario.
- Revisión visual de capturas Qt a escala 125 %: referencias de la misma unidad sin factor/cabecera/sufijo; unidades distintas con valor original, factor y sufijo. Selector y formulario legibles. Capturas temporales `metrado_referencia_factor.png`, `metrado_referencia_igual.png`, `metrado_referencia_busqueda.png` y `metrado_referencia_conversion.png`.
- Prueba sintética de 10 000 filas y 4999 enlaces encadenados: inicialización 97,6 ms; edición y recálculo 63,7 ms, último total −4 correcto. No incluye repintado y no es garantía para todos los equipos.
- Formatos SQLite 5, JSON 7 y portapapeles 6. Migración de SQLite 4 comprobada; guardado sin cambios conserva revisión; copias internas remapean identificadores.
- `git diff --check` sin errores. Se preservaron los cambios previos de atajos y eliminación múltiple; no se creó commit.

## Next
Probar el flujo `/` con partidas reales. El cálculo conserva todas las columnas y anchos; solo cambia sus etiquetas al seleccionar una referencia. Misma unidad: no muestra factor. Un factor existente cuya conversión ya no corresponde tras cambiar unidades deja el resultado pendiente hasta volver a confirmar mediante `/`.
