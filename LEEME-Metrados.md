# Metrados de obra

## Abrir en este equipo

Haz doble clic en **Abrir Metrados.cmd**, en esta carpeta. Abre la aplicación de escritorio usando el entorno Python ya preparado. Mantén juntas las carpetas del proyecto; este acceso no es un instalador independiente.

La primera ventana muestra un ejemplo basado en la imagen de referencia. **Nueva planilla** crea una hoja vacía y **Cargar ejemplo** recupera la demostración, previa consulta si hay cambios sin guardar.

La interfaz adapta la presentación de Gitbin: cabecera compacta con el nombre editable de la obra, pestaña subrayada en turquesa y barra de botones planos con símbolos sobre sus etiquetas. Usa Segoe UI en los tamaños de la referencia y números en Consolas. La estructura de la planilla permanece igual. Si la aplicación estaba abierta al actualizarla, ciérrala guardando tus cambios y vuelve a abrirla para ver el diseño.

## Vista dividida: partidas y metrado

El panel izquierdo muestra un árbol de **títulos, subtítulos y partidas**, con **ÍTEM, descripción, unidad y total actualizado**. Puedes contraer títulos con su flecha y editar descripciones o unidades con doble clic o F2. Los títulos no suman cantidades de unidades diferentes.

Al seleccionar una partida, el panel derecho muestra **solo su desagregado**, incluidos títulos internos, acero y líneas FE, sin repetir la partida como una fila de la tabla. La numeración visual empieza en **1 para cada partida** y cuenta también los títulos internos; no cambia los códigos ÍTEM. La cabecera reúne código, descripción, unidad y total en **una sola línea**. Si la descripción es larga se acorta visualmente, manteniendo el total visible; el texto completo aparece al pasar el puntero. Seleccionar un título deja la planilla vacía hasta elegir una partida; desde el título puedes crear subtítulos o partidas con los botones habituales. Las partidas vacías conservan su cabecera y permiten agregar el primer detalle.

Arrastra el **separador vertical** para repartir el espacio entre paneles. La vista compacta reserva menos espacio a las partidas y ajusta la descripción del metrado al ancho disponible al redimensionar la ventana o mover el separador. Las columnas mantienen sus anchos al cambiar de partida, incluido acero, y al deshacer. Si estrechas demasiado el panel o amplías columnas manualmente, se mantiene el desplazamiento horizontal para no hacer ilegibles los datos. El divisor y los grupos contraídos se conservan durante las operaciones de la sesión, no se guardan como datos de la obra.

En la planilla derecha se ocultan únicamente ÍTEM, unidad de la partida y Total, ya disponibles en el árbol y el encabezado. La cantidad **Und.**, dimensiones, resultados, diámetro y línea FE siguen visibles. Los datos originales y las exportaciones no cambian. Pasa el puntero sobre una descripción cortada para leerla completa; edita la unidad desde el árbol. Copiar/pegar celdas usa las columnas visibles sin sobrescribir las ocultas; copiar bloques conserva toda su información.

Ambos paneles usan el mismo documento: editar una medida actualiza el total de la izquierda inmediatamente. Cambiar de partida confirma la celda que estabas editando, no borra mediciones ni añade una operación de navegación al historial. **Ctrl+Z/Ctrl+Y** funciona en ambos paneles y muestra la partida/fila afectada. Dentro de un editor de texto mantiene su comportamiento habitual.

Las acciones de crear, mover, subir/bajar, tabular, eliminar y copiar/pegar actúan sobre el panel seleccionado. En el árbol, **Ctrl+C** copia el título o partida con todos sus descendientes; puedes seleccionar varios con Ctrl o Mayús. En la planilla, sigue copiando celdas o filas. Pegar texto de varias filas en el árbol solo modifica sus filas visibles, sin alcanzar detalles intermedios. Pegar un rectángulo en la planilla no puede sobrepasar la partida visible: agrega primero sus detalles. **Guardar** y **Exportar JSON** conservan toda la obra, no solo la partida que estás viendo. No cambia el formato SQLite ni los cálculos existentes.

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

