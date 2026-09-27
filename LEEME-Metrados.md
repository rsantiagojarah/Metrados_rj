# Metrados de obra

## Abrir en este equipo

Haz doble clic en **Abrir Metrados.cmd**, en esta carpeta. Abre la aplicación de escritorio usando el entorno Python ya preparado. Mantén juntas las carpetas del proyecto; este acceso no es un instalador independiente.

La primera ventana muestra un ejemplo basado en la imagen de referencia. **Nueva planilla** crea una hoja vacía y **Cargar ejemplo** recupera la demostración, previa consulta si hay cambios sin guardar.

La interfaz adapta la presentación de Gitbin: cabecera compacta con el nombre editable de la obra, pestaña subrayada en turquesa y barra de botones planos con símbolos sobre sus etiquetas. Usa Segoe UI en los tamaños de la referencia y números en Consolas. La estructura de la planilla permanece igual. Si la aplicación estaba abierta al actualizarla, ciérrala guardando tus cambios y vuelve a abrirla para ver el diseño.

## Registrar metrados

1. Escribe el nombre de la obra.
2. Agrega un **título** (capítulo) para agrupar partidas; aparece en rojo. Selecciónalo y pulsa **+ Subtítulo** para crear un grupo dentro de él. Puedes repetirlo para anidar más subtítulos.
3. Agrega una **partida**, edita su descripción y elige su unidad con doble clic en Und. El código ÍTEM se asigna por posición y nivel.
4. Selecciona la partida y pulsa **+ Detalle** para registrar una medición. Puedes añadir varios detalles por partida.
5. Escribe las dimensiones y los factores **Elem. simil.** y **N.º de veces**. Los resultados y el total se calculan automáticamente.

La tabla conserva las 14 columnas: Ítem, Descripción, Und, Elem. simil., Largo, Ancho, Alto, N.º de veces, Lon., Área, Vol., Kg., Und. y Total. Dimensiones y Metrado tienen encabezados agrupados. Puedes ajustar el ancho de las columnas arrastrando sus bordes.

## Organizar títulos, subtítulos y partidas

La sangría de la descripción muestra qué filas pertenecen a cada grupo. Seleccionar un título o subtítulo y añadir una partida la coloca **dentro** de ese grupo; añadirla desde una partida o detalle la coloca después de la partida actual, al mismo nivel. **+ Título** crea un grupo principal después del título principal seleccionado. **+ Detalle** crea una medición dentro de la partida seleccionada.

La barra **Organizar**, el menú superior y el clic derecho ofrecen las mismas operaciones:

- **Subir / Bajar** (`Alt+↑` / `Alt+↓`): intercambiar con el grupo o fila anterior/siguiente del mismo nivel. Un título incluye sus subtítulos y partidas; una partida incluye sus detalles.
- **Aumentar nivel** (`Tab` en Ítem o Descripción, o `Alt+→`): introducir la fila en el título/subtítulo hermano inmediatamente anterior. Un título pasa a ser subtítulo.
- **Reducir nivel** (`Mayús+Tab` en Ítem o Descripción, o `Alt+←`): sacar el bloque de su grupo y colocarlo después de él, un nivel más arriba.
- **Mover a…** (`Ctrl+M`): buscar un título/subtítulo de destino por código o descripción y trasladar el bloque completo. Un detalle puede trasladarse a otra partida de la misma unidad; sus totales se recalculan.

En columnas numéricas y mientras editas una celda, `Tab` sigue avanzando entre celdas. Las acciones de nivel actúan sobre la fila actual. Se conservan los datos y los anchos de columna, incluso los anchos ajustados manualmente. No se suman unidades distintas.

**Numeración automática de ÍTEM:** al crear, eliminar, pegar o mover filas, se renumera toda la planilla de arriba hacia abajo según la jerarquía actual. Los títulos principales son `01`, `02`, `03`…; los subtítulos y partidas del mismo grupo comparten una secuencia: `01.01`, `01.02`…; sus hijos heredan el nuevo prefijo: `01.02.01`, `01.02.02`… Los detalles quedan sin código y no consumen números. Cambiar el nivel o el orden actualiza también todos los descendientes. Los códigos anteriores o editados manualmente se sustituyen por esta secuencia al realizar una operación estructural.

## Títulos dentro del desagregado

