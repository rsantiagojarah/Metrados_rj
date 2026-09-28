# Atajos configurables

## Intent

Permitir que cada usuario asigne, cambie o quite combinaciones de teclas para todas las acciones de Metrados, sin afectar las obras guardadas y sin reiniciar la aplicación.

## Scope

Incluye un formulario global accesible desde Ayuda, dos combinaciones por acción, búsqueda, detección de conflictos, restauración de valores predeterminados y persistencia SQLite. Incluye acciones con y sin atajo actual. Las teclas nativas de edición y navegación de celdas —Enter, Esc, Tab, flechas y edición de texto— permanecen reservadas.

## Checklist

- [x] Crear catálogo estable de acciones y persistencia global; prueba: lectura, escritura, valores predeterminados y datos inválidos cubiertos.
- [x] Crear formulario rápido para buscar, capturar, limpiar y restaurar atajos; prueba: validación visual y conflictos cubiertos.
- [x] Aplicar cambios en vivo a menús, barra, paneles y paleta de comandos; prueba: eventos reales y textos actualizados cubiertos.
- [x] Ejecutar regresiones; prueba: suite focalizada y suite completa aprobadas.

## Evidence

El catálogo identifica todas las acciones de menús, barra y navegación, incluidas las que no tenían atajo. La configuración global se guarda atómicamente en `atajos.sqlite3`, admite dos combinaciones por acción y detecta revisiones concurrentes. El formulario ordena y busca por acción o categoría, permite limpiar y restaurar valores, rechaza duplicados con nombres comprensibles y protege teclas nativas de edición. Treinta y dos pruebas de atajos aprobaron persistencia, conflictos, aplicación inmediata, actualización de ayuda, sustitución de `Ctrl+C` y reapertura de la aplicación. Otras 81 pruebas aprobaron barra minimalista, selección, niveles e importación/exportación Excel. La regresión completa aprobó 446 pruebas en 264,425 s; después del ajuste visual final, las 32 pruebas focalizadas volvieron a aprobar.

## Next

Abrir **Ayuda → Configurar atajos…** y validar visualmente una combinación personalizada.
