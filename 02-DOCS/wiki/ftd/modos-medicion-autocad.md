# Modos de medición desde AutoCAD

## Intent
Permitir que `MTRAREA` y `MTRLONGITUD` envíen un total único, cada medición individual con un nombre común o cada medición individual identificada por su layer de AutoCAD.

## Scope
Los dos comandos ofrecerán `Total`, `Individual` y `Layer`, con `Total` como opción predeterminada. Los modos individuales se transferirán en un solo mensaje y se insertarán en la partida activa como una sola operación deshacible. Para áreas, cada curva cerrada será una medición; las líneas conectadas se convertirán en contornos cerrados. En modo `Layer`, los contornos formados por líneas deberán cerrarse dentro de cada layer. No se agregan botones ni conexiones adicionales.

## Checklist
- [x] Incorporar los tres modos en ambos comandos; prueba: complemento AutoCAD 2021 compila y las opciones aparecen en el código registrado.
- [x] Transferir y validar lotes de mediciones de forma compatible con mensajes anteriores; prueba: casos de protocolo válidos e inválidos aprobados.
- [x] Insertar todas las filas con un solo Ctrl+Z; prueba: áreas y longitudes por nombre común y por layer aprobadas.
- [x] Ejecutar regresiones e instalar el complemento actualizado; prueba: suites relevantes, compilación e instalación aprobadas.

## Evidence
2026-09-27: el complemento compiló para AutoCAD 2021 con SHA256 `3F6B8C7F00CE766B63A44CC663721CE7B2695F7009180AD4AF8AF3B11F7B17E1`. Veintiséis pruebas focalizadas comprobaron mensajes simples y en lote, serialización real desde el cliente .NET, validación, nombres comunes y de layer, inserción múltiple y un solo Ctrl+Z.

La regresión completa aprobó 430 pruebas Python en 203,879 s y `git diff --check` no encontró errores. La instalación no pudo reemplazar la DLL porque el proceso `acad` mantiene cargado el complemento actual; el paquete nuevo quedó compilado en `target/autocad/Metrados.AutoCAD2021.bundle`.

Con AutoCAD cerrado, el complemento actualizado se instaló en `%APPDATA%\Autodesk\ApplicationPlugins\Metrados.AutoCAD2021.bundle`. La DLL compilada y la instalada tienen el mismo SHA256: `96B5F4B4A4E6FDF84632552D1F9D5A35251FEC3B76C9B4FB32F3C801732B9ECA`.

## Next
Abrir AutoCAD 2021 y comprobar manualmente `Total`, `Individual` y `Layer` en `MTRAREA` y `MTRLONGITUD`.
