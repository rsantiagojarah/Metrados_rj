"""Synthetic UI/storage benchmark; temporary files only, no timing assertions.

Run from the project root: .venv\Scripts\python.exe -B app/tests/benchmark_performance.py
Includes Qt event processing; offscreen rendering is not physical display latency.
"""
import json
import os
from pathlib import Path
from statistics import median
import tempfile
from time import perf_counter

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
import metrado._enlace as engine
from metrado import steel_config as sc
from metrado.database import read_database, write_database
from metrado.identity import ensure_ids
from metrado.references import make_reference
from metrado.sheet import new_row
from metrado.steel_store import CatalogStore
from metrado.window import PlantillaWindow


class CountingEngine:
    def __init__(self):
        self.calls = 0

    def ask_sheet_quantity(self, *args):
        self.calls += 1
        return engine.ask_sheet_quantity(*args)

    def __getattr__(self, name):
        return getattr(engine, name)


def dataset(mode):
    rows, catalog = [], sc.initial_catalog()
    for i in range(100):
        unit = 'kg' if mode == 'steel' else 'm3'
        item = new_row('item', str(i + 1), f'Partida {i + 1}', unit, 0)
        rows.append(item)
        for j in range(99):
            row = new_row('detail', description=f'Detalle {j + 1}', unit=unit, level=1)
            if mode == 'steel':
                row['cells'][4], row['cells'][7], row['cells'][10] = '10', '1/2"', '8'
                sc.adopt(row, catalog)
            else:
                row['cells'][4:7] = ['2', '3', '4']
            rows.append(row)
        if mode == 'steel':
            sc.adopt(item, catalog)
    ensure_ids(rows)
    if mode in ('references', 'one_reference'):
        for i in (range(1, 100) if mode == 'references' else [1]):
            rows[i * 100 + 1]['reference'] = make_reference(rows[0], 'm3')
    return rows


def main():
    app = QApplication.instance() or QApplication([])
    for name in ('segoeui.ttf', 'consola.ttf', 'seguisym.ttf'):
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + name)

    def timed(operation):
        app.processEvents()
        start = perf_counter()
        result = operation()
        app.processEvents()
        return result, round((perf_counter() - start) * 1000, 3)

    for mode in ('ordinary', 'one_reference', 'references', 'steel'):
        with tempfile.TemporaryDirectory() as folder:
            counter = CountingEngine()
            window = PlantillaWindow(counter, CatalogStore(Path(folder) / 'catalog.db'))
            rows = dataset(mode)
            window.resize(1600, 900)
            window.show()
            _, load_ms = timed(lambda: window._load('Benchmark', rows))
            window._select(1, 1)
            window.table.setFocus()
            edits, calls, selections, switches, undos = [], [], [], [], []
            edit_row = 201 if mode == 'one_reference' else 1
            for i in range(5):
                window._select(edit_row, 4)
                app.processEvents()
                counter.calls = 0
                _, duration = timed(lambda: window.model.setData(window.model.index(edit_row, 4), str(20 + i)))
                edits.append(duration)
                calls.append(counter.calls)
                _, duration = timed(window.model.undo_stack.undo)
                undos.append(duration)
                window.model.undo_stack.redo()
                _, duration = timed(lambda: window._select(301 if i % 2 else 201, 1))
                switches.append(duration)
                window.table.clearSelection()
                _, duration = timed(window.table.selectAll)
                selections.append(duration)
            path = Path(folder) / 'benchmark.metrado.db'
            revision, save_ms = timed(lambda: write_database(path, 'Benchmark', window.model.rows))
            _, read_ms = timed(lambda: read_database(path))
            window.model.setData(window.model.index(edit_row, 4), '99')
            _, save_edit_ms = timed(lambda: write_database(path, 'Benchmark', window.model.rows, revision))
            print(json.dumps(dict(mode=mode, rows=len(rows), load_ms=load_ms,
                                  edit_ms=median(edits), edit_engine_calls=median(calls),
                                  undo_ms=median(undos), switch_ms=median(switches),
                                  select_all_ms=median(selections), first_save_ms=save_ms,
                                  reopen_ms=read_ms, save_one_edit_ms=save_edit_ms,
                                  file_bytes=path.stat().st_size)), flush=True)
            window.model.undo_stack.setClean()
            window.close()
            window.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


if __name__ == '__main__':
    main()