En la planilla derecha, **Ctrl+C / Ctrl+V** copia y pega la celda o el rectángulo seleccionado. Puedes seleccionar varias celdas arrastrando o usando Mayús; el formato de texto con tabulaciones es compatible con una hoja de cálculo. El pegado empieza en la celda actual y requiere filas existentes dentro de la partida visible. Las celdas calculadas no se sobrescriben. Si una unidad o diámetro no es admisible, se rechaza todo el pegado, sin dejar cambios parciales.

Para copiar un **título, subtítulo o partida con todos sus descendientes**, selecciónalo en el árbol izquierdo y usa `Ctrl+C`. En la planilla puedes seleccionar una fila desde su número y copiar su bloque. También puedes usar **Copiar bloque con descendientes** (`Ctrl+Mayús+C`) desde cualquier celda. Selecciona el grupo de destino y pulsa `Ctrl+V` (o `Ctrl+Mayús+V`). Al pegar sobre un título/subtítulo, el bloque se añade dentro; sobre una partida o detalle, se añade después de la partida. Los detalles se pegan dentro de una partida de la misma unidad. Los bloques pegados reciben códigos nuevos y conservan las medidas, diámetros y factores exactos.

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

Para un área ya conocida (por ejemplo, 837,13 m2), selecciona el detalle y pulsa **Cantidad directa**. Ingresa la cantidad base antes de aplicar los factores. Esta acción sustituye las dimensiones; editar una dimensión vuelve al cálculo geométrico. Al seleccionar una partida kg o uno de sus detalles, el encabezado superior cambia al formato de acero. Al seleccionar otra unidad o un capítulo vuelve al formato general. Las filas de acero no tienen encabezados propios. DIMENSIONES agrupa Largo, gancho y empalme; después aparece N.º de veces (cantidad de barras). METRADO muestra Lon. acumulada, Diámetro, kg/m y Kg. En Diámetro, entre Lon. y kg/m, haz doble clic o pulsa F2 para elegir una medida de la lista; el peso se recalcula automáticamente. También puedes escribir el diámetro dentro de la descripción, por ejemplo 53 Ø1" o BARRA Ø8mm; la primera forma también completa la cantidad. Gancho y empalme vacíos cuentan como 0. Lon. incluye elementos similares y número de veces. Al abrir archivos anteriores, la columna N.º de veces reúne barras y repeticiones; editarla fija la cantidad total. Los detalles antiguos conservan el cálculo del motor existente; los configurados usan el peso guardado con la fila (ver Tabla de aceros). Sigue pudiendo usarse cantidad directa. Al cambiar la unidad de una partida, se borran las dimensiones y cantidades directas de sus detalles para que vuelvas a ingresarlas en la nueva unidad.

Los resultados se muestran con dos decimales, pero el total usa la precisión del cálculo. Solo se suman detalles de la misma partida; no existe un total global que mezcle unidades.

**Sufijo automático, solo en los detalles de acero:** la descripción termina siempre con la cantidad y el diámetro, por ejemplo `VERTICAL INTERIOR 53 Ø1"`. Se actualiza al cambiar **N.º de veces**, **Diámetro** o la descripción, y se conserva al copiar, guardar y deshacer. Las anotaciones anteriores se reúnen en un único sufijo al final. La cantidad coincide con N.º de veces visible: incluye las repeticiones antiguas, pero no el factor Elem. simil. Renombrar el detalle no altera los factores. Puedes escribir una cantidad y diámetro nuevos en la descripción para actualizar esos campos. Si falta un dato, se muestra `?` hasta completarlo, por ejemplo `Nuevo detalle ? Ø?`. No se agrega a títulos, subtítulos, partidas, grupos internos ni detalles de otras unidades.

## Archivos y teclado

**Guardar** escribe una base de datos SQLite por obra, con extensión `.metrado.db`. No requiere instalar un servidor ni una dependencia adicional. **Abrir** restaura las relaciones, el orden, los datos de entrada y los identificadores internos; recalcula los resultados con el motor Rust. Sigue siendo necesario pulsar **Guardar / Ctrl+S**: no hay autoguardado. Si estás escribiendo una celda, Guardar confirma también esa edición.

