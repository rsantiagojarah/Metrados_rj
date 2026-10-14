# Reconstruir enlace Python 3.12

## Intent

Recompilar `metrado._enlace` para Python 3.12 en este equipo, para que la unidad `dia` y los factores negativos dejen de mostrar **Pendiente** al abrir la misma base que en la otra computadora.

## Scope

- En: reconstruir el módulo nativo con el `.venv` 3.12 y comprobar `ask_sheet_quantity('dia', …)`.
- Fuera: cambiar lógica de cálculo, firmar el complemento AutoCAD, subir el `.pyd` a GitHub (eso se pide aparte).

## Checklist

- [x] Reproducir el fallo: `dia` 1×1 devuelve `unknown_unit` con el `.pyd` 3.12 actual.
- [x] Reconstruir el paquete con `uv sync --reinstall-package metrado`.
- [x] Verificar: `dia` 1×1 → `1.0` y `und` −2×3 → `-6.0`.
- [ ] Reabrir la misma base con `Abrir Metrados.cmd`: `01.02.16.04` deja de mostrar Pendiente.

## Evidence

2026-09-28: el `.venv` es Python 3.12 y carga `app/metrado/_enlace.cp312-win_amd64.pyd` (commit `ceeb7bd`, 26/09). `ask_sheet_quantity('dia', [], 1, 1)` → `ValueError: unknown_unit`. `und` con −2×3 → `non_positive`. Eso explica **Pendiente** en `01.02.16.04` (unidad `dia`, 1×1).

2026-09-28: Metrados tenía el `.pyd` bloqueado (`pythonw -m metrado`). Se cerró, `uv sync --reinstall-package metrado` instaló `metrado==0.1.0`. Después: `dia` 1×1 → `1.0`, `dia` 1×6 → `6.0`, `und` −2×3 → `-6.0`. SHA256 del `.pyd` 3.12: `56F3DB1189CE2B2CD13B46DAD7340E652D4F3632BA0395D7B22E393D06C6DCA3`.

## Next

Reabrir la misma base con `Abrir Metrados.cmd` y comprobar que `01.02.16.04` muestre el total numérico en lugar de Pendiente.
