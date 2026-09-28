# Área total desde AutoCAD

## Intent
Permitir que el usuario seleccione una o varias líneas, polilíneas, circunferencias o elipses cerradas en AutoCAD 2021, asigne un nombre y transfiera la suma de sus áreas como un solo detalle a la partida activa de Metrados.

## Scope
Comando `MTRAREA` sobre la conexión local ya existente. Calcula sin modificar el DWG, exige contornos cerrados y unidades métricas definidas, suma las áreas aunque los contornos se superpongan y crea un detalle de cantidad directa únicamente en una partida de unidad m². No incluye unión geométrica de áreas superpuestas ni vínculo dinámico con cambios posteriores del dibujo.

## Checklist
- [x] Implementar selección, cálculo y captura de nombre en AutoCAD; prueba: complemento compilado contra AutoCAD 2021.
- [x] Enviar la medición por el protocolo autenticado existente; prueba: caso de protocolo aprobado y respuesta de error legible.
- [x] Insertar un único detalle deshacible en la partida activa; prueba: pruebas de inserción, validación y Ctrl+Z aprobadas.
- [x] Ejecutar regresión focalizada e instalar el complemento actualizado; prueba: suites aprobadas e instalación verificada.

## Evidence
2026-09-27: `MTRAREA` compiló sin errores contra las DLL instaladas de AutoCAD 2021. El comando filtra líneas, polilíneas 2D, círculos y elipses; rechaza geometría abierta/no plana, convierte unidades métricas del dibujo a m², solicita un nombre y envía una sola medición sin modificar el DWG.

Quince pruebas focalizadas aprobaron, incluidas la serialización real del cliente .NET, autenticación, reconexión, despacho desde el hilo de la tubería al hilo Qt, validación de unidad m², inserción atómica y Ctrl+Z. La regresión completa aprobó 414 pruebas Python en 319,694 s y 21 pruebas Rust. `git diff --check` no encontró errores. El paquete actualizado quedó instalado en `%APPDATA%\Autodesk\ApplicationPlugins\Metrados.AutoCAD2021.bundle`.

## Next
Reiniciar AutoCAD 2021 y ejecutar una comprobación manual de `MTRAREA` con un contorno conocido.
