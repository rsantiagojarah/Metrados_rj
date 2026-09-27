# Catálogo de aceros y desarrollo automático

## Intent
Configurar pesos, ganchos de 90° y empalmes; aplicar ganchos a una selección y calcular empalmes por longitud. Proteger obras existentes mediante valores propios y actualización expresa.

## Scope
Tabla global editable y persistente, referencias iniciales E.060 para metrado, instantáneas por obra, aplicación de 1/2 ganchos, empalmes por tramos de 9 m, SQLite/JSON/portapapeles y deshacer. Sin validación estructural universal. Trabajo en master por instrucción del usuario; conservar cambios previos.

## Checklist
- [x] Referencias iniciales y reglas: pruebas de geometría y límites de 9/18/27 m.
- [x] Catálogo global y datos propios: pruebas de persistencia y ausencia de actualización implícita.
- [x] Formularios y acciones: pruebas de selección, aplicación y Ctrl+Z.
- [x] Compatibilidad SQLite/JSON/copiar-pegar: pruebas de migración y roundtrip.
- [x] Regresión completa y revisión visual.

## Evidence
2026-09-27: 238 tests completos aprobados en 33,513 s (motor Rust real y Qt sin pantalla); 33 pruebas específicas nuevas. Incluyen límites exactos y comas decimales, diámetro mixto, aplicación atómica, reemplazo, Ctrl+Z real, edición de longitud/diámetro, pegado, valores personalizados, cantidades directas, transición de unidad, protección de archivos antiguos y rechazo atómico de diámetros no configurados.

SQLite 4 probado: lectura de esquema 3 sin escritura y migración al guardar; pruebas existentes cubren esquemas 1/2. Catálogo/gancho en tablas relacionales, control de revisiones, guardado sin cambios y rollback por error simulado. JSON 6 y portapapeles 5 mantienen valores propios. Tabla global en SQLite independiente, guardado persistente y detección de modificación por otra ventana.

Se detectó en una prueba de 10 000 filas que el JSON con sangrías ocupaba 15,37 MB y no reabría por el límite de 10 MB. Se corrigió usando representación compacta para acero y protección antes de reemplazar el destino. La prueba de 10 000 filas ahora exporta, importa y decodifica el portapapeles correctamente.

Rendimiento observado (100 partidas, 9900 detalles de acero, sin repintado): inicializar 296 ms; editar 9,29 ms; deshacer 4,71 ms; guardar SQLite 1789 ms; abrir 1206 ms. Archivo SQLite de prueba: 14,05 MB. Datos sintéticos en directorio temporal; no se modificaron obras del usuario.

Revisión visual de planilla y ambos formularios con escala 125 %: controles y texto legibles, columnas y cabeceras alineadas. Capturas temporales: metrado_steel_sheet.png, metrado_steel_catalog.png y metrado_steel_hooks.png. Se tradujeron Guardar/Cancelar de los nuevos formularios. Git diff --check sin errores (solo avisos existentes de conversión LF/CRLF); rama master confirmada. Sin commit.

Referencias iniciales verificadas contra E.060 (publicación SENCICO): §7.1.2, tabla 7.1, §12.2 y §12.15; perfil y limitaciones documentados en el formulario y LEEME. Gancho longitudinal, no detalle sísmico universal; para 6 mm se señala la extrapolación. Los detalles heredados conservan sus valores hasta una actualización expresa o aplicación de ganchos sobre ellos.

## Next
Probar el flujo con una copia de una obra real. La tabla global no recalcula esa obra; usar Actualizar aceros de esta obra solo si se desea adoptar los valores. Commit únicamente cuando lo solicite el usuario.
