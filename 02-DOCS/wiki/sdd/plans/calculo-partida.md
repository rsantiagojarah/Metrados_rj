---
type: plan
title: Plan — Cálculo de una partida
description: The structure-level implementation plan for one work item's quantity.
tags: [sdd, plan]
timestamp: 2026-09-26T04:45:00Z
topic: sdd
slug: calculo-partida
status: approved
---

# Plan — Cálculo de una partida

> Spec: [../specs/calculo-partida.md](../specs/calculo-partida.md) · Constitution: [../constitution.md](../constitution.md) · Status: approved
> Last updated: 2026-09-25

## 0. Global Constraints

- **Stack:** Rust edition 2021. Ninguna fórmula de cantidad en Python.
- **Crate:** `metrado_calculo` en `domain/`. Sin dependencias externas.
- **Identificadores:** `Partida`, `Dimension`, `Quantity`. Un idioma (inglés) en el crate.
- **Cantidad:** producto de las medidas, en el mismo orden numérico en que se entregan. Una sola dimensión devuelve esa medida.
- **Medida válida:** número finito y estrictamente mayor que cero.
- **Nombre válido:** texto no vacío después de recortar espacios de los extremos. La comparación de nombres de dimensión usa ese texto recortado.
- **Archivos:** código escrito a mano, 300 líneas o menos por archivo.
- **Tests:** `cargo test` en `domain/` pasa antes de integrar.
- **Autoría git:** de la persona. Sin `Co-Authored-By` de una IA.
- **Fuera:** PySide6, PyO3, Maturin, `pyproject.toml`, persistencia, redondeo, fórmulas por unidad.

## 1. Context & constraints

- Criterios que fijan el diseño: spec, sección Acceptance criteria, los ocho escenarios.
- Constitución en juego: principios 2, 4, 6, 16, 17 y 20.
- Fuera de alcance que el diseño no debe absorber: pantalla, persistencia, varias partidas, catálogo de unidades.

## 2. Architecture

```text
[ Partida ] --holds--> [ Dimension ]
     |
     +--produces--> [ Quantity ]
```

- **Dimension** (internal) — nombre y medida válida. No calcula.
- **Quantity** (internal) — la cantidad ya obtenida. No acepta medidas sueltas.
- **Partida** (internal) — une el nombre con las dimensiones y produce la cantidad.
- **DomainError** (internal) — dice qué regla se rompió. No fabrica una cantidad.

**Top architectural decision:** un solo crate de dominio, sin repositorio ni eventos. Hay un solo llamador (quien pide la cantidad de una partida). Un repositorio sería una abstracción sin segundo uso (principio 16).

## 3. Interfaces & contracts

```text
Dimension.try_new(name: text, measure: number) -> Dimension | EmptyDimensionName | NonPositiveMeasure
  - precondition: name recortado no vacío; measure finita y > 0
  - postcondition: la dimensión guarda el nombre recortado y la medida

Partida.try_new(name: text, dimensions: list of Dimension) -> Partida | EmptyName | NoDimensions | DuplicateDimensionName
  - precondition: name recortado no vacío; al menos una dimensión; nombres de dimensión distintos
  - postcondition: quantity es el producto de las medidas
  - invariant: el orden de las dimensiones no cambia quantity

Partida.quantity() -> Quantity
Quantity.value() -> number
```

## 4. Data model & flow

**Entities**

- **Partida** — nombre; una o más Dimension; una Quantity derivada.
- **Dimension** — nombre; medida. Objeto de valor.
- **Quantity** — un número. Objeto de valor. No se construye desde fuera del dominio con una medida arbitraria en este ciclo: la produce Partida.

**Primary flow** (partida con tres medidas)

1. Cada medida entra por Dimension.try_new.
2. Partida.try_new recibe el nombre y las dimensiones.
3. Devuelve la partida cuya cantidad es el producto, o un error sin cantidad.

- Consistency boundaries: la partida y su cantidad se crean juntas. No hay estado a medias.
- Migration impact: none — no hay almacén.

## 5. Testing strategy

| Acceptance criterion | Level | Asserts | Fakes / mocks |
| --- | --- | --- | --- |
| Muro 2×3×4 = 24 | unit | quantity value is 24 | none |
| Una medida 5 = 5 | unit | quantity value is 5 | none |
| Mismo producto en otro orden | unit | both quantities equal | none |
| Nombre vacío | unit | EmptyName, no partida | none |
| Dimensión sin nombre | unit | EmptyDimensionName | none |
| Nombre de dimensión repetido | unit | DuplicateDimensionName | none |
| Sin dimensiones | unit | NoDimensions | none |
| Medida 0, negativa o no finita | unit | NonPositiveMeasure | none |

- No hay e2e: no hay pantalla en este ciclo.
- Nada se simula. El dominio es la dependencia real.

## 6. Sequencing & dependencies

1. Tests que fallan por ausencia del API — depends on: none — serial
2. Dimension y Quantity — depends on: 1 — serial
3. Partida y el producto — depends on: 2 — serial
4. `cargo test` completo — depends on: 3 — serial

- Parallel candidates: none. Comparten el mismo crate.
- Hard ordering: el test existe antes que la implementación que lo pone en verde.

## 7. Risks & open decisions

**Risks**

| Risk | Trigger | Impact | Mitigation / spike to retire it |
| --- | --- | --- | --- |
| El producto de números reales no es exacto para todos los decimales | medidas como 0.1 | una cantidad distinta al decimal esperado | este ciclo solo afirma productos exactos en los criterios; el redondeo queda diferido |
| Una fórmula por unidad invalida el producto | un spec posterior | hay que cambiar Partida | el spec ya lo deja fuera |

**Open decisions**

- none — el redondeo y las unidades están diferidos, no abiertos dentro de este ciclo.

## Tasks
<!-- generated by tasks on 2026-09-25; IDs are stable, do not renumber -->

El corte es secuencial porque los tres tipos comparten `domain/src` y el test público del crate.

| ID | [P] | Task | Done-check | Depends-on | Trace |
| --- | --- | --- | --- | --- | --- |
| T001 |  | Add failing tests for the eight acceptance cases | `cargo test --manifest-path domain/Cargo.toml` fails because `metrado_calculo` has no public API yet | — | spec Acceptance criteria |
| T002 |  | Implement Dimension and Quantity | `cargo test --manifest-path domain/Cargo.toml dimension` passes; measure 0, negative and NaN return NonPositiveMeasure; blank dimension name returns EmptyDimensionName | T001 | spec edge and error paths for a dimension |
| T003 |  | Implement Partida quantity as the product of measures | `cargo test --manifest-path domain/Cargo.toml` exits 0, including 2×3×4 = 24, a single measure 5, order independence, empty name, duplicate dimension name and no dimensions | T002 | spec Acceptance criteria |

**T002 — Interfaces**

- Consumes: nothing from another task
- Produces: `Dimension::try_new(name: &str, measure: f64) -> Result<Dimension, DomainError>`; `Quantity` readable with `value() -> f64`

**T003 — Interfaces**

- Consumes: `Dimension::try_new` from T002
- Produces: `Partida::try_new(name: &str, dimensions: Vec<Dimension>) -> Result<Partida, DomainError>`; `Partida::quantity(&self) -> Quantity`
