# Rendimiento de dibujo, edición y estado

## Intent
Reducir trabajo repetido al dibujar, editar y seleccionar celdas en planillas grandes.

## Scope
Reutilizar recursos gráficos; recalcular solo la partida afectada; mantener los conteos al cambiar datos, sin recorrer filas al seleccionar. Conservar interfaz, fórmulas y formato de archivo.

## Checklist
- [x] Edición parcial equivalente al cálculo completo, incluidos errores y cambios de unidad.
- [x] Conteos correctos después de editar, agregar y eliminar.
- [x] Dibujo visualmente idéntico y mediciones comparables.
- [x] Suite de regresión aprobada.

## Evidence
Copia previa: C:\Users\CARMEN\AppData\Local\Temp\metrado-antes-optimizacion-azw3et_0

Prueba de recálculo parcial: falló antes (calculaba ambas partidas) y pasó después (solo la afectada). Se verificó equivalencia con calculate completo en errores, recuperación, cambios de unidad, diámetro, cantidad directa y reemplazo de filas.
36 pruebas aprobadas en 3,892 s. git diff --check sin errores.
Comparación local, misma sesión Qt offscreen, medianas de 30 operaciones:
- Edición del modelo de 5500 filas (500 partidas de 10 detalles): 7,817 ms antes / 0,055 ms después; excluye dibujo de ventana.
- Repintado de tabla visible: 57,008 / 16,657 ms.
- Desplazamiento: 60,765 / 18,247 ms.
- Navegación: 1,506 / 0,943 ms.
Capturas equivalentes antes/después: QImage compara idénticas. Captura guardada en 02-DOCS/attachments/planilla-optimizada.png.
Se reutilizan fuentes, colores, alineaciones y lápiz de bordes; se atienden los roles visuales sin procesar antes los datos del acero. El modelo conserva índices de partida y conteos; editar actualiza únicamente el bloque afectado. La selección no recorre las filas ni vuelve a publicar el mismo mensaje de estado.
Los resultados de tiempo son pruebas locales; el recálculo sigue dependiendo del número de detalles de la partida editada.

## Next
Reabrir Abrir Metrados.cmd para usar las optimizaciones.
