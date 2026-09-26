---
type: spec
title: Spec — Fórmulas por unidad
description: WHAT and WHY for a quantity that depends on the work item's unit.
tags: [sdd, spec]
timestamp: 2026-09-26T04:55:00Z
topic: sdd
slug: formulas-por-unidad
status: draft
---

# Spec — Fórmulas por unidad

> Slug: `formulas-por-unidad` · Status: draft · Created: 2026-09-25
> Inherits: [constitution](../constitution.md)
> Implementar esta primero. Sustituye la regla «producto de cualquier lista de medidas» de [calculo-partida](calculo-partida.md).

## Problem & why

Una partida de obra no se metra siempre igual. Un muro en metros cúbicos usa tres medidas; un tubo en metros lineales usa una; un accesorio en unidades usa un conteo. Multiplicar todas las medidas que haya produce una cantidad equivocada en cuanto la unidad no es cúbica.

## Cost of not building it

La plantilla mostraría 24 para un muro de 2 × 3 × 4 aunque la partida se pague por metro lineal. Ese número entra al presupuesto y no hay forma de distinguir el error de un metrado bien hecho.

## The cheapest alternative

Dejar la regla actual (producto de las medidas que el usuario escriba) y pedirle que ponga 1 en las medidas que no aplican. No basta: un 1 olvidado cambia la cantidad, y la unidad de la partida no obliga a las medidas que de verdad corresponden.

## Goals

- Cada partida declara una unidad y solo acepta las medidas de esa unidad.
- La cantidad sale de la fórmula de esa unidad y de ninguna otra.
- La regla anterior, producto de una lista libre de medidas, deja de ser válida.

## Non-goals / out of scope

- Pantalla, teclado y textos de la plantilla.
- Guardar partidas.
- Redondeo a un número fijo de decimales.
- Unidades distintas de metro lineal, metro cuadrado, metro cúbico y unidad.
- Empaquetar la aplicación.

## Users & context

Quien metra una partida y ya sabe si se mide en m, m², m³ o und. Quiere la cantidad que corresponde a esa unidad.

## Behaviour

- Main path: la partida tiene nombre, unidad y las medidas que esa unidad exige. La cantidad es el resultado de la fórmula de la unidad.
- Fórmulas:
  - Metro lineal (m): una medida, longitud. Cantidad = longitud.
  - Metro cuadrado (m²): largo y ancho. Cantidad = largo × ancho.
  - Metro cúbico (m³): largo, ancho y alto. Cantidad = largo × ancho × alto.
  - Unidad (und): una medida, veces. Cantidad = veces.
- Edge cases: los nombres de las medidas llevan espacios al borde que no cuentan. El orden en que se entregan no cambia la cantidad si cada medida viene con su nombre.
- Error paths: no hay cantidad si falta la unidad, si falta una medida que la unidad exige, si sobra una medida que la unidad no usa, si el nombre de la partida queda vacío, o si una medida es cero, negativa o no es un número finito. El fallo dice qué regla se rompió y no inventa una cantidad.

## Acceptance criteria

- Given unidad m³ y medidas largo 2, ancho 3 y alto 4, When se pide la cantidad, Then la cantidad es 24.
- Given unidad m y longitud 5, When se pide la cantidad, Then la cantidad es 5.
- Given unidad m² y medidas largo 2 y ancho 3, When se pide la cantidad, Then la cantidad es 6.
- Given unidad und y veces 4, When se pide la cantidad, Then la cantidad es 4.
- Given unidad m y además un ancho, When se intenta crear la partida, Then no hay cantidad y el fallo es medida de más.
- Given unidad m³ sin alto, When se intenta crear la partida, Then no hay cantidad y el fallo es medida faltante.
- Given una medida 0, negativa o no finita, When se intenta crear esa medida, Then no entra en la partida.
- Given un nombre de partida vacío, When se intenta crear la partida, Then no hay cantidad.

## Points to clarify

- **suposición tomada** — las únicas unidades de este ciclo son m, m², m³ y und, con las fórmulas de arriba. *Base:* son las cuatro unidades con las que se metra casi toda partida de obra antes de llegar a kilogramos o global. *Riesgo:* si el proyecto usa kg o glb, hay que ampliar esta spec antes de implementar.
- **decisión diferida** — redondeo. Fuera de este ciclo.
- **decisión diferida** — pantalla y guardado. Son otras specs.
