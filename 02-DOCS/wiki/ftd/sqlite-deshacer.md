# SQLite y deshacer

## Intent
Guardar cada obra en una base SQLite consultable, con identidades estables y relaciones jerárquicas, e incorporar deshacer/rehacer eficiente.

## Scope
SQLite local por obra, versión de esquema, transacciones y guardado incremental; importar JSON sin sobrescribirlo y exportarlo para intercambio. Historial de sesión mediante comandos Qt: celdas, unidades, cantidades directas, bloques, niveles, pegado y nombre de obra. Guardar conserva el historial y marca el estado limpio; abrir/nuevo lo reinicia. No incluye servidor multiusuario, autoguardado ni historial después de cerrar. Trabajo en master por instrucción expresa del usuario; preservar cambios previos del desagregado.

## Checklist
- [x] Persistencia relacional y compatibilidad: pruebas de ida/vuelta, IDs, importación y consultas.
- [x] Guardado seguro: pruebas de reversión transaccional, versión desconocida y conflicto de revisiones.
- [x] Deshacer/rehacer: pruebas de celdas, acero, unidades, grupos, movimientos, pegado, título y estado guardado.
- [x] Integración: atajos reales, abrir/guardar/importar/exportar, anchos y regresiones.
- [x] Rendimiento: medición reproducible con 10 000 filas; documentación de límites.

## Evidence
- Verificación final: `.venv\Scripts\python.exe -B -m unittest discover -s app/tests -q`: **118 pruebas, OK, 55.030 s, salida 0**. Incluye las 34 pruebas nuevas de SQLite/historial y las 84 regresiones anteriores. `git diff --check` sin errores de espacios; solo avisos de normalización LF/CRLF. Rama comprobada: master.
- Pruebas SQL verifican relaciones, `integrity_check=ok`, claves foráneas, rechazo de versiones extrañas e IDs duplicados. Un disparador de auditoría confirmó exactamente un UPDATE para una celda modificada; guardar sin cambios no modifica filas ni revisión.
- Falla inyectada durante una actualización: permanecieron intactos filas, título y revisión anteriores. Falla durante la creación inicial: no quedó una base parcial ni temporales. Segunda ventana con revisión distinta: rechazo sin sobrescribir cambios ajenos.
- QtTest ejercitó Ctrl+Z, Ctrl+Y, Ctrl+Mayús+Z y Ctrl+S con editor activo; deshacer de texto no afectó prematuramente al documento. Pegado de bloque usa IDs nuevos que se mantienen al rehacer. Guardar conserva el historial y su punto limpio. Límite probado: 200 operaciones.
- Se corrigió en pruebas una omisión al cerrar las conexiones SQL del propio test; las conexiones de producción ya usaban cierre explícito. También se limpió el portapapeles de la prueba al finalizar (el portapapeles offscreen retenía el proceso). Se eliminaron referencias circulares en comandos y se protegieron señales durante destrucción Qt.
- `benchmark_storage.py`: 10 000 filas (100 partidas, 99 detalles por partida). Inicialización 95.263 ms, edición mediana 0.662 ms, deshacer 0.4775 ms, rehacer 0.478 ms, primer guardado 274.497 ms, reapertura 108.773 ms, guardado incremental 194.930 ms. Base de 2 510 848 bytes; cada comando de celda conserva una sola fila anterior. Valores locales, sin repintado ni garantías universales de tiempo.
- Captura offscreen `metrado_sqlite_history_qa.png` en la carpeta temporal de Windows revisada visualmente: botones Deshacer/Rehacer legibles, jerarquía del desagregado y columnas conservadas. No se alteró ninguna obra real.
- LEEME actualizado con migración, exportación, esquema consultable, atajos y límites. Sin autoguardado ni historial persistente entre sesiones. SQLite local por obra; no se implementó un servidor compartido.

## Next
Commit de cierre solicitado por el usuario junto con títulos del desagregado y sufijo de acero. Verificación conjunta: 135 pruebas aprobadas en 45.652 s, salida 0. Preparar el commit local en master; sin push.
