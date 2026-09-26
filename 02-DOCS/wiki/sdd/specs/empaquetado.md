---
type: spec
title: Spec — Empaquetado de la aplicación
description: WHAT and WHY for launching the desktop takeoff sheet as one application.
tags: [sdd, spec]
timestamp: 2026-09-26T04:55:00Z
topic: sdd
slug: empaquetado
status: draft
---

# Spec — Empaquetado de la aplicación

> Slug: `empaquetado` · Status: draft · Created: 2026-09-25
> Inherits: [constitution](../constitution.md)
> Implementar solo después de [plantilla](plantilla.md).

## Problem & why

La plantilla y el cálculo pueden existir en el proyecto y aun así no formar una aplicación. Quien va a metrar necesita abrir un programa de escritorio y ver la hoja, no armar el entorno a mano cada vez.

## Cost of not building it

Cada uso empieza por preparar lenguajes, dependencias y la ventana por separado. Si un paso falla, la plantilla no abre y el metrado vuelve a la hoja externa.

## The cheapest alternative

Abrir la plantilla desde el entorno de desarrollo, con los comandos del proyecto a la vista. Sirve para quien ya construye el programa. No basta para usarlo como aplicación de escritorio.

## Goals

- Abrir una aplicación de escritorio muestra la plantilla.
- Esa aplicación usa el mismo cálculo que el dominio.
- Hace falta un solo modo de instalar las dependencias del proyecto, el que ya fija la constitución.

## Non-goals / out of scope

- Publicar en una tienda de aplicaciones.
- Actualizar la aplicación sola.
- Instalador gráfico para quien no tiene el proyecto.
- Cambiar fórmulas, columnas de la plantilla o el guardado.

## Users & context

Quien va a usar la plantilla en su equipo a partir de este proyecto y no quiere calcular las cantidades en otro programa.

## Behaviour

- Main path: después de instalar las dependencias del proyecto, abrir la aplicación muestra la plantilla vacía.
- La cantidad de una partida cargada en esa ventana es la del dominio.
- Error paths: si el cálculo no está disponible, la aplicación no abre una plantilla que multiplique por su cuenta. Avisa, en español, que no puede calcular.

## Acceptance criteria

- Given el proyecto con sus dependencias instaladas, When se abre la aplicación, Then aparece la plantilla vacía.
- Given esa ventana, unidad metro cúbico y medidas 2, 3 y 4, When se completan, Then la cantidad visible es 24.
- Given el cálculo no disponible, When se intenta abrir la aplicación, Then no aparece una hoja que calcule sola y hay un aviso en español.

## Points to clarify

- **decisión diferida** — instalador para un equipo que no tiene el proyecto. Fuera de este ciclo.
- **suposición tomada** — «abrir la aplicación» es un programa de escritorio de este repositorio, no una página web. *Base:* la constitución fija la interfaz de escritorio. *Riesgo:* si más adelante se quiere un instalador cerrado, hace falta otra spec.
