---
type: constitution
title: Metrados — Constitution
description: The non-negotiable principles every rsc-sdd phase obeys.
tags: [sdd, constitution]
timestamp: 2026-09-26T04:40:00Z
topic: sdd
version: v1.3.0
---

# Metrados — Constitution

> Version: v1.3.0 · Ratified: 2026-09-25 · Last amended: 2026-09-25
> Principios no negociables. El detalle de stack vive en `02-DOCS/wiki/stack/*`.

## 1. Stack canon

1. La interfaz es una aplicación de escritorio en Python 3.11 o superior con PySide6. Cambiar el toolkit de UI es una enmienda MAJOR.
2. El motor de cantidades es un crate Rust (edition 2021). Ninguna fórmula de metrado se implementa en Python.
3. La integración es PyO3, empaquetada con Maturin. `pyproject.toml` declara a Maturin como build backend y `Cargo.lock` va en el repositorio.

## 2. Quality bar

4. Todo cambio en el crate de cálculo incluye o actualiza un test que afirma el resultado de la cantidad. `cargo test` pasa antes de integrar.
5. La interfaz PySide6 y el pegamento PyO3 no tienen piso de cobertura en v1. Un cambio que no toca el motor puede integrarse sin tests nuevos.

## 3. Conventions

6. Los textos visibles de la plantilla están en español (partida, dimensión, cantidad). Los identificadores de código están en inglés, un idioma por crate.
7. La plantilla permite registrar partidas, editar dimensiones y ver la cantidad calculada sin ratón.

## 4. Branching & shipping

8. El trabajo va en una rama. El merge a la rama por defecto es mediante pull request.
9. La autoría git es de la persona. No hay `Co-Authored-By` de una IA ni pie «generated with». Lo exige la fase `ship`.

## 5. Security

10. Ningún secreto se commitea. Los secretos viven en `01-TOOLS/<provider>/.env`, ignorado por git.

## 6. Knowledge

11. Cada decisión relevante se anexa en `02-DOCS/wiki/sdd/decisions.md` con fecha, opciones y motivo.

## 7. Architecture

12. El producto es un monolito modular: una sola aplicación de escritorio, con tres módulos de responsabilidad (UI PySide6, motor Rust, enlace PyO3). Añadir otro ejecutable o servicio es una enmienda MAJOR.
13. El desarrollo es por fases. Cada fase declara por escrito, en `02-DOCS`, un solo límite de módulo antes de abrir el código del siguiente.
14. SOLID, comprobable así: un módulo tiene un motivo de cambio; la UI no depende de internos de Rust fuera de la API PyO3 publicada; el motor no depende de PySide6.
15. DRY, junto con el principio 2: cada fórmula de cantidad tiene una sola implementación, en el crate Rust. Una segunda copia falla la revisión.
16. KISS: no se añade una abstracción (trait, wrapper o capa) sin dos llamadores concretos en el repositorio, salvo una justificación escrita junto a esa abstracción.
17. Un archivo de código escrito a mano no supera 300 líneas. Si las supera, el primer bloque de comentario dice la justificación técnica y el corte que se descartó. Quedan exentos el código generado, los lockfiles y lo vendorizado.
18. Separación de responsabilidades: el layout de widgets, las fórmulas de cantidad y el enlace PyO3 no conviven en el mismo archivo.

## 8. Python toolchain

19. El gestor de paquetes de Python es uv. Cuando exista el paquete, `uv.lock` va en el repositorio y uv es el único instalador. pip y Poetry no son el flujo del proyecto.

## 9. Domain language

20. El significado de partida, dimensión y cantidad lo define solo el dominio de cálculo. En código los identificadores son `Partida`, `Dimension` y `Quantity`. La interfaz muestra «partida», «dimensión» y «cantidad» y no calcula la cantidad.

## Definition of Done

- [ ] Si el diff toca el motor Rust, `cargo test` pasa (principio 4).
- [ ] No aparece una fórmula de cantidad en Python (principio 2).
- [ ] Textos nuevos de la plantilla están en español y el flujo principal se recorre con teclado (principios 6 y 7).
- [ ] Rama, PR y autoría humana (principios 8 y 9).
- [ ] Sin secretos en el diff (principio 10).
- [ ] El diff no abre un segundo ejecutable ni mezcla UI, fórmulas y enlace PyO3 en el mismo archivo (principios 12 y 18).
- [ ] Cada archivo de código escrito a mano queda en 300 líneas o menos, o trae en el primer comentario la justificación técnica (principio 17).
- [ ] Una abstracción nueva tiene dos llamadores o una justificación escrita al lado (principio 16).
- [ ] Cuando exista el paquete Python, `uv.lock` está en el repositorio (principio 19).
- [ ] La cantidad la produce el dominio de cálculo; la interfaz no la recalcula (principio 20).

## Amendment log

- v1.0.0 — 2026-09-25 — Ratificada. Interfaz Python + PySide6, motor Rust vía PyO3/Maturin, tests obligatorios solo en el cálculo.
- v1.1.0 — 2026-09-25 — Añadidos los principios 12-18: monolito modular por fases, SOLID, DRY, KISS, tope de 300 líneas y separación de archivos. Los principios 1-11 no cambian.
- v1.2.0 — 2026-09-25 — Añadido el principio 19: uv es el gestor de paquetes de Python. Los principios 1-18 no cambian.
- v1.3.0 — 2026-09-25 — Añadido el principio 20: el dominio de cálculo define partida, dimensión y cantidad. Los identificadores de código siguen en inglés. Los principios 1-19 no cambian.
