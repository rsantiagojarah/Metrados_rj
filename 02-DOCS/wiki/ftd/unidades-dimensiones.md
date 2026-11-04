# Cálculo de unidades por dimensiones

## Intent
Permitir metrados en unidades con largo, ancho y factor editables, para ladrillos de losas.

## Scope
Cálculo, edición en la planilla y exportación a Excel; se conserva el comportamiento anterior de filas sin dimensiones.

## Checklist
- [x] Calcular unidades con tres factores, conservando filas históricas sin dimensiones.
- [x] Validar edición, exportación y apertura de bases anteriores.
- [x] Añadir las cuatro partidas de losa a los archivos existentes y reconciliar los paños.

## Evidence
Las pruebas de unidades (2), exportación (33), cálculo (36), referencias (33), historial de base (34) y cantidades directas (6) pasaron. Los 31 paños de concreto, encofrado y ladrillos concilian en 156,25 m²; se aplica el factor de 9 ladrillos/m² solicitado. El reporte exportado muestra las fórmulas por dimensión y la base pasa la verificación de integridad.

## Next
Abrir la base actualizada en Metrados para revisar o ajustar las partidas.
