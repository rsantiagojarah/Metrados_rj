# Muros tipo persistentes

## Intent
Crear tipos de muro reutilizables y generar concreto, encofrado y acero en partidas existentes a partir de longitud y altura opcional.

## Scope
Catálogo SQLite local, duplicado, eliminación, importación y exportación JSON; pantalla, zapata, dentellón opcional, refuerzo cortado fijo y distribuciones verticales/horizontales. La altura alternativa modifica pantalla y sus barras dependientes; el refuerzo cortado conserva su longitud.

## Checklist
- [x] Persistir tipos y transferirlos en JSON.
- [x] Configurar geometría, dentellón y distribuciones de acero.
- [x] Generar detalles en partidas m³, m² y kg existentes.
- [x] Probar altura variable, refuerzo cortado y selección de destinos.
- [x] Editar un tramo generado conservando sus vínculos, su configuración original y la posibilidad de deshacer.
- [ ] Ampliación pendiente fuera de esta entrega: configuración detallada de extremos de encofrado.

## Evidence
`test_wall_types.py` y `test_wall_editing.py`: 19 pruebas aprobadas para persistencia, transferencia, generación, altura variable, refuerzo cortado automático, formularios y edición. Incluyen el flujo real de ventana generar → seleccionar detalle → editar → deshacer; aislamiento entre tramos, actualización de destinos, copias independientes, reapertura SQLite/JSON, migración de esquema 6 a 7 y cancelación sin guardar borradores. La integración está en el menú «Muros».

Revisión visual fuera de pantalla de geometría, tabla de acero y edición de tramo: formularios legibles, sin JSON ni recortes. Los campos numéricos admiten operaciones. `git diff --check` sin errores.

Regresión general: 480 pruebas ejecutadas; se detectaron cinco errores al simular esquemas antiguos que conservaban la tabla nueva `wall_details`. Se actualizaron esas preparaciones para eliminar también dicha tabla. Reejecución completa de los tres módulos afectados: referencias 33/33, acero 33/33 y esponjamiento 37/37 aprobadas. Reejecución final de muros: 19/19 aprobadas. No se repitió la batería completa tras corregir exclusivamente esas preparaciones de pruebas.

Se corrigió el conteo del acero longitudinal de zapata: depende de su ancho, no de la altura de pantalla. El refuerzo cortado mantiene su longitud. Los detalles antiguos sin identificador de tramo conservan sus cantidades, pero requieren generar un tramo nuevo para disponer de edición conjunta.

## Next
Validar en uso los formularios y la edición desde «Muros → Editar muro generado…». Trabajo realizado directamente sobre master por petición explícita del usuario.

## Tipos MC-1 a MC-4
Crear en el catálogo persistente los cuatro muros de los planos proporcionados, con dimensiones, acero y dentellón cuando aplica. Mantener horizontales de pantalla limitados a su altura por defecto y dentellón sin encofrado.
- [x] Inspeccionar visualmente los cuatro planos y transcribir geometría y distribuciones.
- [x] Validar generación de concreto, encofrado aplicable y acero en un catálogo temporal.
- [x] Guardar MC-1, MC-2, MC-3 y MC-4 en el catálogo de la aplicación sin alterar `mc_` ni `Muro modelo`.

Evidencia: los cuatro planos se renderizaron y revisaron. Catálogo final: MC-1 (2 m³, 3 m², 9 kg), MC-2 (3 m³, 3 m², 11 kg), MC-3 (3 m³, 3 m², 11 kg), MC-4 (2 m³, 3 m², 8 kg) para un tramo de 10 m; las columnas expresan cantidad de detalles por unidad, no cantidades de obra. MC-1 y MC-4 no tienen dentellón; MC-2 y MC-3 sí. Pruebas de muros: 31/31 aprobadas y `git diff --check` sin errores. MC-4 usa un vuelo derecho de 0,35 m inferido del detalle, pues el plano no lo acota explícitamente; se puede ajustar desde Tipos de muro.

## Altura opcional de zapata para horizontales de pantalla
Casilla desmarcada por defecto: «Incluir altura de zapata en el acero horizontal de pantalla». Solo afecta las distribuciones horizontales de ambas caras de pantalla; al marcar incluye zapata, al desmarcar termina en la cara superior de zapata. Conservar la opción en el tipo y en la copia del tramo.
- [x] Añadir casilla y valor predeterminado desmarcado, incluso para tipos antiguos sin el campo.
- [x] Usar la opción en dibujo, conteo y altura alternativa; comprobar persistencia y aislamiento del resto del acero.

