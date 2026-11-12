# Arranque visible y validación de muros sin repeticiones

## Intent

Mostrar Metrados mientras se recupera la última obra y evitar que la preparación de AutoCAD retrase la ventana. Reducir las validaciones idénticas de configuraciones de muro sin saltarse la validación de cada fila.

## Scope

- Ventana inicial vacía con «Abriendo obra…» y edición bloqueada durante la recuperación.
- Leer/validar la base en un hilo de trabajo; aplicar filas, calcular y habilitar la interfaz únicamente en el hilo de Qt.
- Preparar AutoCAD después de recuperar la obra, fuera del hilo de la interfaz. Cerrar durante el arranque cancela la entrega de resultados y limpia la conexión.
- Caché limitada a una validación de proyecto para tipos de muro idénticos. Validar siempre los identificadores, dimensiones y destinos de cada fila; no compartir diccionarios editables ni resultados calculados.
- Conservar la recuperación de sesión y rutas UNC ya implementadas en la rama actual. No modificar bases de usuario durante las mediciones.

## Checklist

- [x] Medición inicial sin perfilador con la misma base y condiciones de caché.
- [x] Pruebas de lectura lenta, ventana visible, eventos Qt atendidos y bloqueo de edición antes de cargar.
- [x] Pruebas de error/archivo ausente, cierre durante lectura y cierre durante preparación de AutoCAD.
- [x] Pruebas de caché por contenido, invalidación entre proyectos y rechazo de filas inválidas.
- [x] Pruebas relacionadas correctas y comparación de tiempos de ventana visible y obra lista.

## Evidence

- Diagnóstico previo con perfilador: base METRADOS_cf.db, 1.748 filas, 170 partidas. Lectura/validación 0,344 s; aplicación y cálculo 0,065 s; se validaron 667 configuraciones de muro por separado. Esta medición incluye el coste del perfilador y no se usará como base de porcentajes finales.
- Medición inicial sin perfilador: cinco procesos nuevos, Qt fuera de pantalla, misma base local y caché de disco caliente. Medianas: ventana pintada 0,36650 s; obra cargada y repintada 0,39494 s. Se excluyó el arranque real del puente CAD en ambos grupos para no alterar sesiones de usuario.
- Pruebas rojas observadas antes de implementar: cinco errores por ausencia del coordinador/resultado de sesión y dos fallos de caché (20 validaciones en lugar de una; cuatro en lugar de dos para dos proyectos separados). Los controles de filas y tipos inválidos ya rechazaban los datos incorrectos.
- Implementación: lectura/validación en un hilo Python; resultado entregado a Qt mediante señal encolada. El modelo, cálculo y widgets se actualizan en el hilo de la interfaz. La ventana se deshabilita antes de mostrarla y se habilita al aplicar el resultado. El puente CAD comienza en otro hilo después de recuperar la obra. Cerrar invalida los resultados tardíos y su limpieza se completa tras salir del bucle de eventos.
- Batería completa: 548 pruebas Python correctas en 33 módulos, con salida 0 de todos los procesos. Registros temporales en `tmp/startup-tests`. Tras el ajuste final del bloqueo previo a show(), se repitieron las 21 pruebas de arranque/sesión, todas correctas.
- El puente nativo de Windows se inició desde el hilo de preparación en una sesión temporal aislada; al cerrar se comprobaron servidor detenido y descriptor eliminado. Se probaron además un arranque CAD lento y un fallo de su inicialización.
- Comprobación de la base real: 667 validaciones de tipo de muro pasan a siete, manteniendo la validación de cada fila. La comparación con la validación sin caché produjo documentos, valores calculados y errores idénticos para las 1.748 filas, revisión 56.
- Medición final, cinco procesos y repintado incluido en ambas variantes: ventana pintada 0,23900 s; obra completamente presentada 0,37438 s. Reducciones aproximadas: 35 % para ver la ventana y 5 % para disponer de toda la obra. La medición intermedia de 0,34 s era previa al repintado y no se usa para el porcentaje final.
- Límites: cifras locales con caché caliente, sin medir latencia física del monitor ni tiempos del servidor. La espera de red se traslada fuera del hilo de Qt, pero su duración depende del servidor. No se modificó el motor Rust ni se escribió en la base del usuario.
- `git diff --check` correcto. La implementación conserva las correcciones de reapertura y UNC presentes en la rama `fix/ultima-obra-rutas-red`.

## Next

Reiniciar Metrados desde su acceso habitual para usar el arranque nuevo. Comprobar la ventana «Abriendo obra…» y que la última base queda disponible al terminar la carga.
