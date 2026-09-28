# Acero distribuido desde AutoCAD

## Intent
Crear `MTRACERO` para capturar en AutoCAD el largo de una barra, la distancia donde se distribuye y un texto de distribución configurable, y generar el detalle completo en la partida de acero activa usando exclusivamente los cálculos existentes de Metrados.

## Scope
Cada distancia podrá obtenerse con dos puntos o escribirse como número. El usuario seleccionará un texto como `1Ø1"@0.275` y escribirá la descripción del detalle. Metrados interpretará multiplicador, diámetro y espaciamiento mediante una configuración global editable; calculará barras como `multiplicador × (ceil(distribución / espaciamiento) + 1)`, dejará ganchos en cero, aplicará empalmes y peso según el catálogo histórico de la partida y añadirá el sufijo existente. No se incorporan cálculos de acero en AutoCAD ni vínculos vivos con el DWG.

## Checklist
- [x] Configurar y validar formatos globales de texto; prueba: diálogo y persistencia cubiertos.
- [x] Capturar distancias, texto y descripción con `MTRACERO`; prueba: complemento AutoCAD 2021 compila.
- [x] Validar el mensaje y crear un detalle de acero con cálculos existentes; prueba: cantidad, sufijo, empalmes, peso y Ctrl+Z aprobados.
- [x] Ejecutar regresiones e instalar el complemento; prueba: suites, compilación, hash e instalación aprobados.

## Evidence
2026-09-27: el formato global admite marcadores seguros y editables `{multiplicador}`, `{diametro}` y `{espaciamiento}`, con vista previa antes de guardar. Reconoce también el código de diámetro `%%c` de AutoCAD. La configuración se guarda en el SQLite global de aceros sin modificar obras ni catálogos históricos.

El comando `MTRACERO` compiló para AutoCAD 2021 y la sonda .NET transmitió largo, distancia de distribución, texto y descripción mediante la conexión existente. Cincuenta y cinco pruebas focalizadas aprobaron interpretación, redondeo hacia arriba, persistencia, protocolo, sufijo, cero ganchos, empalmes, peso histórico y Ctrl+Z. La regresión completa aprobó 439 pruebas Python en 202,651 s; `git diff --check` no encontró errores. El paquete actualizado se instaló en `%APPDATA%\Autodesk\ApplicationPlugins\Metrados.AutoCAD2021.bundle`; la DLL compilada y la instalada coinciden con SHA256 `606EF5FE5E0DDC4AB6B4F5FAE4553372CDA4D682F954A0AA2F059C925D3D606A`.

## Next
Abrir Metrados y AutoCAD 2021 y probar `MTRACERO` manualmente con una distribución conocida.
