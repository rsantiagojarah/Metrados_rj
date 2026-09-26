---
type: spec
title: Spec — Enlace del cálculo
description: WHAT and WHY for the desktop app to ask the domain for a quantity.
tags: [sdd, spec]
timestamp: 2026-09-26T04:55:00Z
topic: sdd
slug: enlace-calculo
status: draft
---

# Spec — Enlace del cálculo

> Slug: `enlace-calculo` · Status: draft · Created: 2026-09-25
> Inherits: [constitution](../constitution.md)
> Implementar solo después de [formulas-por-unidad](formulas-por-unidad.md). No incluye la pantalla.

## Problem & why

La cantidad ya tiene una sola fórmula en el dominio. Si la aplicación de escritorio vuelve a multiplicar las medidas por su cuenta, aparecen dos resultados para la misma partida y el de la pantalla puede mentir.

## Cost of not building it

La plantilla, cuando exista, no podrá mostrar la cantidad del dominio. Quien la construya copiará la fórmula en la interfaz. A partir de ahí, un cambio de unidad hay que hacerlo dos veces y una de las dos se olvida.

## The cheapest alternative

Calcular en la interfaz y no conectar el dominio. Cubre la demo de una pantalla. No basta: rompe la regla de una sola fórmula y deja el dominio sin uso.

## Goals

- La aplicación puede pedir la cantidad de una partida al dominio.
- El número que recibe es el mismo que devuelve el dominio para esas medidas y esa unidad.
- La aplicación no multiplica medidas por su cuenta.

## Non-goals / out of scope

- Dibujar la plantilla, los textos visibles y el recorrido con teclado.
- Guardar partidas.
- Instalar o empaquetar la aplicación para quien no tiene el proyecto abierto.
- Cambiar las fórmulas. Eso ya está en `formulas-por-unidad`.

## Users & context

Quien va a registrar partidas en la aplicación de escritorio. Todavía no necesita la pantalla terminada: necesita que la aplicación sepa preguntar la cantidad.

## Behaviour

- Main path: la aplicación entrega nombre, unidad y las medidas de esa unidad, y recibe la cantidad del dominio.
- Edge cases: la misma partida preguntada dos veces devuelve la misma cantidad.
- Error paths: si el dominio rechaza la partida, la aplicación recibe el fallo y no sustituye la cantidad por un producto propio.

## Acceptance criteria

- Given unidad m³ y medidas largo 2, ancho 3 y alto 4, When la aplicación pide la cantidad, Then recibe 24, igual que el dominio.
- Given unidad m y longitud 5, When la aplicación pide la cantidad, Then recibe 5.
- Given una medida negativa, When la aplicación pide la cantidad, Then recibe el fallo y no hay cantidad.
- Given las mismas medidas, When se comparan la respuesta de la aplicación y la del dominio, Then son iguales.
- Given el código que pide la cantidad, When se revisa, Then no contiene una segunda multiplicación de largo, ancho, alto o veces.

## Points to clarify

- **decisión diferida** — el aspecto de la ventana. Es la spec `plantilla`.
- **suposición tomada** — el enlace expone una sola operación: pedir la cantidad de una partida. *Base:* la plantilla solo necesita ese resultado. *Riesgo:* si más adelante hay que listar partidas guardadas, esta operación no alcanza y hace falta otra spec.
