# Ítems y partidas sin sangría en el navegador

## Intent
Eliminar la sangría de ambas columnas, Ítem y Partidas, en todos los niveles.

## Scope
Ítem y Partidas alineados a la izquierda en todos los niveles, con los mismos anchos. Flechas de expansión al extremo derecho de la descripción, sin desplazar su texto. Sin cambios en códigos, jerarquía, cálculos ni datos. Trabajo en master según indicación del usuario; conservar cambios pendientes de importación Excel.

## Checklist
- [x] Códigos y descripciones alineados en todos los niveles y anchos intactos.
- [x] Flechas, selección y edición siguen funcionando.
- [x] Pruebas de navegación y revisión visual aprobadas.

## Evidence
El navegador usa un QTreeView con sangría de 14 píxeles por nivel en su columna de árbol predeterminada (Ítem). La columna Partidas ya es flexible y puede contener esa representación jerárquica.

La primera versión movía la sangría a Partidas; el usuario aclaró que tampoco la quiere allí. Versión corregida: sangría cero, ambas columnas alineadas y controles de expansión al extremo derecho de la descripción. No se cambiaron anchos, niveles ni códigos.

Pruebas: cuatro niveles con ambas columnas alineadas, Ítem de 94 px sin reducción por nivel, flechas clicables sin cambios en datos, navegación por teclado, doble clic en flecha sin abrir editor y resto de navegación/edición/selección múltiple/Undo. Suite completa: **367 pruebas OK en 37,567 s**. Después del ajuste final de dibujo se repitieron las **38 pruebas de navegación, OK en 6,747 s**. Render Qt final inspeccionado: ambas columnas sin desplazamiento por nivel, flechas visibles y fondos continuos. `git diff --check` sin errores. Sin commit.

## Next
Reabrir la aplicación para ver ambas columnas sin sangría; los datos guardados no necesitan migración.