Dentro de una partida puedes separar sus mediciones con encabezados como **VEREDAS**, **VEREDAS 2** y sus propios subtítulos. Son títulos internos: aparecen en negrita y con sangría, sin código ÍTEM, unidad ni valores numéricos visibles. La partida suma todos los detalles contenidos en esos grupos; un título vacío no deja el total pendiente.

1. Selecciona la partida y pulsa **Título detalle** (`Alt+G`). Escribe el encabezado.
2. Selecciona ese título y pulsa **+ Detalle** para añadir mediciones dentro de él.
3. Pulsa **Subt. detalle** (`Alt+Mayús+G`) para crear un subtítulo dentro del título de detalle seleccionado. También funciona desde un detalle que pertenezca a ese título.
4. Para crear otro título al mismo nivel, selecciona el título anterior y pulsa **Título detalle**. Se inserta después de todo su bloque. Desde una medición, se inserta después de ella, a su mismo nivel.

Para incorporar mediciones existentes, colócalas después de un título de detalle y usa **Tab** en Ítem o Descripción, o **Mover a…** para elegir el grupo. **Mayús+Tab** saca la medición o subgrupo un nivel, sin permitir que salga de su partida. Subir/bajar, copiar/pegar y eliminar incluyen todos los descendientes del título. Se pueden trasladar grupos a otras partidas de la misma unidad. Al cambiar la unidad de una partida, sus grupos se conservan y se vacían las medidas de todos sus detalles para introducirlas en la nueva unidad.

Los botones principales **Título** y **Subtítulo** siguen creando capítulos que agrupan partidas; usa **Título detalle** y **Subt. detalle** para organizar el interior de una partida. Los grupos internos no consumen números en la secuencia de ÍTEM.

## Copiar y pegar

**Ctrl+C / Ctrl+V** copia y pega la celda o el rectángulo seleccionado. Puedes seleccionar varias celdas arrastrando o usando Mayús; el formato de texto con tabulaciones es compatible con una hoja de cálculo. El pegado empieza en la celda actual y requiere filas existentes. Las celdas calculadas no se sobrescriben. Si una unidad o diámetro no es admisible, se rechaza todo el pegado, sin dejar cambios parciales.

Para copiar un **título, subtítulo o partida con todos sus descendientes**, selecciona la fila desde su número en el margen izquierdo y usa `Ctrl+C`. También puedes usar **Copiar bloque con descendientes** (`Ctrl+Mayús+C`) desde cualquier celda. Selecciona el grupo de destino y pulsa `Ctrl+V` (o `Ctrl+Mayús+V`). Al pegar sobre un título/subtítulo, el bloque se añade dentro; sobre una partida o detalle, se añade después de la partida. Los detalles se pegan dentro de una partida de la misma unidad. Los bloques pegados reciben códigos nuevos y conservan las medidas, diámetros y factores exactos.

Mientras editas texto con doble clic o F2, `Ctrl+C / Ctrl+V` conserva su comportamiento habitual dentro del editor. El límite por planilla es de 10 000 filas y hasta 32 niveles de sangría.

## Cálculos

| Unidad | Datos del detalle | Resultado |
| --- | --- | --- |
| m | Largo | Lon. |
| m2 | Largo y ancho | Área |
| m3 | Largo, ancho y alto | Vol. |
| kg | Largo, gancho, empalme, Ø y n° de barras (solo esa partida) | Long., kg/m y Kg |
| und, mes, vje, glb | Factores; cantidad base opcional | Und. |

Todos los resultados se multiplican por elementos similares y número de veces. Los factores comienzan en 1. Se aceptan coma o punto decimal, sin separadores de miles. Los datos deben ser positivos y finitos; un detalle incompleto deja el total de su partida como **Pendiente**. Una partida sin detalles tiene total 0,00.

