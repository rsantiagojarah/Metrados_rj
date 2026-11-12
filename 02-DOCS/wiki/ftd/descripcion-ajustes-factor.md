# Descripción correcta de los ajustes por factor

## Intent

Evitar que un reparto porcentual de materiales aparezca como «Factor de esponjamiento». Mostrar la descripción del usuario directamente en la planilla y los reportes, con una denominación neutra cuando no exista descripción.

## Scope

- Acción y formulario «Ajuste por factor»; campo «Descripción del ajuste» y sigla visible F.
- Usar el texto existente de note como descripción; si está vacío o contiene solo espacios, mostrar «Ajuste por factor».
- Misma descripción en la línea visual de la planilla, copia de filas y ambas exportaciones Excel.
- Conservar factor, cálculos, redondeo, bloques, historial, atajos e identificadores de acciones. Mantener los formatos SQLite/JSON y sus observaciones existentes.
- No reescribir automáticamente las obras ni inventar el significado del factor a partir de su valor.

## Checklist

- [x] Reproducir con pruebas el rótulo incorrecto y comprobar 70 %/30 % sobre 410,76 m³.
- [x] Unificar descripción y sigla en interfaz, portapapeles y exportaciones.
- [x] Comprobar descripción vacía, textos literales, guardado/apertura e historial.
- [x] Pruebas relacionadas y regresión correctas; revisar el Excel generado.

## Evidence

- El exportador construye B de la línea de ajuste con el prefijo fijo «Factor de esponjamiento» y agrega note; la interfaz solo muestra FE/factor/subtotal.
- La configuración ya persiste note; no hace falta migrar la base para reutilizarlo como descripción.
- Antes de implementar se observaron siete pruebas fallidas: descripción ausente en planilla/portapapeles, prefijo fijo en Excel, nombre antiguo en formulario/menú y falta del texto de respaldo.
- La función común factor_description utiliza note solo para presentación; conserva el texto almacenado y devuelve «Ajuste por factor» cuando está vacío. Los identificadores internos y de atajos permanecen iguales.
- Ocho pruebas nuevas correctas, incluidas persistencia e historial, descripción vacía, texto que parece fórmula y exportación de ambos repartos. El texto `=1+1` se conserva como literal de Excel, no como fórmula.
- Regresión completa: 556 pruebas Python correctas en 34 módulos, todos con salida 0. Registros temporales en tmp/factor-description-tests. El motor Rust y las fórmulas de cantidad no cambiaron.
- Revisión visual de la planilla y el formulario renderizados fuera de pantalla, cargando explícitamente Segoe UI y Consolas para la captura: descripción alineada a la izquierda, sigla F, factor 0,70 y subtotal 287,53. Los textos largos se acortan en pantalla y se conservan completos al copiar/exportar.
- Excel instalado abrió y recalculó copias temporales de las exportaciones con fórmulas y solo valores. En ambas: «Reparto de relleno: material de préstamo — 70 %» con 0,70 y 287,53 m³; «Reparto de relleno: material propio — 30 %» con 0,30 y 123,23 m³. Sigla F, ajuste de texto y totales correctos. Las copias se cerraron sin guardar.
- git diff --check correcto. No se reescribió ninguna obra del usuario ni se modificaron los formatos SQLite/JSON.

## Next

Reiniciar Metrados y volver a exportar la obra. Las observaciones guardadas se mostrarán automáticamente como descripción del ajuste; los Excel exportados anteriormente conservan sus textos hasta volver a generarlos.
