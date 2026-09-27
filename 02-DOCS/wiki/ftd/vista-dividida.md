# Navegación por partidas y planilla dividida

## Intent
Reducir el desplazamiento vertical con un árbol de títulos/subtítulos/partidas a la izquierda y el metrado de una sola partida a la derecha, sin alterar cálculos, persistencia ni reglas existentes.

## Scope
Divisor ajustable; árbol con ítem, descripción, unidad y total vivo; selección sincronizada, edición de títulos/partidas, menús y atajos en ambos paneles. Planilla original con anchos fijos y FE, acero y títulos internos intactos. Confirmar editores antes de cambiar partida; undo/redo revela la partida afectada. Conservar identidades, historial global y SQLite actual, sin migraciones ni duplicar datos. Master por instrucción del usuario; sin commit hasta que lo solicite. Cachés y documento codex-0-156-1.md ajenos quedan intactos.

## Checklist
- [x] Árbol jerárquico editable con unidades y totales que se actualizan sin reconstruirse por cada celda.
- [x] Planilla muestra solo la partida seleccionada; divisor ajustable y anchos constantes.
- [x] Crear/mover/tabular/eliminar y copiar/pegar desde ambos paneles; cambiar partida confirma edición.
- [x] Ctrl+Z/Ctrl+Y revela fila/partida afectada; guardar/abrir conserva toda la obra.
- [x] Pruebas específicas y regresiones, rendimiento, revisión visual y manual.

## Evidence
Inicio: master, commit 1c43e04, 171 pruebas aprobadas en la función anterior. Cambios ajenos: cuatro cachés y codex-0-156-1.md.

- Verificación final: `.venv\Scripts\python.exe -B -m unittest discover -s app/tests -v` ejecutó **196 pruebas OK en 248.585 s, salida 0**: las 171 previas y 25 específicas de navegación.

- Modelo del árbol mapea índices a las filas originales, sin copias de datos ni recálculos al navegar. Conserva identidades y grupos contraídos al cambiar estructura. Los cambios de celda actualizan solo los nodos afectados.
- Planilla conserva el modelo original y oculta las filas ajenas a la partida. Los índices de historial, FE, numeración y operaciones existentes no cambian. Pegado tabular del árbol mapea sus filas visibles a destinos explícitos; usa la misma validación atómica que la planilla.
- Primera suite específica: 21 pruebas OK en 19.793 s. Tras añadir protección de pegado, 24 pruebas OK en 44.479 s. Incluye edición en árbol, cambio de unidad, confirmación al navegar/guardar, FE, undo entre partidas, textos nativos, copia con descendientes, multiselección y pegado parcial inválido.
- Regresiones parciales observadas: jerarquía 29 pruebas OK; base/historial 34 pruebas OK; FE 36 pruebas OK. Las pruebas que antes pulsaban títulos en la tabla o seleccionaban rangos entre partidas se adaptan a los controles visibles actuales; cálculos y garantías se mantienen.
- Se detectó que una prueba antigua intentaba aplicar FE a filas ocultas de otra partida y abría un diálogo modal. Esa ejecución conjunta se interrumpió y se corrigió la selección de prueba para incluir un título interno visible (sigue siendo un rango inválido). La ejecución final completa terminó correctamente.
- Revisión visual: captura offscreen metrado_split_qa.png en temporal de Windows. Árbol a la izquierda, planilla de acero seleccionada a la derecha; columnas y tamaños originales, desplazamiento horizontal disponible.
- Rendimiento con 10 000 filas / 100 partidas: carga 127.058 ms; cambiar partida incluyendo repintado, mediana 26.850 ms; editar y repintar, mediana 13.295 ms. Solo 100 filas visibles; no se reconstruye todo el árbol al editar. Mediciones locales, no garantías universales.
- Manual actualizado. Ningún cambio al esquema de almacenamiento ni a las fórmulas. No se han modificado obras reales ni realizado commit/push.