Para un área ya conocida (por ejemplo, 837,13 m2), selecciona el detalle y pulsa **Cantidad directa**. Ingresa la cantidad base antes de aplicar los factores. Esta acción sustituye las dimensiones; editar una dimensión vuelve al cálculo geométrico. Al seleccionar una partida kg o uno de sus detalles, el encabezado superior cambia al formato de acero. Al seleccionar otra unidad o un capítulo vuelve al formato general. Las filas de acero no tienen encabezados propios. DIMENSIONES agrupa Largo, gancho y empalme; después aparece N.º de veces (cantidad de barras). METRADO muestra Lon. acumulada, Diámetro, kg/m y Kg. En Diámetro, entre Lon. y kg/m, haz doble clic o pulsa F2 para elegir una medida de la lista; el peso se recalcula automáticamente. También puedes escribir el diámetro dentro de la descripción, por ejemplo 53 Ø1" o BARRA Ø8mm; la primera forma también completa la cantidad. Gancho y empalme vacíos cuentan como 0. Lon. incluye elementos similares y número de veces. Al abrir archivos anteriores, la columna N.º de veces reúne barras y repeticiones; editarla fija la cantidad total. Los pesos conservan el cálculo del motor existente. Sigue pudiendo usarse cantidad directa. Al cambiar la unidad de una partida, se borran las dimensiones y cantidades directas de sus detalles para que vuelvas a ingresarlas en la nueva unidad.

Los resultados se muestran con dos decimales, pero el total usa la precisión del cálculo. Solo se suman detalles de la misma partida; no existe un total global que mezcle unidades.

**Sufijo automático, solo en los detalles de acero:** la descripción termina siempre con la cantidad y el diámetro, por ejemplo `VERTICAL INTERIOR 53 Ø1"`. Se actualiza al cambiar **N.º de veces**, **Diámetro** o la descripción, y se conserva al copiar, guardar y deshacer. Las anotaciones anteriores se reúnen en un único sufijo al final. La cantidad coincide con N.º de veces visible: incluye las repeticiones antiguas, pero no el factor Elem. simil. Renombrar el detalle no altera los factores. Puedes escribir una cantidad y diámetro nuevos en la descripción para actualizar esos campos. Si falta un dato, se muestra `?` hasta completarlo, por ejemplo `Nuevo detalle ? Ø?`. No se agrega a títulos, subtítulos, partidas, grupos internos ni detalles de otras unidades.

## Archivos y teclado

**Guardar** escribe una base de datos SQLite por obra, con extensión `.metrado.db`. No requiere instalar un servidor ni una dependencia adicional. **Abrir** restaura las relaciones, el orden, los datos de entrada y los identificadores internos; recalcula los resultados con el motor Rust. Sigue siendo necesario pulsar **Guardar / Ctrl+S**: no hay autoguardado. Si estás escribiendo una celda, Guardar confirma también esa edición.

Cada guardado se realiza en una transacción: todas sus modificaciones se confirman juntas o se revierten si falla. Las filas sin cambios no se actualizan en SQL. Un archivo nuevo se publica solo después de completar su primera transacción. Se detecta si otra instancia de la aplicación guardó la misma obra: en ese caso no se sobrescriben sus cambios, y puedes usar **Guardar como** para conservar tu versión. El esquema de la base tiene versión propia; una versión desconocida se rechaza sin modificarla. Esta modalidad está diseñada para archivos locales, no para edición simultánea desde varios equipos en una carpeta de red.

**Migrar un archivo anterior:** usa **Abrir**, selecciona el `.metrado.json` y luego **Guardar**. Elige un nombre para la nueva base `.metrado.db`; el JSON original no se modifica. Se admiten las versiones JSON 1, 2 y 3. **Archivo → Exportar copia JSON…** permite obtener una copia para intercambio, sin cambiar la base activa ni marcar los cambios pendientes como guardados. Los programas anteriores necesitan esa copia JSON compatible, no el archivo SQLite.

Cerrar, crear una planilla o abrir otra consulta qué hacer con los cambios pendientes. Eliminar un título/subtítulo, incluido uno del desagregado, elimina todo su bloque con confirmación previa y puede deshacerse.

## Deshacer y rehacer

**Ctrl+Z** deshace; **Ctrl+Y** o **Ctrl+Mayús+Z** rehace. También están en **Edición**, la barra Organizar y el menú de clic derecho, con el nombre de la operación correspondiente.

El historial cubre celdas, cambio de unidad (incluidas las medidas que se vacían), cantidades directas, nombre de obra, creación y eliminación de grupos, movimientos, niveles y pegado. Pegar o eliminar un bloque con descendientes es una sola operación. Al deshacer se recuperan los datos, los códigos ÍTEM, los totales y la selección; los anchos de columna se conservan. Mientras escribes dentro de una celda, Ctrl+Z actúa primero sobre el texto del editor; al confirmar la celda, su edición entra al historial de la obra.

