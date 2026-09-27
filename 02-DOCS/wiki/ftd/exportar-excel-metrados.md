# Exportación Excel de metrados

## Intent

Entregar un archivo editable con Desarrollo y Resumen y fórmulas enlazadas. Revisión solicitada con FORMATO.png: ambas hojas A4 vertical, cabecera enmarcada, campos de obra, encabezados grises, cuadrícula fina, títulos magenta/subtítulos rojos y cuerpo blanco sin bandas de color. En acero, la partida contiene los rótulos gancho, empal., diam. y kg/m; los detalles comienzan inmediatamente debajo, sin una cabecera gris adicional.

## Scope

Menú Archivo y buscador de comandos, sin botón nuevo. Todos los títulos, partidas y detalles; cantidades directas, acero con configuración histórica, referencias y FE por bloques. Desarrollo y resumen verticales. Campos de cabecera editables en Excel; solo proyecto y fecha de exportación tienen valores conocidos. El Excel exportado no contiene notas ni comentarios de celda y usa una escala visual ligeramente menor. No modifica SQLite ni importa de vuelta las fórmulas. Se trabaja en master por indicación expresa del usuario.

La biblioteca Excel ya incluida en la aplicación construye la exportación; la herramienta de hojas de cálculo se utiliza para revisar cálculos y presentación sin agregar dependencias privadas de Codex al programa.

Uso: Archivo → Exportar metrados a Excel…; también aparece al buscar «Excel» con Ctrl+K. Se exporta la obra completa, no solamente la partida visible. Las entradas numéricas pueden editarse; el resumen, las referencias y el FE se actualizan con fórmulas. El texto se imprime negro salvo títulos, subtítulos y valores negativos. Los cambios del archivo exportado no se sincronizan con la base SQLite. Cambiar unidades, insertar filas o reemplazar vínculos exige revisar manualmente las fórmulas.

El catálogo histórico se conserva dentro de Desarrollo, en columnas auxiliares ocultas. Mostrar Q:R permite editar la cantidad de ganchos (0/1/2) y una longitud personalizada; X:AA contiene diámetros, pesos, ganchos y empalmes de cada configuración histórica. Las filas antiguas con gancho/empalme manual conservan ese comportamiento. No se consulta el catálogo global al exportar.

## Checklist

- [x] Simplificar el bloque de acero como aceros.formato.png, sin fila gris y sin desplazar fórmulas.
- [x] Eliminar todas las notas/comentarios y reducir ligeramente tipografía y zoom solo en Excel.
- [x] Verificar visualmente acero, fórmulas, totales, A4 vertical y ausencia de comentarios.

- [x] Ajustar al formato de FORMATO.png y A4 vertical en ambas hojas; conservar relaciones al desplazar las filas de cabecera.
- [x] Verificar cabecera, cuadrícula, colores, impresión vertical y regresiones de fórmulas.

- [x] Revisar visualmente ambos PDF y confirmar un libro de dos hojas editable con fórmulas.
- [x] Implementar exportación atómica, fórmulas y valores iniciales verificados contra el motor.
- [x] Integrar menú sin alterar documento, selección ni historial.
- [x] Probar geometría, signos, acero, referencias, FE, datos pendientes y errores de escritura.
- [x] Revisar presentación y configuración A4; documentar límites de la verificación.

## Evidence

Revisión FORMATO.png (27/09/2026):

- Arial Narrow 9 pt, título centrado en marco independiente, bloque de datos de obra enmarcado y encabezado gris de dos niveles. Cuerpo blanco con cuadrícula gris, capítulos magenta, subtítulos rojos y partidas en negrita. No se aplican sangrías ni se copian los datos de la imagen. Datos faltantes editables en Excel.
- Desarrollo y Resumen configurados A4 vertical, ajuste a una página de ancho y tantas páginas de alto como se necesiten. Se conservan las 14 columnas y los encabezados locales de acero; dimensiones y totales no se cortan en la revisión de Excel. Las fórmulas empiezan ahora en la fila 12 y todos sus enlaces se validaron.
- 26 pruebas de exportación aprobadas (tres nuevas sobre cabecera, tipografía/cuadrícula y precisión de pesos). Suite completa: 396 pruebas aprobadas en 84.966 s. Revisión adicional del ajuste de texto vertical realizada después de esa ejecución.
- Excel nativo confirmó PaperSize=9, Orientation=1, FitToPagesWide=1 y PrintTitleRows=$1:$11 en ambas hojas. Nuevas comprobaciones de recálculo aprobaron FE, referencias, conversión, acero y pendientes. El peso mostrado con dos decimales conserva la precisión original de cálculo.
- Inspección de Desarrollo, Resumen y página de continuación mediante imágenes generadas desde Excel; Artifact Tool revisó las dos hojas, sus fórmulas y las vistas de desarrollo/acero/resumen. Se corrigieron los encabezados estrechos «Ancho» y «N.º de veces» durante esta revisión.
- Límite del PDF auxiliar de Excel 2019: al exportar el libro completo no repitió el encabezado en la segunda página; la exportación de la hoja individual sí lo repite correctamente, sin cambiar el XLSX. Desarrollo produjo 607.10×859.22 pt y Resumen 594.96×842.04 pt. Se verifica la configuración A4 del XLSX, no exactitud física del PDF auxiliar ni del controlador de impresora. No se modificó ninguna configuración global de impresión.