## Revisión: ajuste compacto solicitado
Intención: mostrar todas las columnas útiles en la ventana de referencia sin desplazamiento horizontal. Panel izquierdo más estrecho, ocultar Ítem/Unidad/Total repetidos a la derecha, descripción adaptable y barras compactas. Mantener cantidad Und., FE, acero, historial, copia/pegado y datos originales. Los anchos responderán al tamaño disponible, nunca al tipo de partida.

- [x] Ajuste por geometría y encabezados correctos con columnas ocultas.
- [x] Copiar/pegar celdas visibles sin sobrescribir columnas ocultas.
- [x] Pruebas de tamaños, estabilidad, regresiones y revisión visual.
- [x] Actualizar manual y registrar evidencia observada.

### Decisiones
- Ajustar por ancho del panel, no por contenido ni unidad. Reservar el carril vertical evita saltos de ancho entre partidas cortas y largas.
- Modelo de 14 columnas intacto; ocultar solo 0, 2 y 13 en la vista. Encabezado agrupado omite secciones ocultas. Cantidad (12) y FE (8–10) no se ocultan.
- Copiado rectangular y pegado mapean columnas visibles. La copia de bloques sigue transportando todos los datos y metadatos.
- Descripción mínima de 160 píxeles y desplazamiento horizontal de respaldo cuando el usuario reduce excesivamente el panel o amplía columnas. No se reduce el tamaño de letra.
- Primera prueba específica: 28/29 aprobadas; se corrigió el supuesto de ancho inicial del separador y la etiqueta izquierda que imponía un mínimo excesivo. Dos pruebas antiguas de la suite general exigían los anchos originales; ahora verifican estabilidad de los nuevos anchos. Esa ejecución se interrumpió para validar de nuevo el conjunto actualizado.

## Next

### Evidencia de la revisión compacta
- Suite final completa: **200 pruebas OK, 462.359 s, salida 0**. Ejecutada con el Python del entorno, `-B`, plataforma Qt offscreen, precarga de Segoe UI/Consolas/Segoe UI Symbol de Windows y `unittest.defaultTestLoader.discover('app/tests')` con `TextTestRunner(verbosity=2)`. Son las 196 anteriores más cuatro pruebas de ajuste/columnas visibles.
- Antes de la ejecución final se adaptó también la prueba de anchos manuales: primero redimensiona el separador (reajuste esperado) y luego fija los anchos que deben sobrevivir a navegación, movimientos y undo. La ejecución anterior se interrumpió para incorporar ese supuesto correcto.
- Pruebas de 1280, 1480 y 1600 píxeles lógicos: longitud del encabezado dentro del área disponible y máximo del desplazamiento horizontal igual a cero. Cambio de partida y tipo conserva exactamente los anchos; redimensionar sí adapta la descripción.
- Revisión visual al 125 %: ventana de 1525 × 780 píxeles lógicos (captura de 1906 × 975), panel izquierdo de 320; acero y FE con todas las columnas visibles y desplazamiento horizontal cero. Capturas temporales revisadas: metrado_compact_125_steel.png y metrado_compact_125_fe.png. FE: dos detalles de 24 m³, factor 1,20, subtotal y total 57,60.
- Copia/pegado visible probado sin sobrescribir unidad oculta y con undo atómico. Regresiones de base de datos, sufijos, jerarquías, FE y teclado aprobadas. Manual actualizado; `git diff --check` sin errores (solo avisos de conversión de fin de línea).
- Cachés y documento codex-0-156-1.md ajenos preservados. No se modificaron obras reales, esquema SQLite ni fórmulas. Sin commit/push.

Entregado: guardar la obra abierta y reiniciar para cargar la vista compacta. Cambios en master, sin commit ni push; realizarlos únicamente si el usuario lo solicita.

## Revisión: desarrollo sin partida repetida

Intención y alcance: ocultar la fila de partida en el panel derecho (no borrarla del modelo), numerar desde 1 sus detalles y títulos internos, y reunir código/descripción/unidad/total en una sola línea superior. Mantener códigos ÍTEM, datos, cálculos, selección de partidas, edición, historial y FE. Trabajo en master por petición del usuario, sin commit.