Evidencia: 31/31 pruebas de muros aprobadas. Ambas caras terminan en y=0 con la opción apagada y en y=-espesor de zapata al activarla. Para el modelo, los conteos horizontales pasan de 35/35 a 40/39; el resto de detalles conserva sus valores. Verificados altura alternativa, actualización del esquema, guardado/reapertura del tipo, copia SQLite del tramo y nuevo tipo desmarcado. Revisión visual a 1114×700 sin recortes. `git diff --check` sin errores.

## Vuelos de zapata en cero
Permitir un muro sin vuelo izquierdo, derecho o ambos, manteniendo obligatorios la altura y los espesores.
- [x] Aceptar `0` y operaciones cuyo resultado sea `0` en ambos vuelos.
- [x] Rechazar valores negativos y conservar la generación de concreto, encofrado y acero.

Evidencia: `test_wall_rebar.py` (10/10) comprueba ambos vuelos en cero, una operación que resulta en cero desde el formulario, generación de concreto y acero, y rechazo de valores negativos. `test_wall_types.py` (4/4) también aprobado. `git diff --check` sin errores.

## Dentellón sin encofrado
Por indicación del usuario, el dentellón genera únicamente concreto y acero.
- [x] Excluir su encofrado al generar y actualizar un tramo; conservar pantalla y zapata.
- [x] Verificar que actualizar elimine los detalles de encofrado anteriores del dentellón sin duplicar metrados.

Evidencia: comprobación de generación con dentellón activo y actualización de un tramo con los dos detalles antiguos; desaparecen únicamente esos detalles, conservando exactamente concreto y acero. Regresión de muros: 29/29 pruebas aprobadas. Los tramos existentes aplican este cambio al actualizarlos desde «Editar muro generado».

## Redondeo de concreto y encofrado
Guardar las dimensiones generadas en m³ y m² con dos decimales para que la planilla calcule con esos mismos valores. Conservar la geometría original del tipo y la precisión del acero.
- [x] Aplicar redondeo al generar y actualizar detalles de concreto y encofrado.
- [x] Comprobar ejemplo inclinado, cálculo con dimensiones redondeadas y acero sin cambios.

Evidencia: 29/29 pruebas de muros aprobadas. La longitud inclinada 8.01560977094… se guarda como 8.02 y participa con ese valor en el cálculo. Se verificaron empates decimales (2.675 → 2.68 y 10.005 → 10.01), actualización conservando identificadores, dimensiones originales en la copia del tipo y datos de acero idénticos a los generados sin redondeo. `git diff --check` sin errores.

## Recorridos y ganchos del acero
Corregir recorridos según ampliaciones del PDF y petición explícita: sin descontar recubrimientos; pantalla hasta fondo de zapata; dentellón hasta cara superior de zapata; distribuciones de extremo a extremo. Ganchos independientes por extremo, editables sobre el esquema, con longitudes iniciales de la tabla de acero existente (no están acotados en el PDF). Compartir geometría entre dibujo y metrado.
- [x] Verificar longitudes, conteos, prolongaciones y dobleces contra el plano.
- [x] Editar y persistir ganchos por posición desde el esquema, con despiece de la barra seleccionada.
- [x] Probar extremos, alturas alternativas, refuerzo cortado fijo, datos antiguos y revisión visual.

Evidencia: ampliaciones de corona y anclajes del PDF inspeccionadas. Pantalla vertical izquierda prolonga su pendiente al fondo de zapata; derecha llega al mismo fondo. Las distribuciones horizontales cubren estos recorridos completos. El acero transversal del dentellón recorre ambas caras hasta la cara superior de zapata; sus longitudinales siguen ese recorrido. Zapata usa el ancho total. Los extremos de los ganchos siguen los sentidos dibujados en el plano. `wall_rebar.py` es la fuente compartida para dibujar y calcular; no aplica recubrimientos. La cota de corte 4,60 m está sobre zapata: su cuerpo agrega penetración y conserva ese desarrollo con alturas alternativas del tramo; ganchos aparte.

