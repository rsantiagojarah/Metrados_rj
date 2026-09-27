# FE por bloques consecutivos de detalles

## Intent

Sustituir el esponjamiento global de partida y su resumen grande por un factor directo aplicado a uno o varios detalles consecutivos. Una línea compacta como la referencia del usuario; el total nunca suma dos veces las mediciones ajustadas.

## Scope

- Solo detalles m³ consecutivos de una misma partida, sin títulos intermedios. FE finito >= 1; entrada directa 1,20, no porcentaje. Observación opcional en el tooltip.
- Línea calculada de 28 px debajo del bloque: Lon.=FE, Área=factor, Vol.=subtotal. Resto vacío. Mantener las 14 columnas, anchos y niveles existentes.
- Varios bloques independientes; subtotal ajustado de cada bloque más volúmenes de detalles libres. Mediciones originales intactas.
- Menús/barra y doble clic para editar/quitar. Seleccionar un miembro abre su bloque; una selección múltiple permite sustituir un tramo.
- El FE se asocia a cada detalle y a una identidad de bloque: mover/eliminar/copiar no deja referencias huérfanas ni pierde factores. Si se separa un bloque, aparecen subtotales por tramo consecutivo. Nuevos detalles no heredan FE.
- SQLite esquema 3, tabla detail_swelling; migración de 1/2 al guardar, JSON 5 y portapapeles 4. Configuraciones antiguas convertidas sin pérdida de factor/observación; ajustes desactivados pasan a factor 1 y anotan el porcentaje previo. Partidas antiguas vacías retienen configuración hasta tener detalles.
- Ctrl+Z/Ctrl+Y; copiar bloques o fragmentos conserva FE con identidades independientes. El texto copiado calcula el subtotal del fragmento, no el del origen completo.
- Sin cambiar fórmulas de acero ni añadir autoguardado. Master por instrucción expresa; cachés y documento codex-0-156-1.md ajenos preservados. Commit autorizado por el usuario tras probar y aprobar la función; sin push.

## Checklist

- [x] Cálculo por bloques: 24+24 con FE 1,20=57,60; varios factores, detalles libres, pendientes, precisión y overflow.
- [x] Interfaz: selección válida, línea compacta, diálogo directo, editar/quitar, alturas y anchos constantes.
- [x] Historial/movimientos: undo/redo, inserción/eliminación, cambio de unidad, separación de bloques, copia parcial/completa.
- [x] Persistencia: esquema consultable, migraciones transaccionales, rollback y conflicto, JSON y formatos heredados; rechazo de factores mezclados antiguos/nuevos.
- [x] Manual actualizado y capturas revisadas.
- [x] Última ejecución conjunta de regresión concluida: 171 pruebas OK.

## Evidence

Estado inicial: master en 90002ea con el ajuste global anterior todavía sin commit. Esta revisión sustituye ese diseño.

- Verificación final: `.venv\Scripts\python.exe -B -m unittest discover -s app/tests -v` ejecuta la suite completa: **171 pruebas OK en 81.183 s, salida 0**.

- Primera ejecución conjunta: 169 pruebas OK en 119.249 s, salida 0.
- Después de reforzar validación de datos mezclados y portapapeles anterior: 36 pruebas específicas OK en 3.034 s, salida 0.
- Cálculo comprobado: 24+24 ajustados con 1,20 → 57,60; otro detalle 24 con 1,50 → 36,00; detalle libre 24 → total partida 117,60. Ningún subtotal se vuelve a sumar como detalle.
- Pruebas UI verifican selección múltiple, Ctrl+Z/Ctrl+Y, doble clic FE, editor restringido a la medición (no al resumen), quitar, cambio de unidad y mantenimiento de anchos personalizados.
- SQLite 1/2 se abre sin modificar bytes; se migra al guardar. Fallo inyectado revierte datos, tabla y versión. Factor solo actualiza detail_swelling, no nodes. JSON 1/4/5 y portapapeles antiguo/nuevo probados.
- Capturas offscreen inspeccionadas en carpeta temporal: metrado_fe_bloques_qa.png y metrado_fe_dialog_qa.png. Línea normal con FE / 1,20 / 57.60 y diálogo pequeño con previsualización y Quitar FE; sin BASE/FINAL.
- Rendimiento local, 10 000 filas: edición mediana 0.8255 ms, undo 0.6125 ms, redo 0.6035 ms; primer guardado 350.193 ms, reapertura 131.263 ms, guardado incremental 255.517 ms. Modelo sin repintado.
- Carga adicional con 10 000 filas y 1 000 bloques FE: inicialización 85.296 ms; edición mediana 0.556 ms. Mediciones orientativas de esta máquina, no garantías.
- git diff --check sin errores; solo avisos LF/CRLF. Ninguna obra real modificada.

## Next

El usuario confirmó «está perfecto» y solicitó el commit. Registrar código, pruebas, manual y este cierre en master, excluyendo cachés y documentos ajenos. Verificar el commit y el estado restante; sin push.
