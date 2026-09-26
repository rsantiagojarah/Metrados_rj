# SDD decisions

## 2026-09-25 — Constitution v1.0.0

Opciones de stack: Python de escritorio, Python web local, u otro. Elección: aplicación de escritorio híbrida, Python con PySide6 en la interfaz y Rust en el motor de cantidades, integrado con PyO3/Maturin.

Opciones de calidad: tests solo en el cálculo, TDD en toda la lógica, o revisión manual. Elección: tests obligatorios en el motor de cantidades; la interfaz puede integrarse sin piso de cobertura en v1.

Motivo: las fórmulas quedan en un solo crate comprobable, y la plantilla no bloquea el primer entregable.

## 2026-09-25 — Constitution v1.1.0

Se añaden arquitectura y estilo, sin tocar los principios 1-11.

Elección: monolito modular (UI, motor, enlace), entrega por fases, SOLID, DRY y KISS, y tope de 300 líneas por archivo con excepción justificada en el propio archivo.

Motivo: legibilidad, mantenimiento y crecimiento por módulos, sin partir el escritorio en varios procesos. «Legible, mantenible y escalable» queda cubierto por esas reglas comprobables, no como un lema aparte.

## 2026-09-25 — sdd-init

No hay manifiesto ni runner de tests. `strict_tdd` queda en false. El modo de ejecución queda en `interactive` y el enrutado de modelos queda apagado.

## 2026-09-25 — uv

Opciones: uv, pip, o dejarlo abierto. Elección: uv. No se instalan las habilidades `python`, `rust` ni `testing-py`.

Motivo: un lockfile reproducible junto a Maturin. La habilidad de Rust del catálogo está orientada a servicios, no a PyO3.

## 2026-09-25 — Constitution v1.3.0

Opciones: nombrar el dominio en español dentro del código, o mantener identificadores en inglés y reservar el español para lo que se muestra. Elección: principio 20. El dominio define el significado; los identificadores son `Partida`, `Dimension` y `Quantity`; la interfaz no calcula.

Motivo: el principio 6 ya exige identificadores en inglés. Un tipo llamado en español chocaría con esa regla. El lenguaje del oficio sigue siendo la fuente del significado.

## 2026-09-25 — Dominio de cálculo

El crate `metrado_calculo` implementa el plan de `calculo-partida`. `cargo test` en `domain/` pasa con los ocho criterios. No hay pantalla ni enlace PyO3.

## 2026-09-25 — Fórmulas, enlace, plantilla y empaquetado

Las cuatro specs quedaron implementadas en este orden. La cantidad depende de la unidad (m, m², m³, und). `metrado._enlace` pide esa cantidad al dominio. La plantilla PySide6 la muestra. `uv run metrado` abre la aplicación.

## 2026-09-26 — bug: hook de memoria supera 5s (feature: hook-memory-timeout)

Repro: adaptador codex request con JSON por stdin y timeout 5000 ms, desde domain/src: ETIMEDOUT a 5010 ms. La prueba aislada con 900 archivos reproduce el fallo.
Cause: fingerprintFiles crea un proceso Git por archivo; capture vuelve a tomar la misma instantánea dos veces por evento.
Fix: calcular huellas con git hash-object --stdin-paths en lotes y evitar la instantánea duplicada, conservando huellas y conteos. La prueba de regresión pasa; 14 ejecuciones reales de los handlers terminan entre 1,3 y 2,6 s, dentro de los límites originales de 5/3 s.
Why missed: el costo de iniciar procesos por archivo queda oculto en repositorios pequeños; este proyecto tenía 886 archivos sin seguimiento. No se desactivó la memoria ni se aumentó el timeout.

## 2026-09-26 — bug: procesos auxiliares sin ventana oculta (feature: hook-hidden-windows)

Repro: instrumentación de execFileSync registra 24 llamadas de captura/recuperación sin windowsHide. Durante la reproducción se fuerza ocultamiento para no interrumpir al usuario.
Cause: el helper Git compartido omite windowsHide; el hashing en lote ya lo tenía. No se ha demostrado que este sea el único origen de las ventanas PowerShell reportadas.
Fix: añadir windowsHide: true al helper. Prueba de regresión: falla antes y pasa después, con 27 lanzamientos ocultos solicitados y memoria funcional. La prueba de rendimiento también pasa (870–915 ms por evento).
Why missed: redirigir stdout/stderr no equivale a solicitar que Windows oculte la consola. Pendiente confirmación visual del usuario; no se modificó el lanzador interno de Codex ni se desactivaron hooks.
