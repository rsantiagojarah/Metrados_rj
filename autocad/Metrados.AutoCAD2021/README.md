# Complemento de conexión para AutoCAD 2021

Este componente mantiene una única conexión local con Metrados, comprueba su disponibilidad y transfiere mediciones de área sin modificar el dibujo.

## Compilar

Ejecuta `build.ps1`. El script usa las bibliotecas de la instalación local de AutoCAD 2021 y genera el paquete en `target/autocad/Metrados.AutoCAD2021.bundle`.

## Instalar

Cierra AutoCAD y ejecuta `install.ps1`. El paquete se copia al directorio de complementos del usuario actual. No modifica `TRUSTEDPATHS`, `SECURELOAD` ni otras preferencias de seguridad de AutoCAD.

El binario de desarrollo no tiene firma digital. AutoCAD puede solicitar una confirmación al cargarlo; no se desactiva esa protección. Una distribución a otros equipos debe firmarse con un certificado de publicación válido.

## Comprobar

1. Abre Metrados.
2. Abre AutoCAD 2021.
3. Ejecuta `MTRCONEXION` en la línea de comandos de AutoCAD.
4. Debe aparecer `Metrados conectado correctamente`.

## Medir áreas

1. Deja activa en Metrados una partida cuya unidad sea `m2` o `m3`.
2. Ejecuta `MTRAREA` en AutoCAD.
3. Elige `Total`, `Individual` o `Layer`; Enter conserva `Total`.
4. Selecciona líneas que cierren contornos, polilíneas 2D cerradas, círculos o elipses completas.
5. En `Total` e `Individual`, confirma la selección y escribe el nombre del detalle.

`Total` suma los contornos y crea una sola fila; `Individual` crea una fila por contorno con el nombre escrito; `Layer` crea una fila por contorno usando el nombre de su layer. En modo `Layer`, las líneas sueltas que formen un contorno deben cerrarlo dentro del mismo layer. Todo el lote se deshace con un solo Ctrl+Z. En `m2`, el área es la cantidad directa; en `m3`, queda en la columna Área para que el usuario complete después exactamente una dimensión en Largo, Ancho o Alto. El dibujo debe tener unidades métricas definidas mediante `UNITS`. El comando no modifica el DWG; los contornos superpuestos se suman y la medición transferida no queda vinculada a cambios posteriores del dibujo.

## Medir longitudes y perímetros

1. Deja activa en Metrados una partida `m`, `m2` o `m3`.
2. Ejecuta `MTRLONGITUD` en AutoCAD.
3. Elige `Total`, `Individual` o `Layer`; Enter conserva `Total`.
4. Selecciona líneas, polilíneas, círculos o elipses, abiertas o cerradas.
5. En `Total` e `Individual`, confirma y escribe el nombre del detalle.

`Total` suma longitudes y perímetros en una fila; `Individual` crea una fila por objeto con el nombre escrito; `Layer` crea una fila por objeto usando el nombre de su layer. Todo el lote se deshace con un solo Ctrl+Z. En una partida `m` crea cantidades directas; en `m2` o `m3` coloca cada resultado en Largo y deja las demás dimensiones para que el usuario las complete en Metrados.

## Metrar acero distribuido

1. Deja activa en Metrados una partida cuya unidad sea `kg`.
2. Ejecuta `MTRACERO` en AutoCAD.
3. Para el largo de cada barra, marca dos puntos o escribe una distancia.
4. Para la distancia de distribución, marca otros dos puntos o escribe una distancia.
5. Selecciona un texto simple o múltiple, por ejemplo `1Ø1"@0.275`.
6. Escribe la descripción del detalle.

AutoCAD solo captura esos datos. Metrados interpreta el texto usando el formato global editable en `Acero > Formato de distribución CAD…`, calcula las barras como `multiplicador × (redondeo hacia arriba(distribución / espaciamiento) + 1)` y utiliza el catálogo guardado con la partida para diámetro, empalme y peso. El detalle se crea sin ganchos; estos se aplican después desde Metrados. El sufijo de cantidad y diámetro se añade automáticamente y toda la inserción se deshace con un solo Ctrl+Z.

Los diagnósticos, sin credenciales ni contenido del dibujo, se guardan en `%LOCALAPPDATA%\Metrados\bridge`.
