# Importar estructura de partidas desde Excel

## Intent
Crear una planilla desde un presupuesto Excel con ítems, descripciones y unidades, sin añadir botones a la barra.

## Scope
Archivo → Importar partidas desde Excel. Lectura XLSX, elección de hoja y vista previa; conservar códigos, nombres y jerarquía de títulos/subtítulos. Normalizar unidades conocidas e incorporar día como unidad de conteo porque aparece en el archivo de referencia. No importar precios, cantidades ni detalles, no modificar el Excel ni sobrescribir la obra abierta. Importación como nueva planilla sin guardar, tras confirmación y protección de cambios pendientes. Trabajo en master por instrucción del usuario.

## Checklist
- [x] Leer el archivo real y verificar 278 filas: 62 títulos/subtítulos y 216 partidas.
- [x] Importación validada y atómica: unidades, códigos, jerarquía, hojas, errores y límites.
- [x] Menú y vista previa sin botones nuevos en la barra; cancelar conserva la obra.
- [x] Día compatible con cálculo, referencias, edición y persistencia.
- [x] Pruebas automáticas, prueba real y revisión visual aprobadas.

## Evidence
Inspección de solo lectura del XLSX indicado: hoja SP1, encabezados Item / Descripción / Unidad en A1:C1; segunda hoja vacía. Unidades: M, M2, M3, KG, UND, MES, VJE, GLB y DIA. Todos los códigos están guardados como texto; cuatro niveles como máximo. La habilidad Spreadsheets guía la conservación de identificadores y la comprobación independiente de recuentos; no se edita ni se exporta el libro original.

Verificación 2026-09-27:

- Importador real y flujo de ventana con el archivo del usuario: **278 filas = 62 títulos/subtítulos + 216 partidas**. Conteos iguales a la extracción XML independiente. Unidades de partidas: m2 70, m3 62, m 27, und 20, glb 17, kg 12, mes 6, vje 1, dia 1. Sin detalles ni cantidades importadas; todos los totales iniciales 0, sin errores de cálculo.
- Guardado y reapertura SQLite de esa estructura en carpeta temporal: filas y cálculos idénticos. SHA-256 del Excel antes/después idéntico: `3a9d950596fd1d425ab6ab647833ee01a7b8335c3d6e415955e43f46f7411bfd`.
- Lectura inicial observada: 426 ms incluyendo carga diferida de la biblioteca; dato orientativo local. Leer Excel no añade ese coste al arranque normal de Metrados.
- `test_excel_import.py`: **19 pruebas nuevas**, incluyendo columnas reordenadas, encabezados repetidos, ceros de formato numérico, códigos decimales ambiguos, unidades desconocidas/cero, fórmulas, errores Excel, duplicados, padres ausentes, hojas vacías, límites sin truncado silencioso, archivo corrupto, cancelación, protección del historial, vista previa y persistencia. Día probado con negativos, referencias y Undo.
- Suite completa Qt con motor instalado: **363 pruebas OK, 35,844 s**, salida 0. Primera pasada detectó que la acción de menú se había incluido en la lista exclusiva de botones; se separó de esa lista, manteniéndola en Ctrl+K, y se repitió toda la suite.
- `cargo test`: **21 pruebas OK**. `uv sync` reconstruyó e instaló el motor con soporte día y las dependencias Excel; `DEFUSEDXML=True` verificado. `git diff --check` sin errores, solo avisos de finales de línea.
- Vista previa y aplicación importada renderizadas con Qt fuera de pantalla e inspeccionadas visualmente: tres columnas legibles, selector de hoja, recuentos y confirmación; barra principal sin botón de importación. El navegador vuelve al inicio para mostrar los títulos iniciales.
- Excel y obras existentes no modificados. Cambios en master, sin commit solicitado en este turno.

## Next
Reiniciar Metrados y usar Archivo → Importar partidas desde Excel para crear y guardar la obra del usuario cuando lo decida.