Cada guardado se realiza en una transacción: todas sus modificaciones se confirman juntas o se revierten si falla. Las filas sin cambios no se actualizan en SQL. Un archivo nuevo se publica solo después de completar su primera transacción. Se detecta si otra instancia de la aplicación guardó la misma obra: en ese caso no se sobrescriben sus cambios, y puedes usar **Guardar como** para conservar tu versión. El esquema de la base tiene versión propia; una versión desconocida se rechaza sin modificarla. Esta modalidad está diseñada para archivos locales, no para edición simultánea desde varios equipos en una carpeta de red.

**Migrar un archivo anterior:** usa **Abrir**, selecciona el `.metrado.json` y luego **Guardar**. Elige un nombre para la nueva base `.metrado.db`; el JSON original no se modifica. Se admiten las versiones JSON 1, 2, 3, 4 y 5. **Archivo → Exportar copia JSON…** permite obtener una copia para intercambio, sin cambiar la base activa ni marcar los cambios pendientes como guardados. Si hay FE por detalles, la copia usa JSON 5 y requiere esta versión de Metrados para preservar el ajuste; sin ella conserva el formato anterior que corresponda.

Cerrar, crear una planilla o abrir otra consulta qué hacer con los cambios pendientes. Eliminar un título/subtítulo, incluido uno del desagregado, elimina todo su bloque con confirmación previa y puede deshacerse.

## Factor de esponjamiento por bloques de detalles (m³)

Selecciona **uno o varios detalles consecutivos de la misma partida m³**, arrastrando sobre sus celdas o usando Mayús+clic. No incluyas títulos ni partidas en la selección. En el clic derecho, el menú **Edición** o la barra Organizar, elige **Factor de esponjamiento…** e introduce directamente el **FE**, por ejemplo **1,20** (no 20 %). La observación es opcional y se consulta al pasar el cursor por el bloque o su línea FE. El programa no recomienda un valor técnico: utiliza el que corresponda a tu proyecto.

Debajo del bloque aparece **una sola línea**, con las mismas columnas y anchos: **Lon.: FE · Área: 1,20 · Vol.: 57.60**, para dos detalles de 24 m³. Las demás columnas quedan vacías. No hay rótulos BASE/FINAL ni un resumen grande. La línea FE es calculada, no una medición adicional ni un ÍTEM.

**Subtotal del bloque = suma de sus volúmenes originales × FE.** El total de la partida suma los subtotales ajustados y los detalles que no tienen FE, una sola vez. Puedes tener varios bloques con factores diferentes, incluso bloques adyacentes con el mismo factor. Los detalles conservan sus dimensiones y volúmenes originales. Un bloque incompleto muestra **Pendiente** y deja pendiente el total de la partida; los otros bloques válidos mantienen su subtotal. El FE debe ser finito y mayor o igual a 1; se admite coma o punto decimal y no se redondea antes de calcular.

**Doble clic en la línea FE** permite cambiar el factor o **Quitar FE**. También puedes seleccionar un miembro del bloque y abrir la misma acción para editar todo ese bloque. Seleccionar varias filas permite aplicar un nuevo FE solo a ese tramo, sustituyendo el anterior sin superponer ajustes. Ctrl+Z deshace y Ctrl+Y rehace cada cambio.

Al **mover, copiar o eliminar detalles**, el factor acompaña a sus mediciones. Si separas un bloque mediante movimientos o insertando filas libres, cada tramo consecutivo conserva su FE y muestra su propio subtotal. Un detalle nuevo **no hereda automáticamente** un FE. Copiar un bloque o parte de él conserva los factores y crea identidades independientes al pegar; el resumen de texto corresponde únicamente a lo copiado. Para copiar filas completas usa sus encabezados o Ctrl+Mayús+C; Ctrl+C sobre celdas conserva el comportamiento de texto. Cambiar la unidad a otra distinta de m³ elimina los FE, recuperables con Ctrl+Z.

**Ctrl+S** guarda los factores en SQLite, esquema **4**, en la tabla consultable `detail_swelling` (`detail_id`, `block_id`, `factor`, `note`). Los resultados no se almacenan: se recalculan desde las mediciones. Las bases anteriores se leen sin escribir y se migran al guardar, en una transacción que también revierte el cambio de esquema si falla. Se conservan las revisiones para detectar cambios de otra instancia.