Se guardan G1/G2 independientes en el tipo, exportación JSON y copia del tramo SQLite; los valores efectivos quedan fijados al generar. G1/G2 aceptan operaciones y vacío como cero. Pruebas: muros 28/28, aritmética 10/10, configuración de acero 33/33. Incluyen selección mediante clic sobre el esquema, edición de extremos, persistencia, datos antiguos, extremos sin recubrimiento y ausencia de doble conteo de ganchos. Revisión visual de pantalla, dentellón y barras fuera del plano de sección, con despiece y suma de longitudes. `git diff --check` sin errores. No se repitió la batería completa; no hubo commit ni push.

## Simplificación solicitada tras revisión visual
Formulario compacto con sección dinámica al costado y once posiciones de acero fijas según MURO MODELO.pdf: cinco de pantalla, cuatro de zapata y dos de dentellón. Sin altas/bajas de distribuciones. Diámetro o separación vacíos omiten la posición sin error; refuerzo cortado además requiere longitud. Mantener persistencia y edición de tramos.
- [x] Sustituir tabla configurable por posiciones fijas opcionales, verificadas contra el plano.
- [x] Compactar campos y dibujar sección con cotas y acero actualizado en vivo.
- [x] Verificar omisión de vacíos, guardado/reapertura, generación y revisión visual.

Evidencia de esta simplificación: 22/22 pruebas de muros y 10/10 de operaciones aritméticas aprobadas. Se comprobaron filas vacías y parcialmente completadas, ausencia de controles para agregar/quitar posiciones, refuerzo cortado opcional, persistencia sin acero, actualización inmediata del esquema y cancelación sin escribir catálogo. Revisión visual a 1160×700 y 1114×700: geometría y acero con/sin dentellón, cortado y pantalla de espesor constante. Los campos quedan compactos y el esquema ocupa el espacio disponible. El dentellón incorpora vuelo inclinado (0,40 m en el modelo); tipos antiguos sin ese campo conservan valor cero. Su sección de concreto y acero en U se calculan con esa geometría. No se repitió la batería global; los cambios de esta iteración se limitaron a formularios y generación de muros. No se realizaron commit ni push.

## Ampliación: ingreso amigable y edición de tramos
- [x] Selector de componente, cara, diámetro, separación y longitud fija; campos numéricos con operaciones y secciones ordenadas.
- [x] Guardar identificación y copia del tipo por tramo en SQLite y JSON; editar desde cualquier detalle asociado sin duplicados; deshacer en una operación.
- [x] Comprobar aislamiento entre tramos iguales, jerarquías de partidas, reapertura, cancelación y errores.
- [x] Revisar visualmente los formularios.
- [x] Ejecutar regresión general y verificar nuevamente los módulos afectados después de corregir las preparaciones de pruebas antiguas.

## Generación desde la partida actual
Usar `F1` dentro de una partida de concreto (m³), encofrado (m²) o acero (kg) para elegir tipo, longitud y altura opcional. El generador inserta solamente los detalles de esa unidad bajo la partida actual; no solicita tres destinos ni un nombre de tramo. La ayuda pasa a `Mayús+F1`.
- [x] Simplificar el diálogo contextual y vincularlo a la partida actual.
- [x] Verificar el atajo, la selección de un detalle como contexto, unidades incompatibles y la generación resultante.

Evidencia: `test_wall_editing.py` (21/21) verifica que el diálogo contextual no muestra destinos ni nombre, inserta solo m² cuando se abre desde esa partida, y conserva la edición de tramos. `test_shortcuts.py` (25/25) confirma que `F1` queda asignado al generador y `Mayús+F1` a la ayuda. Regresión de muros: 35/35 aprobadas. `git diff --check` sin errores.

## Acero longitudinal del dentellón
Mantener el acero transversal en U, con anclaje dentro de la zapata. Distribuir el acero longitudinal únicamente en el borde horizontal inferior del dentellón, por debajo de la zapata.
- [x] Excluir las ramas verticales dentro de la zapata de la distribución longitudinal.
- [x] Verificar el nuevo conteo y que el transversal conserva su recorrido completo.

Evidencia: regresión de muros 35/35 aprobada. El transversal conserva la U completa, desde la cara superior de zapata hasta el fondo del dentellón. Para el muro modelo, el longitudinal queda entre x=3,85 m y x=4,45 m a cota −1,90 m: cuatro barras con separación de 0,25 m, sin barras longitudinales en la zapata. `git diff --check` sin errores.

