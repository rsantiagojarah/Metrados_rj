# FE también prorratea

## Intent

El mismo factor de esponjamiento reparte un volumen m³. Un relleno puede quedar 80 % en material de préstamo (FE 0,80) y 20 % en material propio (FE 0,20), sin una función nueva.

## Scope

- En: aceptar un FE finito y mayor que 0. Mayor que 1 esponja, como hasta ahora. Entre 0 y 1 multiplica el volumen del bloque por esa fracción. El diálogo, el aviso y la guía dicen cómo usarlo. Cero, negativos y no numéricos siguen rechazados.
- Fuera: un comando distinto de prorrateo, un segundo factor, o partir solo un detalle en dos filas. El reparto se hace copiando el volumen y aplicando un FE a cada copia.

El subtotal ya es la suma de los volúmenes originales por el FE. Solo cambia el mínimo admitido.

## Checklist

- [x] FE 0,80 y 0,20 prorratean y su suma recupera el volumen; prueba: el test del bloque da 19,20 y 4,80 sobre dos detalles de 24 m³.
- [x] Cero, negativo y no numérico siguen rechazados, y 1,20 sigue esponjando; prueba: la suite de FE pasa.
- [x] El diálogo acepta 0,80 y muestra el producto; prueba: el test de la ventana habilita Aceptar y muestra 38,40 m³.

## Evidence

2026-10-15: `uv run python -m unittest app.tests.test_swelling` terminó **38 pruebas OK** en 3,866 s. Incluye el reparto 0,80 / 0,20 (19,20 m³ + 4,80 m³ = 24 m³) y la vista previa del diálogo con 0,80 sobre 48 m³ = 38,40 m³. El rechazo de cero y de valores no numéricos, y el esponjamiento 1,20, siguen en esa misma suite.

## Next

Abrir Metrados, copiar el volumen del relleno en las dos partidas y aplicar FE 0,80 y 0,20.