Revisión de acero aceros.formato.png (27/09/2026):

- Se eliminó la fila gris «ACERO · longitudes en m». La fila de partida de acero muestra gancho, empal., diam. y kg/m en F, G, J y K; el primer detalle queda inmediatamente debajo y conserva las fórmulas de largo, ganchos, empalme, número de barras, longitud, diámetro, peso unitario y peso total.
- Se eliminaron todas las notas y comentarios de ambas hojas. La tipografía del cuerpo bajó de 9 a 8 pt, el título de 12 a 11 pt y el zoom inicial de 100 % a 90 %, únicamente en el Excel exportado.
- Artifact Tool recalculó el libro, no detectó errores de fórmula y confirmó visualmente el nuevo bloque. Excel nativo confirmó A4 vertical, una página de ancho, cero comentarios y recálculo de FE, referencias, conversiones, acero y pendientes. Los valores revisados incluyeron 1,336.66 m, 3.98 kg/m y 5,316.77 kg.
- 27 pruebas específicas de exportación y la suite completa de 397 pruebas aprobaron; la ejecución completa tomó 116.132 s. `git diff --check` se ejecuta al cierre.

Evidencia de la implementación inicial (anterior al cambio de formato):

Ambos PDF tienen tres páginas. Se revisó la primera página de cada uno: fondo blanco, encabezados grises, títulos coloreados y jerarquía tipográfica. El usuario confirmó dos hojas y fórmulas editables mediante las dos respuestas del formulario.

- 23 pruebas específicas de exportación aprobadas: lectura real del XLSX con fórmulas y cachés, paridad con Rust, todas las unidades, FE múltiple, referencias con signos/conversión, acero histórico, datos pendientes, escritura atómica, seguridad de texto, menú y conservación del documento.
- Suite completa final: 390 pruebas aprobadas en 48.891 s. `git diff --check` sin errores de espacios; rama master.
- Excel 2019, instancia propia no visible y libros de prueba: al cambiar largo 2→4 se obtuvo FE=86.4, referencia negativa=-86.4, conversión=172.8 y resumen=86.4. Largo de acero 8.2 + ganchos 0.8 produjo cero empalmes; 8.21 produjo un empalme. Cambiar diámetro actualizó kg/m. Largo cero propagó «Pendiente» hasta Resumen.
- Artifact Tool: importación, recálculo, inspección y tres vistas renderizadas (desarrollo, acero y resumen); total de acero del ejemplo=22040.95982672276. Excel nativo confirmó ceros iniciales de los ítems, sufijos y presentación final sin cortes de encabezados.
- Impresión: ambas hojas contienen paperSize=9 (A4), un ancho de página y altura libre, encabezados repetidos, márgenes y numeración. Se inspeccionaron las páginas exportadas por Excel. Limitación observada: el motor PDF local generó páginas de 895.79×632.94 pt (y orientación inversa), no las dimensiones físicas A4; no se atribuye verificación física A4 a esos PDF. La funcionalidad entrega XLSX, no PDF, y no modifica configuraciones de impresora.
- Rendimiento: exportación real de 10 000 filas (9 999 detalles) en 6.503 s; antes de reutilizar estilos y evitar formateo duplicado, 15.796 s. Complejidad lineal en filas y vínculos; sin fórmulas sobre columnas completas.
- Temporales y previsualizaciones en tmp/, excluidos de Git. No se cambió la dependencia de la aplicación. Existe un bytecode rastreado de window modificado externamente durante el trabajo; no se revirtió.

## Next

Entregado para probar Archivo → Exportar metrados a Excel… con una obra real. No generar commit sin una nueva solicitud.
