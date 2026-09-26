---
type: spec
title: Spec — Cálculo de una partida
description: WHAT and WHY for calculating one work item's quantity from its dimensions.
tags: [sdd, spec]
timestamp: 2026-09-26T04:40:00Z
topic: sdd
slug: calculo-partida
status: planned
---

# Spec — Cálculo de una partida

> Slug: `calculo-partida` · Status: planned · Created: 2026-09-25
> Inherits: [constitution](../constitution.md)
> Approval: approved in autopilot by the accepted implementation plan (2026-09-25).

## Problem & why

Quien metra una partida anota largo, ancho, alto u otras medidas y necesita una cantidad. Si esa cuenta vive en una hoja o en la cabeza, dos personas obtienen dos resultados para las mismas medidas y nadie puede señalar cuál es el del proyecto.

## Cost of not building it

Cada partida se sigue calculando a mano. Un error de multiplicación pasa a la cantidad de obra y no hay una comprobación repetible que lo detenga. El costo es concreto: cantidades distintas para las mismas medidas, descubiertas tarde, cuando ya se presupuestó o se ejecutó.

## The cheapest alternative

Una hoja de cálculo con una celda de producto cubre el caso de una sola partida y una sola persona. No basta: no rechaza una medida nula o negativa, no impide dos dimensiones con el mismo nombre y no deja un resultado que el resto del sistema pueda pedir sin volver a multiplicar.

## Goals

- Dadas las medidas de una partida, hay una sola cantidad.
- Una medida que no es un número positivo no entra en la cuenta.
- Una partida sin medidas no produce cantidad.

## Non-goals / out of scope

- Pantalla, teclado y textos visibles de la plantilla.
- Guardar partidas entre sesiones.
- Varias partidas a la vez, totales de obra o presupuestos.
- Fórmulas distintas según la unidad (metro lineal, metro cuadrado, unidad, kilogramo).
- Redondeo a un número fijo de decimales.
- Empaquetar o exponer el cálculo a otro lenguaje.

## Users & context

Quien registra el metrado de una partida de obra. Tiene las medidas tomadas y quiere la cantidad de esa partida, no un presupuesto ni un plano.

## Behaviour

- Main path: quien entrega el nombre de la partida y una o más dimensiones, cada una con nombre y medida positiva, obtiene una cantidad igual al producto de esas medidas.
- Edge cases: una sola dimensión produce una cantidad igual a esa medida. El orden de las dimensiones no cambia la cantidad. Los espacios al borde del nombre no forman parte del nombre.
- Error paths: no hay cantidad si el nombre de la partida queda vacío, si una dimensión no tiene nombre, si dos dimensiones comparten el mismo nombre, si no hay ninguna dimensión, o si una medida es cero, negativa o no es un número finito. El fallo dice qué regla se rompió y no inventa una cantidad.

## Acceptance criteria

- Given una partida llamada «Muro» con dimensiones largo 2, ancho 3 y alto 4, When se pide la cantidad, Then la cantidad es 24.
- Given una partida con una sola dimensión de medida 5, When se pide la cantidad, Then la cantidad es 5.
- Given las mismas medidas en distinto orden, When se pide la cantidad, Then las dos cantidades son iguales.
- Given un nombre de partida formado solo por espacios, When se intenta crear la partida, Then no hay cantidad y el fallo es el nombre vacío.
- Given una dimensión sin nombre, When se intenta usarla, Then no entra en la partida.
- Given dos dimensiones con el mismo nombre, When se intenta crear la partida, Then no hay cantidad y el fallo es el nombre repetido.
- Given una partida sin dimensiones, When se pide la cantidad, Then no hay cantidad.
- Given una medida 0, negativa o no finita, When se intenta crear la dimensión, Then no entra en la partida.

## Points to clarify

- **suposición tomada** — la cantidad es el producto de las medidas. *Base:* el plan aprobado pide dimensiones de entrada y una cantidad de salida, y el producto es la regla mínima que hace binarios los criterios. *Riesgo:* si una partida debe usar una fórmula por unidad, estos criterios cambian. *Clarify 2026-09-25:* se mantiene en este ciclo; la fórmula por unidad está en Non-goals.
- **decisión diferida** — redondeo y catálogo de unidades. Fuera de este ciclo a propósito.
- **decisión diferida** — pantalla, persistencia y enlace con otro lenguaje. Declarados en la fase y en Non-goals.

## Clarifications

- 2026-09-25 — La suposición del producto queda validada para este ciclo. No se reabre hasta un spec de fórmulas por unidad.
