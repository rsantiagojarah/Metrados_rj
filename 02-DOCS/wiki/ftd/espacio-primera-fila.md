# Espacio vacío antes del primer detalle

## Intent

Eliminar la franja vacía que aparece al crear el primer detalle de una partida después de visitar otra con FE.

## Scope

Solo geometría de la tabla y regresiones de navegación/FE. Sin cambios de datos, cálculos, exportación Excel ni anchos de columna. Rama master según indicación del usuario; conservar modificaciones pendientes.

## Checklist

- [x] Reproducir y medir la franja en Qt.
- [x] Agregar regresiones que fallen antes de corregir.
- [x] Evitar que la altura mínima de FE interfiera con la ocultación de filas.
- [x] Verificar navegación, alta, undo/redo y suite completa.

## Evidence

Reproducción offscreen con ventana real: visitar EXCAVACIÓN con FE, navegar a VACÍA y agregar detalle. La cabecera vertical conserva length=56 cuando no hay filas visibles; el primer detalle normal tiene altura 28 pero rowViewportPosition=56. La franja permanece al añadir más detalles y deshacer. El callback sectionResized intenta restaurar 56 píxeles incluso cuando Qt oculta la sección reduciéndola a cero.

Las tres regresiones nuevas fallaron antes de corregir (56 != 0). Tras ignorar tamaños cero y filas ocultas en el callback, pasaron las 41 pruebas de navegación en 6.828 s. La captura Qt revisada muestra el primer detalle bajo el encabezado: y=0, altura=28, longitud total de cabecera=28. Cambiar de partida, sincronizar FE oculto y undo/redo conservan la geometría; el FE visible sigue midiendo 56 píxeles y calculando 57.60.

Suite completa: 393 pruebas aprobadas en 46.696 s. `git diff --check` sin errores de espacios. Cambios de Excel y bytecode de la aplicación conservados; sin commit.

## Next

El usuario debe guardar y reiniciar su aplicación para cargar el código corregido. No se tocó su ventana abierta ni se guardó su obra.