- [x] Desarrollo sin fila repetida; partidas vacías conservan sus acciones.
- [x] Numeración visual local tras cambiar de partida, mover filas y deshacer.
- [x] Encabezado de una sola línea con total actualizado, sin forzar el ancho del panel.
- [x] Regresiones, revisión visual y manual actualizados con evidencia.

Evidencia:
- Suite completa: **204 pruebas OK en 37.686 s, salida 0**. Python del entorno con `-B`, Qt offscreen y fuentes Segoe UI/Consolas/Segoe UI Symbol; descubrimiento de todos los tests en app/tests. El runner procesa `QEvent.DeferredDelete` con `QCoreApplication.sendPostedEvents` al terminar cada test para liberar las ventanas cuya eliminación ya programó su teardown; no modifica las aserciones ni el código productivo.
- Cuatro nuevas pruebas: numeración local sin tocar ÍTEM/historial, numeración y títulos internos tras movimiento/undo con FE, cabecera larga de una sola línea con total vivo, y foco del desarrollo sobre una fila visible. Se extendió la prueba de partida vacía para crear su primer detalle numerado como 1.
- Primera ejecución específica: 32/33 correctas. La restante esperaba que copiar toda la tabla incluyese la partida; se actualizó para exigir solo el desagregado ahora visible (título interno y dos detalles). La suite final valida ese comportamiento y mantiene la copia completa de partidas desde el árbol.
- Revisión visual de acero y FE al 125 %, ventana lógica 1525 × 780: capturas temporales metrado_development_steel.png y metrado_development_fe.png. Acero comienza en 1 sin fila de partida; FE conserva ZANJAS y detalles numerados 1, 2, 3, con subtotal 57,60 y total en el encabezado de una línea.
- Manual actualizado. `git diff --check` sin errores; solo avisos de fin de línea. Sin cambios a fórmulas, SQLite, códigos ÍTEM ni obras reales. Cambios ajenos preservados; sin commit/push.

Siguiente: guardar la obra y reiniciar la aplicación para revisar los tres ajustes implementados en master.

## Revisión: tablas alineadas en altura

Intención y alcance: alinear el borde superior de ambas tablas igualando el espacio de sus cabeceras y separaciones. Conservar el encabezado de partida en una línea, tamaños de columnas, cálculos, datos y funciones. Master por instrucción del usuario; sin commit.

- [x] Reproducir el desfase mediante coordenadas y corregir las cabeceras.
- [x] Verificar alineación al cambiar partidas, redimensionar y mover el separador, también con títulos largos.
- [x] Regresiones y captura al 125 %, con evidencia registrada.

Evidencia:
- Prueba previa falló con coordenadas Y 17 y 25 dentro del área de trabajo: desfase reproducido de 8 píxeles. Ambas cabeceras usan ahora el mismo componente, métricas de fuente, márgenes y política vertical; separación explícita de 3 píxeles en los dos paneles.
- Suite completa: **205 pruebas OK en 36.735 s, salida 0**. Runner offscreen descrito en la revisión anterior, con procesamiento de eliminación diferida entre pruebas. Nueva regresión comprueba igualdad de coordenadas al redimensionar a 1280/1480/1600, mover el divisor y seleccionar títulos o partidas. La prueba de título largo también verifica alineación.
- Captura al 125 % revisada: metrado_aligned_tables_125.png en temporal de Windows, ventana lógica 1525 × 780 y divisor similar a la referencia del usuario. Ambos bordes superiores tienen Y=26 dentro del área de trabajo; cabecera de partida sigue en una línea.
- `git diff --check` sin errores; solo avisos de fin de línea. No se modifican fórmulas, columnas ni persistencia. Cambios previos y ajenos conservados, master sin commit/push.

Siguiente: guardar la obra y reiniciar la aplicación para ver ambas tablas alineadas.