Los ajustes antiguos por partida se convierten en bloques sobre sus detalles actuales, conservando factor y observación. Si hay títulos intermedios se muestran varios subtotales equivalentes. Un ajuste antiguo desactivado se conserva como FE 1,00, con el porcentaje anterior anotado. Una partida antigua vacía conserva su configuración hasta que tenga detalles. La exportación con FE por detalles utiliza **JSON 5**; después de guardar en SQLite 4 o exportar JSON 5/6 necesitas esta versión de la aplicación para volver a abrir el archivo.

## Tabla de aceros, ganchos y empalmes

En **Acero → Tabla global de aceros…** puedes editar directamente el peso en kg/m, la longitud de **un gancho de 90°** (incluye tramo libre y doblez) y la longitud de **un empalme**, para cada diámetro. **Guardar** conserva esta tabla en una base SQLite de configuración del usuario, en la carpeta Metrados de su directorio de configuración. Está disponible para todas las obras. Abrir el programa no escribe ese archivo: los valores iniciales están disponibles aunque todavía no hayas guardado la tabla.

Los nuevos detalles de acero comienzan **sin ganchos**, con empalmes automáticos. Selecciona una o varias filas (Mayús para un bloque, Ctrl para filas separadas) y pulsa **Aplicar ganchos…** en la barra, el menú Acero o el clic derecho. Elige **1 o 2 ganchos** para toda la selección: se propone la longitud guardada de cada diámetro o puedes usar una longitud personalizada común. Reaplicar reemplaza los ganchos anteriores; no los acumula. La selección no puede incluir títulos, otras unidades ni cantidades directas.

La columna **Ganchos** contiene la suma de los ganchos de cada barra. La columna **Empalme** contiene la suma de sus empalmes; ambas son calculadas en los detalles configurados. Al pasar el cursor sobre ellas o sobre kg/m se muestra la descomposición. Largo debe representar el tramo recto sin volver a incluir los ganchos. Para el conteo se usa exclusivamente **Largo + Ganchos**: hasta 9 m → 0 empalmes; más de 9 y hasta 18 m → 1; más de 18 y hasta 27 m → 2, etc. Los empalmes mismos, las barras y los elementos similares no intervienen en ese conteo. Es la regla de estimación solicitada, no un optimizador de corte de barras.

**Protección de trabajos:** cada partida y detalle configurado conserva una copia de sus valores. Cambiar la tabla global solo afecta nuevas partidas; no recalcula la obra abierta ni archivos anteriores. Los detalles nuevos de una partida existente usan su tabla guardada. Copiar/pegar conserva los valores del detalle original, incluso en otra obra. Las mediciones antiguas mantienen sus ganchos, empalmes manuales y pesos hasta una acción expresa.

Para adoptar la tabla actual, usa **Acero → Actualizar aceros de esta obra…** y confirma. Solo cambia la obra abierta: pesos, referencias de gancho y empalmes automáticos. Se conservan ganchos personalizados y cantidades directas. Los ganchos manuales antiguos se conservan como un gancho personalizado de la misma longitud total. Aplicar ganchos a filas antiguas también adopta el cálculo automático, **solo para esas filas**, con aviso en el formulario. Estas operaciones se deshacen completas con **Ctrl+Z**. Editar la tabla global es una configuración independiente: no forma parte del historial de la obra.

### Referencias iniciales editables

No son longitudes universales de diseño ni validación de estribos sísmicos. Se utiliza el gancho longitudinal de 90° de E.060 §7.1.2 y tabla 7.1: para el metrado se deriva `12db + π(Dinterior + db)/4`, medido sobre el eje de la barra. Para 6 mm se extrapola un diámetro interior de 6db como referencia, no como requisito explícito de esa tabla.

