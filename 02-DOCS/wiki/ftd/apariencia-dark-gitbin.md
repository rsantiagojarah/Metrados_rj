# Apariencia oscura de Metrados basada en Gitbin

## Intent
Aplicar a Metrados el estilo oscuro, la tipografía y los estados visuales de Gitbin, según confirmación del usuario.

## Scope
Solo presentación en Python/PySide6: paleta, fuentes, bordes, botones, selección y campos. Gitbin es referencia de lectura. Se conservan 14 columnas, textos, anchos, alturas de filas, agrupación de encabezados, estructura, cálculos, persistencia y acciones.
Rama existente: feat/calculo-partida. Guía FTD usada para registrar el alcance y sus comprobaciones.

## Checklist
- [x] Corrección solicitada: reproducir cabecera de 34 px, barra plana de 44 px, símbolos sobre etiquetas de 9 px y banda de 30 px, verificando contra componentes renderizados de Gitbin.
- [x] Inspeccionar paleta y controles de Gitbin sin modificarlo.
- [x] Adaptar apariencia de Metrados y revisar captura nativa de Windows.
- [x] Comprobar edición, selección, campos, mensajes y cálculos con pruebas existentes.
- [x] Verificar integridad de Gitbin y de los archivos de cálculo/persistencia.

## Evidence
Corrección final: chrome.py adapta la cabecera, la pestaña de proyecto con línea turquesa, los botones planos (símbolo 14 px sobre etiqueta 9 px) y la banda contextual. Segoe UI se mide en píxeles como en el QML original. La tabla conserva 14 columnas, anchos, filas de 28 px y encabezado de 62 px; solo cambia la tipografía de presentación a 11 px.
15 pruebas integradas aprobadas, incluidas dos nuevas para clic en botón y atajo Ctrl+Enter. Captura nativa final revisada: 02-DOCS/attachments/planilla-gitbin-interfaz.png. Se revisó además la ventana de 900 px: acciones accesibles y tabla desplazable. Nueva comparación de hashes: Gitbin y motor/persistencia de Metrados idénticos.
Revisión del usuario: la primera adaptación no reproduce suficientemente los botones ni la jerarquía tipográfica. Se renderizaron exclusivamente AppHeader, ActionStrip y WorkspaceNav originales en una ventana visual aislada, sin lógica de Gitbin ni escritura en sus archivos. La fuente resuelta es Segoe UI, 11 px para texto normal; etiquetas de acciones de 9 px y símbolos de 14 px. Se conserva el alcance de presentación y la estructura de la tabla.
Fuentes de referencia: Gitbin Main.qml (#11151b), AppHeader.qml (#10141a), ActionStrip.qml (#191e26), HistoryButton.qml (botones #202d3a, hover #2c4051) y FormField.qml (entrada #0f141a, foco #25b9c4). Texto principal #e1e8f2; secundario #8e97a4. Gitbin usa fuente de sistema para la interfaz y Consolas para campos técnicos; Metrados adopta Segoe UI y Consolas para códigos/números.
Referencias inspeccionadas como texto; no se ejecuta Gitbin. Se guardaron hashes previos de sus fuentes de escritorio y de los archivos de cálculo y persistencia de Metrados.
2026-09-26: las 13 pruebas existentes de app/tests/test_sheet.py pasan, actualizando únicamente la expectativa de contraste al fondo oscuro. Se revisaron capturas con plataforma windows de la planilla, una celda en edición y el cuadro de cantidad directa. Captura final: 02-DOCS/attachments/planilla-dark-gitbin.png.
La ventana nativa confirmó 14 columnas y encabezado de 62 px. Las constantes de columnas y anchos y la altura de filas se conservaron. No se cambiaron acciones ni fórmulas.
Comparación SHA256 antes/después: idénticos todos los archivos Python/QML inspeccionados en gitbin/desktop y app/metrado/sheet.py, domain/src/lib.rs, domain/src/sheet.rs y enlace/src/lib.rs de Metrados.
Tema centralizado en app/metrado/theme.py: paleta oscura, Segoe UI para texto, Consolas para códigos y números, bordes y foco turquesa. El registro FTD documenta el alcance estrictamente visual.

## Next
Reabrir Metrados mediante Abrir Metrados.cmd para usar el tema oscuro.
