# Rendimiento de planillas grandes

## Intent
Eliminar el trabajo repetido observado en selección, referencias y guardado de acero, sin cambiar resultados ni comportamiento de la obra.

## Scope
Selección por rangos y filas visibles; grafo de dependencias reutilizable con recálculo de partidas afectadas; instantáneas de acero compartidas e inmutables para evitar copias y validaciones repetidas. Preservar SQLite, formatos anteriores, Ctrl+Z, conversiones, FE y protección de obras anteriores. Trabajo en master, sin commit solicitado.

## Checklist
- [x] Selección visible sin enumerar todas las celdas ocultas; pruebas de eliminación, nivel, ganchos, FE y copiar.
- [x] Recálculo incremental equivalente al completo en ediciones, unidades, pendientes, cadenas y Undo/Redo.
- [x] Guardado de acero con menos copias/validaciones; persistencia y aislamiento de instantáneas verificados.
- [x] Benchmark reproducible, comparación con diagnóstico previo y suite completa aprobada.

## Evidence
Diagnóstico anterior, 10 000 filas: selección 0,9–3,3 s; guardado inicial acero 4,2–4,5 s y un cambio 2,8 s. Edición ajena a una única referencia: 9902 cálculos en 59 ms frente a 100 cálculos en 1,4 ms sin referencias. Medidas sintéticas, no garantías universales.

Verificación 2026-09-27:

- Suite completa con motor Rust instalado y Qt `offscreen`: **344 pruebas, OK, 64,883 s**, salida 0. Se liberan los objetos Qt pendientes entre pruebas.
- `test_performance_paths.py`: 14 regresiones nuevas. Ctrl+A real selecciona únicamente los 99 detalles visibles de 10 000 filas, en un rango; se comprueba que las acciones no llamen a `selectedIndexes`. Cadenas, dependencias en diamante, pendientes, unidades, negativos, FE, eliminación de origen y Undo/Redo equivalen al cálculo completo.
- Catálogos idénticos comparten una instantánea inmutable validada, también en el historial. Versiones distintas permanecen separadas; modificar valores globales no modifica las instantáneas. Lectura/escritura SQLite y JSON conservan resultados. No se modifica el esquema SQLite 5 existente ni se deduplican registros en disco.
- `git diff --check`: sin errores de espacios; avisos habituales LF/CRLF. Rama `master`, respetando la instrucción del usuario. Sin commit.

Dos ejecuciones de `.venv\Scripts\python.exe -B app/tests/benchmark_performance.py`, que mide ventanas de 100 partidas × 99 detalles (10 000 filas), con procesamiento de eventos y repintado Qt fuera de pantalla. Archivos exclusivamente temporales. Edición, Undo, cambio de partida y selección: mediana de cinco operaciones por ejecución. Apertura y guardado: una operación por ejecución. Tabla con rangos entre ambas ejecuciones, en milisegundos:

| Caso | Edición | Ctrl+A | Primer guardado | Reabrir | Guardar un cambio |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ordinario | 24,8–25,2 | 38,7–40,5 | 295–305 | 106–111 | 199–214 |
| Una referencia, edición ajena | 24,9–54,8 | 34,9–117,0 | 500–501 | 102–142 | 222–226 |
| 99 partidas referencian al origen editado | 98,7–109,5 | 34,8–35,3 | 262–484 | 122–145 | 225–238 |
| Acero gestionado por catálogo | 26,9–33,7 | 39,6–47,8 | 1385–2502 | 482–543 | 714–996 |

La edición ajena calcula 99 detalles, no todo el proyecto. En el caso donde 99 partidas dependen del origen editado se conservan los 10 098 productos necesarios: no se omiten dependencias para aparentar rapidez. El guardado de acero aún procesa 90 000 registros del catálogo; es síncrono y puede tardar segundos en el límite de filas. La variación de disco/sistema es visible entre ejecuciones. No se promete latencia constante ni se equipara el repintado fuera de pantalla con la latencia de un monitor físico.

También se repitió `benchmark_storage.py`, sin repintado: edición 0,561 ms, Undo 0,467 ms, Redo 0,466 ms, primer guardado 339 ms, lectura 103 ms, guardar un cambio 207 ms. Antes: 1,111 / 0,975 / 0,952 / 384 / 111 / 214 ms, respectivamente. Los datos sintéticos del diagnóstico UI anterior y del nuevo script tienen estructura y tamaño comparables, pero no constituyen un ensayo controlado con idéntico estado del sistema.

## Next
Probar una obra real con la aplicación reiniciada y confirmar la fluidez percibida. Si el guardado de acero al límite de filas sigue siendo molesto, medir un guardado en segundo plano como mejora separada, sin alterar la protección de obras ni la concurrencia SQLite.