Se conservan hasta **200 operaciones durante la sesión**. Guardar no borra ese historial; deshacer después de guardar vuelve a marcar la obra como modificada. Una edición nueva después de deshacer descarta el camino de rehacer. Abrir otra obra, crear una nueva o cerrar reinicia el historial. El historial no se guarda en SQLite: recuperar trabajo tras un cierre inesperado requeriría autoguardado o respaldos, que no forman parte de esta versión.

## Consultar los datos SQLite

La base contiene datos relacionales, no un documento JSON dentro de una columna. `project` guarda el nombre y la revisión; `nodes` contiene una fila por título, partida, grupo de detalle o medición. `id` es su identidad estable; `parent_id` identifica el grupo contenedor; `position` determina el orden. Los códigos visibles se pueden renumerar sin cambiar esas identidades. Copiar y pegar crea identidades nuevas. Hay índices por padre/posición, posición global y tipo/unidad.

Las columnas de entrada son `code`, `description`, `unit`, `similar_elements`, `length`, `width_or_hook`, `height_or_lap`, `times_or_diameter`, `steel_repetitions`, `steel_bars` y `direct_quantity`. Las columnas compartidas representan ancho/gancho inicial, alto/empalme y veces/diámetro según la unidad. Los valores de entrada son texto para conservar comas decimales, campos vacíos y ediciones todavía incompletas. Los resultados calculados no se almacenan como datos independientes, para evitar totales desactualizados.

Ejemplo de consulta de solo lectura para listar partidas en su orden actual:

```sql
SELECT id, parent_id, code, description, unit
FROM nodes
WHERE kind = 'item'
ORDER BY position;
```

Para integraciones, consulta la base en modo solo lectura. Las escrituras deben pasar por la aplicación: una edición SQL externa podría romper la jerarquía o saltarse el control de revisiones.

| Acción | Atajo |
| --- | --- |
| Nueva / abrir / guardar | Ctrl+N / Ctrl+O / Ctrl+S |
| Guardar como | Ctrl+Mayús+S |
| Deshacer / rehacer | Ctrl+Z / Ctrl+Y o Ctrl+Mayús+Z |
| Título / subtítulo | Alt+C / Alt+S |
| Partida / detalle | Ctrl+Mayús+N / Ctrl+Enter |
| Título de detalle / subtítulo de detalle | Alt+G / Alt+Mayús+G |
| Subir / bajar bloque | Alt+↑ / Alt+↓ |
| Aumentar / reducir nivel | Tab / Mayús+Tab en Ítem o Descripción; Alt+→ / Alt+← |
| Elegir grupo de destino | Ctrl+M |
| Copiar / pegar celdas o filas seleccionadas | Ctrl+C / Ctrl+V |
| Copiar bloque con descendientes / pegar bloque | Ctrl+Mayús+C / Ctrl+Mayús+V |
| Cantidad directa / eliminar | Ctrl+D / Ctrl+Supr |
| Editar / avanzar durante la edición | F2 / Tab |

Esta versión incluye edición y guardado local. No incluye exportación a Excel/PDF ni instalador para otros equipos.

## Desarrollo

La interfaz usa Python y PySide6; todas las fórmulas de cantidad y la suma por partida viven en Rust y se exponen mediante PyO3.

Desde la carpeta principal del proyecto:

- `uv sync --reinstall-package metrado` reconstruye el paquete local y prepara su entorno Python. Requiere uv y el compilador Rust instalados.
- `uv run metrado` abre la aplicación.
- `cargo test` ejecuta las pruebas del motor Rust.
- `.venv\Scripts\python.exe -B app\tests\test_sheet.py` ejecuta las pruebas de la tabla y del guardado usando el motor real.
- `.venv\Scripts\python.exe -B -m unittest discover -s app/tests -v` ejecuta también las pruebas de jerarquía, movimientos y portapapeles sin instalar herramientas adicionales.
- `.venv\Scripts\python.exe -B app/tests/benchmark_storage.py` mide edición, deshacer, rehacer, apertura y guardado SQLite con 10 000 filas sintéticas en una carpeta temporal. No modifica obras reales. Los tiempos excluyen el repintado de la interfaz y dependen del equipo.
