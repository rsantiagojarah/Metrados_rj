# Acero: distribución de la referencia

## Intent
Alinear las columnas de acero con la captura proporcionada por el usuario.

## Scope
Encabezado superior contextual al seleccionar acero, sin encabezados dentro de las partidas, tres dimensiones, número de veces, longitud acumulada, kg/m y kg. Diámetro seleccionable entre Lon. y kg/m. Conservar datos guardados y pesos calculados.

## Checklist
- [x] Lista de diámetros entre Lon. y kg/m, recálculo y persistencia: prueba de selección real.
- [x] Encabezado superior cambia al seleccionar acero y vuelve al general en otras partidas; sin encabezados locales: pruebas y captura.
- [x] Longitud acumulada y número de veces: pruebas con motor real.
- [x] Edición y guardado compatibles: regresiones.

## Evidence
Copia previa para reversión: C:\Users\CARMEN\AppData\Local\Temp\metrado-antes-referencia-eiq7bhgp

29 pruebas aprobadas en 3,407 s, incluido editor de N.º de veces, diámetro en descripción, guardado, cantidad directa y encabezado local. git diff --check sin errores.
Comparación directa con la copia previa: datos del ejemplo idénticos, 18 pesos idénticos y total idéntico. La longitud mostrada ahora es acumulada, calculada mediante el motor existente.
Captura revisada: 02-DOCS/attachments/acero-referencia.png.
El usuario confirmó que solo requiere la distribución y que deben conservarse datos y cálculos actuales.

Ajuste posterior solicitado por el usuario: encabezado superior contextual restaurado; eliminados los encabezados locales y su código de dibujo. Filas de altura uniforme. La selección actualiza títulos y anchos sin modificar datos ni marcar la planilla como editada.
30 pruebas aprobadas en 3,618 s y git diff --check sin errores. Captura revisada: 02-DOCS/attachments/acero-cabecera-superior.png.

31 pruebas aprobadas en 4,223 s tras añadir Diámetro entre Lon. y kg/m. La prueba abre el selector con F2, cambia de 1 pulgada a media pulgada, comprueba peso dividido entre cuatro, longitud y factores intactos, sincronización de la anotación y persistencia al guardar/abrir. git diff --check sin errores.

## Next
Reabrir Abrir Metrados.cmd y seleccionar una partida o detalle de acero para ver las columnas superiores correspondientes.