Empalmes de referencia: tracción clase B, f’c=210 y fy=4200 kgf/cm², concreto normal, sin epóxico, barra no superior, separación libre ≥2db y recubrimiento ≥db; se aplican §12.2 y §12.15. El cálculo convierte resistencias a MPa, usa el mínimo de desarrollo de 0,30 m y el factor 1,3. Las longitudes se redondean hacia arriba al centímetro. El peso inicial usa densidad 7850 kg/m³ y se almacena con seis decimales. **Revisar y editar según planos y condiciones reales.** Fuente: [E.060, publicación SENCICO](https://educa.costosperu.com/wp-content/uploads/2024/08/Norma-E.060-Concreto-armado.pdf).

La obra utiliza **SQLite 4**: `steel_catalog` conserva columnas consultables de diámetro, peso, gancho y empalme por nodo; `steel_hooks` conserva cantidad de ganchos y longitud personalizada. Las celdas de ganchos/empalmes automáticos se reconstruyen desde estos datos, no son entradas independientes. Bases antiguas se leen sin escribir y se migran al guardar. La copia con acero configurado usa **JSON 6** compacto; mantiene el límite de 10 MB y rechaza una exportación excesiva antes de reemplazar el destino. Para obras grandes usa SQLite. El portapapeles interno usa versión 5.

## Deshacer y rehacer

**Ctrl+Z** deshace; **Ctrl+Y** o **Ctrl+Mayús+Z** rehace. También están en **Edición**, la barra Organizar y el menú de clic derecho, con el nombre de la operación correspondiente.

El historial cubre celdas, cambio de unidad (incluidas las medidas que se vacían), cantidades directas, nombre de obra, creación y eliminación de grupos, movimientos, niveles y pegado. Pegar o eliminar un bloque con descendientes es una sola operación. Al deshacer se recuperan los datos, los códigos ÍTEM, los totales y la selección; los anchos de columna se conservan. Mientras escribes dentro de una celda, Ctrl+Z actúa primero sobre el texto del editor; al confirmar la celda, su edición entra al historial de la obra.

Se conservan hasta **200 operaciones durante la sesión**. Guardar no borra ese historial; deshacer después de guardar vuelve a marcar la obra como modificada. Una edición nueva después de deshacer descarta el camino de rehacer. Abrir otra obra, crear una nueva o cerrar reinicia el historial. El historial no se guarda en SQLite: recuperar trabajo tras un cierre inesperado requeriría autoguardado o respaldos, que no forman parte de esta versión.

## Consultar los datos SQLite

La base contiene datos relacionales, no un documento JSON dentro de una columna. `project` guarda el nombre y la revisión; `nodes` contiene una fila por título, partida, grupo de detalle o medición. `id` es su identidad estable; `parent_id` identifica el grupo contenedor; `position` determina el orden. Los códigos visibles se pueden renumerar sin cambiar esas identidades. Copiar y pegar crea identidades nuevas. Hay índices por padre/posición, posición global y tipo/unidad.

Las columnas de entrada son `code`, `description`, `unit`, `similar_elements`, `length`, `width_or_hook`, `height_or_lap`, `times_or_diameter`, `steel_repetitions`, `steel_bars` y `direct_quantity`. Las columnas compartidas representan ancho/ganchos, alto/empalme y veces/diámetro según la unidad. Los valores de entrada son texto para conservar comas decimales, campos vacíos y ediciones todavía incompletas. Los resultados calculados no se almacenan como datos independientes, para evitar totales desactualizados.

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

La interfaz usa Python y PySide6; Rust calcula las cantidades y totales mediante PyO3. Python conserva el catálogo de acero, resuelve la cantidad de ganchos y empalmes y entrega esas entradas al motor.

Desde la carpeta principal del proyecto:

- `uv sync --reinstall-package metrado` reconstruye el paquete local y prepara su entorno Python. Requiere uv y el compilador Rust instalados.
- `uv run metrado` abre la aplicación.
- `cargo test` ejecuta las pruebas del motor Rust.
- `.venv\Scripts\python.exe -B app\tests\test_sheet.py` ejecuta las pruebas de la tabla y del guardado usando el motor real.
- `.venv\Scripts\python.exe -B -m unittest discover -s app/tests -v` ejecuta también las pruebas de jerarquía, movimientos y portapapeles sin instalar herramientas adicionales.
- `.venv\Scripts\python.exe -B app/tests/benchmark_storage.py` mide edición, deshacer, rehacer, apertura y guardado SQLite con 10 000 filas sintéticas en una carpeta temporal. No modifica obras reales. Los tiempos excluyen el repintado de la interfaz y dependen del equipo.
