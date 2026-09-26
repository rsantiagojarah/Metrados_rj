---
type: spec
title: Spec — Plantilla de metrados
description: WHAT and WHY for the desktop sheet where a user records work items.
tags: [sdd, spec]
timestamp: 2026-09-26T04:55:00Z
topic: sdd
slug: plantilla
status: draft
---

# Spec — Plantilla de metrados

> Slug: `plantilla` · Status: draft · Created: 2026-09-25
> Inherits: [constitution](../constitution.md)
> Implementar solo después de [enlace-calculo](enlace-calculo.md).

## Problem & why

Quien metra anota varias partidas, cada una con su unidad y sus medidas, y necesita ver la cantidad al lado. Sin una plantilla tiene que llamar al cálculo partida por partida, fuera de una hoja de trabajo.

## Cost of not building it

El cálculo existe y no hay dónde usarlo. El metrado sigue en una hoja externa y la aplicación no cumple el objetivo de registrar partidas y ver cantidades.

## The cheapest alternative

Una hoja de cálculo con las fórmulas a mano. Cubre el registro. No basta: no usa la cantidad única del dominio y no obliga a las medidas de cada unidad.

## Goals

- Registrar varias partidas en una misma hoja.
- Elegir la unidad y escribir solo las medidas que esa unidad pide.
- Ver la cantidad de cada partida, calculada por el dominio, sin poder editarla a mano.

## Non-goals / out of scope

- Guardar la hoja al cerrar la aplicación.
- Totales de obra, presupuestos y reportes.
- Redondeo distinto del número que ya devuelve el dominio.
- Instalar la aplicación en otro equipo. Eso es `empaquetado`.

## Users & context

Quien tiene las medidas tomadas y quiere dejarlas anotadas en la plantilla, partida por partida, y leer la cantidad.

## Behaviour

- Main path: la hoja empieza vacía. Quien agrega una partida escribe el nombre, elige la unidad (m, m², m³ o und) y llena las medidas de esa unidad. La cantidad aparece al completar las medidas y no se puede editar.
- Al cambiar la unidad, la plantilla muestra solo las medidas de esa unidad y vuelve a pedir la cantidad.
- Edge cases: puede haber más de una partida. Cada una muestra su propia cantidad. El recorrido principal (agregar partida, pasar de un campo a otro, elegir unidad, escribir medidas y leer la cantidad) se hace sin ratón.
- Error paths: una medida vacía, cero, negativa o no numérica no produce cantidad y el mensaje está en español. La fila no muestra un número inventado.
- Textos visibles, en español: partida, unidad, longitud, largo, ancho, alto, veces y cantidad. Los nombres de unidad visibles son metro lineal, metro cuadrado, metro cúbico y unidad.

## Acceptance criteria

- Given una hoja vacía, When se abre la plantilla, Then no hay partidas y se puede agregar la primera sin ratón.
- Given unidad metro cúbico, largo 2, ancho 3 y alto 4, When se completan esas medidas, Then la cantidad visible es 24 y el campo cantidad no se puede editar.
- Given unidad metro lineal y longitud 5, When se completa, Then la cantidad visible es 5 y no se piden ancho ni alto.
- Given una partida ya cargada, When se cambia la unidad a metro cuadrado, Then se piden largo y ancho, y la cantidad anterior desaparece hasta completarlas.
- Given dos partidas válidas, When ambas están en la hoja, Then cada una muestra su cantidad.
- Given una medida negativa, When se sale de ese campo, Then no hay cantidad y hay un mensaje en español.
- Given el recorrido principal, When se usa solo el teclado, Then se puede agregar la partida, elegir la unidad, escribir las medidas y leer la cantidad.

## Points to clarify

- **suposición tomada** — la hoja vive solo mientras la aplicación está abierta. *Base:* guardar es otra spec. *Riesgo:* si cerrar y volver a abrir debe conservar las partidas, esta spec no alcanza.
- **decisión diferida** — total al pie de la hoja. No forma parte de este ciclo.
