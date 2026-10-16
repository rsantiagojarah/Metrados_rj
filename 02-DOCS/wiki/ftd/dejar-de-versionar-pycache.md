# Dejar de versionar la caché de Python

## Intent
Sacar del repositorio los `.pyc` de `__pycache__`. Son caché que Python regenera al ejecutar el programa y no aportan al funcionamiento. `.gitignore` ya los ignora, pero Git sigue rastreando los que se commitearon antes.

## Scope
Dentro: dejar de rastrear los `.pyc` que ya están en el índice, conservando los archivos en disco. Fuera: no se toca código fuente, no se borra `__pycache__` del disco y no se reescribe el historial.

## Checklist
- [x] Dejar de rastrear cada `.pyc` versionado. Prueba: `git ls-files "*.pyc"` vacío y los archivos siguen en disco.
- [x] Confirmar que `.gitignore` los cubre. Prueba: tras el commit, `git status` no los lista como sin seguimiento.

## Evidence
`git rm --cached` sobre 9 archivos de `app/metrado/__pycache__/`. `git ls-files "*.pyc"` no devolvió rutas. Los `.pyc` siguen en disco (entre ellos `window.cpython-311.pyc`, `sheet.cpython-311.pyc` y el resto de la carpeta). `git check-ignore -v` señala `.gitignore:3:__pycache__/` para `window.cpython-311.pyc`. El índice marcaba los 9 como eliminados (`D`), sin borrarlos del disco. Commit `b690e83` en `master`. Después, `git status` no lista ningún `.pyc` y `git ls-files "*.pyc"` sigue vacío. `git push origin master` actualizó `https://github.com/rsantiagojarah/Metrados_rj.git` de `e15cb3c` a `b690e83`.

## Next
Nada pendiente de esta tarea.
