# Metrados de vivienda Jorge

## Intento
Preparar una obra de Metrados desde los planos suministrados.

## Alcance
Columnas continuas, placas, vigas y losas por nivel y por ejes; concreto de losa 0,09 m³/m²; acero con anclajes y empalmes. Excluir tensores, escaleras y cimentación.

## Lista
- [x] Identificar planos y criterios indicados por el usuario.
- [ ] Reconstruir y comprobar todos los paños, tramos y armaduras contra los planos.
- [ ] Completar cantidades y comprobar el archivo de obra en la aplicación.

## Evidencia
Se examinaron A-01, A-02, E-01 y E-02. La documentación no incluye las láminas 5 y 6.
Se guardó una base preliminar con 62 filas y se comprobó su lectura mediante la función propia de la aplicación. Las cantidades están pendientes: no es un metrado terminado.
Se extrajo DXF desde el DWG aportado: 31 883 entidades y 89 etiquetas de vigas en las tres plantas. La variable INSUNITS declara milímetros, pero la separación dibujada de ejes A-B es 3,10 unidades para una cota de 3,10 m; se requiere tratar la escala con ese contraste. Se preparó una nueva base preliminar con 148 filas, leída con read_database; las etiquetas no prueban tramos ni cantidades. Durante la extracción AutoCAD guardó el DWG original; se restauró desde su copia BAK y se comprobó SHA-256 idéntico para ambos.
Se extrajeron 48 etiquetas de columnas/placas en las tres plantas, no equivalentes a un conteo de elementos continuos. La base parcial V4 contiene 14 paños de losa provisionales con sus respectivos cálculos de área y concreto 0,09 m³/m²; los ítems mantienen detalles pendientes para evitar totales incompletos. El motor de la aplicación calculó los 28 detalles. El usuario autorizó expresamente usar VA-1 como supuesto provisional para VA-4, con identificación explícita.
El usuario autorizó repetir en plantas superiores las secciones y armados de CA y P1, aplicar dos caras entre muros, tres en extremos y cuatro en aisladas, y partir del superior de las zapatas. El avance V23 contiene 674 filas: columnas por tramo continuo, estimaciones de vigas por ejes, paños, acero longitudinal, viguetas, temperatura y estribos aproximados. El detalle Z-1 se tomó a 0,80 m bajo NPT y los cimientos corridos a 0,30 m, sujetos a verificación. La aplicación calculó 531 detalles y mantiene 27 partidas pendientes. SQLite integrity_check: ok. Las áreas brutas de encofrado y el despiece incompleto no son cantidades finales.
El usuario aclaró que los aceros de vigas deben ser continuos a través de los cruces y que solo concreto y encofrado se descuentan en ellos. La base V48 agrega explícitamente longitudes de acero en columnas y cruces, empalmes provisionales, cañas de borde, franjas de losa y 13 CA del cerco con alturas interpretadas de MCA/CC4. VS-1 se aproximó como V-S; los empalmes de vigas suponen barras de 9 m. Se abren 1064 filas, 921 detalles calculados y 27 partidas siguen pendientes; integrity_check: ok. No se ha verificado el despiece completo ni las caras y no se declara terminado.
La versión V49 incorpora además la continuidad de 37 viguetas por piso a través de los cruces en B y E: 1068 filas, 925 detalles calculables, 113 detalles y 27 partidas pendientes; SQLite integrity_check: ok. No se sustituyeron por cero los detalles no resueltos.
Se reorganizó la obra solicitada en nueve partidas: concreto, encofrado y acero para columnas/placas, vigas y losas; niveles y viguetas/temperatura quedan como grupos de detalle. Archivo METRADOS_JORGE_9_PARTIDAS_PENDIENTE.sqlite: 9 partidas, 1036 detalles; comparación con V49 por identidad: 0 perdidos, 0 nuevos, 0 con entradas o resultados cambiados. Las 9 partidas siguen pendientes; integridad SQLite ok.
El usuario pidió extensión .db; se generó METRADOS_JORGE_9_PARTIDAS_ACERO_EN_PROCESO.metrado.db y se abrió con open_document. Se conciliaron 87 etiquetas de vigas con tramos medidos y dos con escalera excluida; los paños de concreto y de encofrado se reconciliaron por dimensiones (15, 14 y 2 por nivel). La base tiene 9 partidas, 999 detalles, seis partidas pendientes y 18 detalles pendientes; sin duplicados de descripción dentro del mismo grupo e integrity_check ok. Los anclajes y remates añadidos son estimados y quedan expresamente marcados: no son una verificación de diseño.
Se verificó que los paños no se solapan, y que el fondo de encofrado y el concreto de vigas coinciden por nivel. Se detectaron y descontaron solapes pequeños de concreto y fondo, conservando la longitud continua del acero. Se conciliaron 48 tramos de columnas/placas y 13 CA de cerco con arranques interpretados; cinco CA del cerco descuentan el tramo bajo NPT del encofrado. Último archivo METRADOS_JORGE_9_PARTIDAS_CERCO_EN_PROCESO.metrado.db: abre con open_document, nueve partidas, cinco pendientes, 993 detalles calculables, integrity_check ok. Son estimaciones, no metrado final validado.

## Siguiente
Terminar la clasificación de caras y los descuentos de encofrado, las vigas y paños aún omitidos, los anclajes y empalmes, y verificar todas las cantidades contra el dibujo antes de cerrar las 27 partidas.
