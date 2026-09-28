# Quitar comentarios al pasar el mouse

## Intent

Evitar que las tablas de partidas, desarrollo y vista previa de importación muestren textos emergentes al dejar el mouse sobre una celda o sobre el resumen FE.

## Scope

Solo se eliminan los tooltips de contenido de ambas tablas. Se conservan los mensajes de validación, la barra de estado, los diálogos y las ayudas breves de los botones. Se trabaja en master por indicación del usuario.

## Checklist

- [x] Eliminar los tooltips producidos por los modelos de partidas, desarrollo y vista previa de importación.
- [x] Eliminar el tooltip especial del resumen FE sin afectar clic ni doble clic.
- [x] Verificar todas las clases de fila y la suite completa.

## Evidence

La regresión nueva falló antes del cambio porque una celda devolvía «01» para `Qt.ToolTipRole`. Después de eliminar ese rol de ambos modelos y el tratamiento especial del pie FE, todas las celdas devuelven vacío para ese rol y el evento hover del pie no invoca `QToolTip.showText`.

Las 128 pruebas relacionadas con FE, navegación, referencias y acero aprobaron en 28.338 s. Una prueba adicional cubre la vista previa de importación. La suite completa aprobó 399 pruebas en 97.974 s. Se conservaron el doble clic del FE, la edición, los errores de validación, los diálogos y las ayudas de botones.

## Next

Reiniciar la aplicación para cargar el cambio. No generar commit hasta que el usuario lo solicite.
