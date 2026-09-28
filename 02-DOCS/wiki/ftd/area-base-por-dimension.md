# Área base por dimensión en partidas m³

## Intent
Permitir calcular volúmenes como un área irregular multiplicada por una sola longitud, ancho, espesor o altura, tanto cuando el área llega desde `MTRAREA` como cuando el usuario la escribe directamente en la planilla.

## Scope
La columna Área será editable en detalles de partidas m³ y almacenará un área base en m². El volumen será área base × exactamente una dimensión entre Largo, Ancho y Alto × Elem. simil. × N.º de veces. `MTRAREA` podrá crear este detalle pendiente en partidas m³ sin preguntar la dimensión. No se agregan columnas ni se cambian anchos.

## Checklist
- [x] Incorporar el modo de cálculo manual y su validación; prueba: área con cada dimensión, estado pendiente y rechazo de múltiples dimensiones.
- [x] Extender `MTRAREA` a partidas m³; prueba: inserta área base sin dimensión y se completa desde la planilla.
- [x] Preservar edición, copiar/pegar, persistencia, Excel y Ctrl+Z; prueba: casos focalizados aprobados.
- [x] Compilar e instalar el complemento y ejecutar regresiones; prueba: compilación, instalación y suites aprobadas.

## Evidence
2026-09-27: cinco pruebas específicas verificaron entrada manual en Área, cálculo con Largo/Ancho/Alto, estado pendiente sin dimensión, rechazo de dimensiones múltiples, Ctrl+Z, portapapeles y persistencia SQLite/JSON/Excel. Seis pruebas de AutoCAD comprobaron que una partida m³ recibe el área sin dimensión y calcula al completarla en Metrados.

La regresión completa aprobó 420 pruebas Python en 165,236 s y 21 pruebas Rust. El complemento compiló contra AutoCAD 2021 y quedó reinstalado en `%APPDATA%\Autodesk\ApplicationPlugins\Metrados.AutoCAD2021.bundle`. `git diff --check` no encontró errores; solo avisos existentes de conversión LF/CRLF.

## Next
Reiniciar AutoCAD 2021 y comprobar manualmente un área conocida en partidas m² y m³.
