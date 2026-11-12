# Precisión unificada de metrados y Excel

## Intent

Igualar los valores utilizados y mostrados por la planilla y sus exportaciones, con redondeo decimal comercial por detalle y totales que suman los detalles redondeados.

## Scope

- Datos generales: normalizar a dos decimales antes de calcular y conservar esa entrada en el documento.
- Excepciones: kg/m, espaciamientos, factores de conversión y FE conservan su precisión. Diámetros conservan su denominación; los conteos físicos permanecen enteros.
- Acero: completar longitud, factores y peso unitario antes de redondear el peso final a dos decimales.
- Resultados de detalles, referencias y ajustes FE: dos decimales. Totales: suma de resultados redondeados.
- Lectura, pegado, AutoCAD, generación de muros, historial y ambas exportaciones siguen la misma política. Las obras originales no se sobrescriben durante las pruebas.
- El motor sigue en Rust. La interfaz prepara entradas y presenta resultados; no duplica fórmulas.

## Checklist

- [x] Reproducción automatizada de 0,05 × 0,70 y suma de detalles redondeados; observar fallos antes del arreglo.
- [x] Motor decimal Rust y enlace: cantidades, acero, referencias y FE; pruebas Rust correctas.
- [x] Entradas generales normalizadas y excepciones conservadas en edición, apertura y operaciones por lotes.
- [x] Pantalla y Excel muestran kg/m con su precisión; fórmulas Excel redondean los resultados en los mismos puntos.
- [x] Pruebas Python, persistencia e historial correctas; comprobar el archivo local sin modificarlo.
- [x] Reconstruir el módulo utilizado por la aplicación y documentar la verificación y sus límites.

## Evidence

- Reproducción previa: 0,05 × 0,70 produce 0,034999999999999996; pantalla 0,03 y Excel solo valores guarda 0,035 (visible 0,04).
- Antes del cambio: 39 pruebas de exportación/presentación pasaban, pero no cubrían ese caso.
- Rama de trabajo: fix/precision-metrados-excel. Se conservan los tres archivos ajenos no versionados presentes al iniciar.
- 2026-11-12: las dos pruebas Rust nuevas fallaron antes del arreglo (0,034999999999999996 frente a 0,035 y 0,07 frente a 0,08). Las cinco pruebas Python nuevas fallaron antes del arreglo en entradas, resultados, referencias, kg/m y exportación.
- 2026-11-12: `cargo test --workspace --offline`: 23 pruebas Rust correctas. BigDecimal realiza productos/sumas decimales y redondeo comercial explícito; el enlace expone el producto completo y el redondeo final.
- 2026-11-12: se reconstruyó e instaló el paquete local mediante `uv sync --reinstall-package metrado --offline`; el binario Python 3.12 del proyecto contiene el motor nuevo.
- 2026-11-12: 523 pruebas Python correctas en los 30 módulos `test_*.py`, ejecutados por módulos con el runner estándar unittest y Qt fuera de pantalla. Los registros completos están en la carpeta temporal ignorada `tmp/precision-final-modules`. Los cambios finales de muros y presentación se comprobaron también con 35 y 11 pruebas específicas correctas.
- 2026-11-12: Excel instalado abrió y recalculó copias temporales en solo lectura: casos con fórmulas (458 celdas), casos solo valores (458), copia de la obra local con fórmulas (115) y solo valores (115). Total: 1.146 comprobaciones, cero diferencias. Se comprobaron valores calculados y representación a dos decimales de los resultados finales.
- 2026-11-12: comprobación adicional en Excel, sin guardar: editar una medida a 1,235 produjo 1,24; cambiar el kg/m a 0,1234567 con longitud de 100 m produjo 12,35 kg.
- 2026-11-12: `git diff --check` terminó correctamente. La obra local se abrió con SQLite en modo lectura y no se sobrescribió. No se cerró ninguna sesión del usuario.
- Límite: se comprobó el entorno Python 3.12 de este equipo y el Excel instalado. Otro intérprete requiere reconstruir su módulo Rust; no se modificó el binario antiguo Python 3.11. Los libros Excel exportados anteriormente deben volver a exportarse para incorporar la nueva política.

## Next

Guardar los cambios pendientes en cualquier ventana anterior, cerrar y abrir Metrados mediante su acceso habitual. Volver a exportar los reportes que deban utilizar la política nueva; el archivo original de la obra solo cambia al guardar.
