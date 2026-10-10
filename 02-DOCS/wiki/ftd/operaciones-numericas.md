# Operaciones en entradas numéricas

## Intent
Aceptar +, -, *, /, ^ y paréntesis; almacenar únicamente el resultado al confirmar.

## Scope
Planilla, cantidad directa y cuadros numéricos de conversión, esponjamiento y acero. Conservar restricciones actuales y no interpretar descripciones, códigos ni diámetros. Evaluador aritmético limitado, sin eval ni ejecución de código.

## Checklist
- [x] Probar precedencia, potencias, coma decimal, errores y límites.
- [x] Integrar planilla, deshacer, avisos y cantidad directa sin perder valores ante errores.
- [x] Integrar cuadros numéricos y comprobar que guardan solo números.
- [x] Ejecutar regresión.

## Evidence
La planilla usa valores decimales en dimensiones y factores. Los selectores de catálogo y ganchos no son entradas numéricas libres.
Evaluador con árbol sintáctico limitado, Decimal, longitud máxima, límite de nodos y exponentes; rechaza nombres, llamadas, atributos, operaciones no admitidas y resultados no reales/no finitos.
10 pruebas nuevas aprobadas: aritmética, restricciones, errores, editor, Enter/Tab reales en la tabla, guardado, deshacer, área base, cantidad directa, diámetros y cuadros auxiliares.
Suite completa: 461 pruebas, 460 aprobadas y una expectativa antigua incompatible con el comportamiento pedido (admitía «pendiente» como longitud). Se actualizó esa prueba para verificar rechazo sin cambios y, después, vaciado de celda para dejar pendiente. Las 33 pruebas de acero volvieron a ejecutarse y aprobaron. La décima prueba nueva de teclado se ejecutó adicionalmente tras iniciar la suite completa.
No se han añadido restricciones de enteros donde la aplicación admite decimales. El evaluador soporta validación entera para editores que la requieran.

## Next
Terminado. Reabrir la aplicación y escribir una operación en cualquier entrada numérica editable.
