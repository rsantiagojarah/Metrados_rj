"""Reproducible local timings; no fixed timing assertions and no user files touched.

Run with: .venv\Scripts\python.exe -B app/tests/benchmark_storage.py
"""
import json
import os
from pathlib import Path
from statistics import median
import tempfile
from time import perf_counter

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication

import metrado._enlace as engine
from metrado.database import read_database, write_database
from metrado.grid import SheetModel
from metrado.sheet import new_row


def timed(operation):
    start = perf_counter()
    result = operation()
    return result, round((perf_counter() - start) * 1000, 3)


def main():
    app = QApplication.instance() or QApplication([])
    rows = []
    for item in range(100):
        rows.append(new_row('item', f'{item + 1:02d}', f'Partida {item + 1}', 'm3', level=0))
        for detail in range(99):
            row = new_row('detail', description=f'Medición {detail + 1}', unit='m3', level=1)
            row['cells'][4:7] = ['10.5', '2', '0.3']
            rows.append(row)
    model, initialization = timed(lambda: SheetModel(engine, rows))
    edits, undos, redos = [], [], []
    for index in range(40):
        _, duration = timed(lambda: model.setData(model.index(1, 4), str(20 + index)))
        edits.append(duration)
        _, duration = timed(model.undo_stack.undo)
        undos.append(duration)
        _, duration = timed(model.undo_stack.redo)
        redos.append(duration)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'benchmark.metrado.db'
        revision, initial_save = timed(lambda: write_database(path, 'Prueba 10000 filas', model.rows))
        _, reopening = timed(lambda: read_database(path))
        model.setData(model.index(1, 4), '99')
        _, incremental_save = timed(lambda: write_database(path, 'Prueba 10000 filas', model.rows, revision))
        output = dict(rows=len(rows), initialization_ms=initialization,
                      edit_median_ms=median(edits), undo_median_ms=median(undos),
                      redo_median_ms=median(redos), initial_save_ms=initial_save,
                      reopen_ms=reopening, incremental_save_ms=incremental_save,
                      file_bytes=path.stat().st_size,
                      rows_per_edit_command=len(model.undo_stack.command(0).before))
        print(json.dumps(output, indent=2))
    model.undo_stack.clear()


if __name__ == '__main__':
    main()
