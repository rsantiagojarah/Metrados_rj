# Longitud y perímetro desde AutoCAD

## Intent
Agregar un comando rápido que sume longitudes de líneas, polilíneas, círculos y elipses seleccionados en AutoCAD 2021 y transfiera el resultado con un nombre a la partida activa de Metrados.

## Scope
Comando `MTRLONGITUD` sobre la conexión autenticada existente. Acepta curvas abiertas o cerradas, convierte la longitud desde las unidades métricas del DWG a metros y no modifica el dibujo. En partidas m crea cantidad directa; en m² y m³ coloca el valor en Largo y deja pendientes las demás entradas. No calcula áreas ni une o elimina tramos superpuestos.

## Checklist
- [x] Implementar cálculo y envío de longitud en AutoCAD; prueba: complemento compilado contra AutoCAD 2021.
- [x] Insertar el detalle según unidad m/m²/m³; prueba: casos de cálculo, pendientes y Ctrl+Z aprobados.
- [x] Validar protocolo, unidades y errores sin inserciones parciales; prueba: casos focalizados aprobados.
- [x] Ejecutar regresiones e instalar el complemento; prueba: suites, instalación y revisión final aprobadas.
- [x] Redondear la longitud transferida a dos decimales; prueba: valor CAD con más decimales se almacena y calcula con dos.

## Evidence
2026-09-27: `MTRLONGITUD` compiló contra las DLL instaladas de AutoCAD 2021 y quedó registrado en el manifiesto R24.0. La implementación usa la distancia acumulada entre los parámetros inicial y final de cada curva, convierte mm/cm/m/km a metros y suma líneas, polilíneas, círculos y elipses sin modificar el DWG.

Cuatro pruebas específicas comprobaron inserción en m, m² y m³, estados pendientes, rechazo de unidades incompatibles, validación y Ctrl+Z. La sonda .NET envió un `length_measurement` real por la conexión autenticada y recibió confirmación. La regresión completa aprobó 425 pruebas Python en 254,203 s y 21 pruebas Rust. El complemento quedó instalado en `%APPDATA%\Autodesk\ApplicationPlugins\Metrados.AutoCAD2021.bundle`; `git diff --check` no encontró errores, solo avisos existentes LF/CRLF.

2026-09-27: la longitud recibida ahora se redondea antes de almacenarse y calcularse. Cinco pruebas focalizadas aprobaron, incluido el caso `344.789697744 m` guardado como `344.79 m` y calculado con factor `2` como `689.58`; `git diff --check` no encontró errores.

## Next
Reiniciar Metrados y comprobar manualmente `MTRLONGITUD` con una entidad cuya longitud tenga más de dos decimales.
