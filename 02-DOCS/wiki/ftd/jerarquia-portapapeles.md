# Jerarquía, movimientos y portapapeles

## Intent
Organizar títulos/subtítulos, partidas y detalles en la misma tabla, con teclado y acciones visibles.

## Scope
Subtítulos anidados, alta contextual, mover bloques arriba/abajo, Tab/Mayús+Tab para cambiar nivel y selector de destino. Copiar/pegar celdas y bloques completos. Mantener anchos y fórmulas, abrir proyectos anteriores y guardar la jerarquía. Trabajo en master por indicación expresa del usuario.

## Checklist
- [x] Renumerar ÍTEM por orden y jerarquía al crear, eliminar, pegar o mover bloques; comprobar prefijos de descendientes y ausencia de saltos.
- [x] Persistencia compatible y jerarquía validada con pruebas de guardado y apertura.
- [x] Alta, eliminación y movimientos conservan los descendientes y los totales (al trasladar detalles, se actualizan origen y destino).
- [x] Menús, botones, atajos y sangría visual verificados en Qt.
- [x] Portapapeles de celdas/bloques verificado, incluyendo acero y entradas inválidas.
- [x] Pruebas anteriores y nuevas aprobadas; comprobación visual y rendimiento.

## Evidence
Estado inicial: master, commit 711cc51; cambios previos en tres .pyc y documento codex-0-156-1.md preservados.

- Se mantiene master por petición del usuario. Tras la verificación, el usuario solicita registrar la implementación en un commit local; no solicita push.
- `.venv/Scripts/python.exe -B -m unittest discover -s app/tests -v`: 59 pruebas aprobadas en 31,931 s. Incluyen 36 anteriores y 23 de jerarquía/portapapeles.
- Pruebas Qt con eventos de teclado reales: Tab/Mayús+Tab, Alt+↑, Ctrl+C/V en celdas y filas, Ctrl+Mayús+C y pegado dentro del editor nativo. Seleccionar filas sigue sin recorrer toda la hoja.
- Pruebas del motor real: conservación de cantidades al mover subtítulos/partidas, actualización de totales al trasladar detalles, copia exacta de acero, rechazo atómico de pegados inválidos y protección de descendientes.
- Formato 2 con niveles explícitos, validación de parentesco y apertura compatible del formato 1. Pruebas de ida/vuelta de archivos y rechazo de niveles inválidos.
- Revisión visual de capturas Qt offscreen de la tabla y del selector de destino, con fuentes Segoe UI/Consolas cargadas para la captura. Sangría, menús y etiquetas legibles; columnas sin cambios de ancho. Capturas temporales `metrado_jerarquia_qa.png` y `metrado_destino_qa.png` en la carpeta temporal de Windows.
- Medición local con 10 000 filas (2 000 partidas y 8 000 detalles): carga del modelo 32,7 ms; mover un bloque y recalcular 137,4 ms; 10 000 consultas de selección 5,2 ms; pegar 12 celdas 144,2 ms. Mediciones de diagnóstico, no garantías para otros equipos.
- `git diff --check`: sin errores de espacios. Guía de menús, atajos, copia y persistencia actualizada en LEEME-Metrados.md.
- Corrección solicitada tras la captura ITEMS.png: los códigos dejan de conservarse al mover; se derivan del orden y parentesco. Títulos y partidas hermanos comparten secuencia, los descendientes heredan el prefijo actualizado y los detalles no consumen números. Aplicado a altas, bajas, pegado, cambio de nivel y movimientos.
- Verificación posterior: 65 pruebas aprobadas en 33,655 s, incluidas seis nuevas de numeración y reproducción del subtítulo de la captura con Mayús+Tab y Alt+↑. Se verifican persistencia, códigos consecutivos, descendientes y conservación de cantidades por descripción.
- Renumeración de 10 000 filas medida en 17,5 ms en este equipo. `git diff --check` sigue sin errores.

## Next
Reabrir la aplicación para utilizar los controles nuevos y la numeración automática. Publicar en el remoto solo si el usuario lo solicita.
