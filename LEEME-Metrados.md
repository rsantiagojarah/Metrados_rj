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

## Archivos y teclado

**Guardar** escribe un archivo de proyecto con extensión `.metrado.json`; **Abrir** restaura la obra, las filas y los datos. El guardado reemplaza el archivo de forma atómica. Cerrar, crear una planilla o abrir otra consulta qué hacer con los cambios pendientes. Eliminar una partida también elimina sus detalles; eliminar un capítulo elimina sus partidas, siempre con confirmación.

Los archivos anteriores siguen abriendo. Los proyectos con niveles explícitos se guardan en formato versión 2 y requieren esta versión de Metrados para preservar los subtítulos. Eliminar un título/subtítulo elimina todo su bloque, con confirmación previa.

| Acción | Atajo |
| --- | --- |
| Nueva / abrir / guardar | Ctrl+N / Ctrl+O / Ctrl+S |
| Guardar como | Ctrl+Mayús+S |
| Título / subtítulo | Alt+C / Alt+S |
| Partida / detalle | Ctrl+Mayús+N / Ctrl+Enter |
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
