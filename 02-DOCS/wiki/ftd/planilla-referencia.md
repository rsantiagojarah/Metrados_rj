# Planilla de metrados con formato de referencia

## Intent
Convertir el formulario existente en una tabla de escritorio con las 14 columnas, encabezados agrupados y jerarquía de la imagen del usuario.

## Scope
Interfaz PySide6 existente; capítulos, partidas y detalles; cálculo Rust de dimensiones, repeticiones y totales por partida; guardar/abrir JSON; ejemplo cargable. Sin presupuesto ni instalador independiente.
Trabajo en la rama existente feat/calculo-partida, conservando archivos previos no versionados.
Límites secuenciales: dominio de cálculo, enlace PyO3, interfaz de planilla y persistencia.

## Checklist
- [x] Cálculo de longitud, área, volumen, peso y conteos con factores: pruebas Rust.
- [x] Enlace compilado: comprobación con Python.
- [x] Tabla de 14 columnas y cabeceras agrupadas: render de la ventana.
- [x] Alta/edición/eliminación de filas y totales: comprobación integrada.
- [x] Guardar/abrir sin perder datos y protección de cambios: pruebas.

## Evidence
Inspección inicial: interfaz de formularios, PySide6 instalado y motor Rust con m, m2, m3 y und. Perfil existente: mixed/L2.
2026-09-26: cargo test pasa 17 pruebas (5 nuevas y 12 existentes). Incluye fórmulas, factores, cantidades directas, datos no finitos y desbordamiento.
uv sync --offline --reinstall-package metrado reconstruyó e instaló el enlace local correctamente.
app/tests/test_sheet.py: 13 pruebas integradas pasan con el motor real; edición mediante F2/Enter, cambios de unidad, inserción, eliminación, datos inválidos, guardado/reapertura, fallo de escritura conservando el archivo anterior, cancelación de cambios y contraste del texto. Total: 30 pruebas aprobadas junto al motor.
Render PySide6 revisado visualmente: 14 columnas, encabezados grises agrupados, capítulos rojos, partidas en negrita, detalles azules, líneas punteadas; ejemplo con 6 meses, 80 m y 837,13 m2. Para la captura offscreen se cargaron explícitamente las fuentes de Windows.
Decisiones: se mantiene Python/PySide6 + Rust/PyO3; nueva API de planilla conserva la API previa. Los totales incompletos muestran Pendiente. La persistencia JSON guarda entradas y recalcula resultados al abrir. No se suma entre unidades diferentes.
Además de las pruebas fuera de pantalla, se abrió y capturó la ventana nativa: platform=windows, visible=True, capture=True. La revisión visual detectó y corrigió el contraste bajo el tema oscuro de Windows; la captura final revisada está en 02-DOCS/attachments/planilla-referencia-20260926.png. No se realizó un recorrido manual exhaustivo ni se creó un instalador autónomo.
El formato Rust de los archivos modificados pasa rustfmt --check. El chequeo global también detectó formato previo pendiente en domain/tests/calculo_partida.rs, que no se modificó.

## Next
Abrir Abrir Metrados.cmd y revisar la planilla con el usuario usando sus datos reales.