## Longitud de muro desde AutoCAD
Al enfocar «Longitud del tramo» en el generador de muro, `MTRLONGITUD` debe completar esa casilla sin crear detalles nuevos en la planilla. En selección total usa la longitud recibida; en selección individual o por capa suma las longitudes seleccionadas.
- [x] Registrar y liberar el campo activo del diálogo.
- [x] Enviar la medición de AutoCAD al campo y conservar la importación habitual cuando no haya un diálogo activo.

Evidencia: `test_autocad_length.py` 7/7 confirma captura de una longitud total y suma de mediciones múltiples en el campo del diálogo, sin agregar filas a la planilla; el flujo habitual de importación de longitudes también se conserva. Regresión de muros: 35/35 aprobadas.

## Generador continuo con destinos por componente
Restaurar el formulario completo y separar sus seis destinos: pantalla y zapata para concreto, encofrado y acero; dentellón pertenece a zapata. Elegir cada partida y el tipo de muro con búsquedas filtradas. Generar títulos automáticos «Tipo · Descripción» y conservar el formulario abierto después de generar.
- [x] Separar destinos y enrutar correctamente pantalla, zapata y dentellón.
- [x] Añadir búsquedas filtradas de partidas y tipos, descripción y títulos por destino.
- [x] Mantener el formulario abierto al generar y conservar la actualización de tramos.

Evidencia: regresión de muros 35/35 aprobada. Comprobación directa con seis partidas de destino: se crean seis títulos, se separan pantalla y zapata en cada unidad, y concreto/acero del dentellón se insertan bajo zapata. `test_autocad_length.py` 7/7 aprobado; `git diff --check` pendiente de la comprobación final.

## Distancia de dos puntos desde AutoCAD
Agregar `MTRDISTANCIA`: toma dos puntos en AutoCAD y pasa la distancia en metros a la casilla numérica activa, sin crear detalles. En una planilla aplica a Largo, Ancho o Alto; en el generador de muros aplica a Longitud del tramo. Rechaza selecciones incompatibles.
- [x] Añadir comando, mensaje del puente y receptor de la aplicación.
- [x] Verificar recepción en el formulario de muro y en una dimensión de planilla.
- [x] Compilar el complemento de AutoCAD 2021.

Evidencia: `test_autocad_length.py` 8/8 aprobado, incluida distancia a campo de muro y a celda de planilla, sin agregar filas. El complemento se compiló correctamente en `target/autocad/Metrados.AutoCAD2021.bundle`; `git diff --check` sin errores.

## Compatibilidad de atajos F1
Una configuración guardada antes de añadir el generador de muros podía conservar `F1` para la ayuda y entrar en conflicto con el nuevo `F1` de «Generar muro tipo».
- [x] Migrar automáticamente esa asignación antigua a `Mayús+F1` al abrir o configurar atajos.
- [x] Conservar los demás atajos personalizados y guardar la configuración reparada.

Evidencia: `test_shortcut_configuration.py` verifica una configuración antigua con ayuda en `F1`, generación de muro en `F1`, ayuda en `Mayús+F1` y persistencia de la corrección.

## Formato decimal de Excel
Evitar cifras residuales largas en las celdas visibles de dimensiones, cantidades directas y metrados al exportar a Excel.
- [x] Mostrar dos decimales en la planilla exportada.
- [x] Conservar el valor y las fórmulas de cálculo internos sin redondearlos.

Evidencia: `test_area_base.py` comprueba que el área directa conserva su valor 125,50 y se presenta con dos decimales.

## Separadores entre partidas en Excel
Insertar una fila vacía en «Desarrollo» al terminar los detalles de cada partida, incluida la fila FE cuando corresponda.
- [x] Crear separadores visuales de altura reducida sin fórmulas ni valores visibles.
- [x] Conservar posiciones correctas para totales, referencias y vínculos desde «Resumen».

Evidencia: `test_excel_export.py` verifica filas separadoras, altura, siguiente partida y vínculo del Resumen.

## Etiqueta de longitud directa
Las cantidades directas de partidas medidas en metros deben identificar su base como «LONGITUD», de la misma forma que m² usa «ÁREA» y m³ usa «VOLUMEN».
- [x] Mostrar «LONGITUD» en la planilla y el reporte Excel para unidad `m`.
- [x] Conservar la cantidad calculada en la columna Lon.

Evidencia: `test_direct_display.py` comprueba la etiqueta y el resultado de longitud directa en pantalla y Excel.
