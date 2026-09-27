"""Regression guards on work performed, not machine-dependent timing limits."""
from contextlib import closing
from copy import deepcopy
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QCoreApplication, QEvent, QItemSelection, QItemSelectionModel, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
import metrado._enlace as engine
from metrado import steel_config as sc
from metrado.clipboard import ROW_MIME, decode_rows
from metrado.database import read_database, write_database
from metrado.grid import SheetModel
from metrado.identity import ensure_ids
from metrado.references import make_reference
from metrado.sheet import calculate, new_row, read_project, write_project
from metrado.steel_snapshot import freeze, CatalogSnapshot
from metrado.steel_store import CatalogStore
from metrado.window import PlantillaWindow

APP = QApplication.instance() or QApplication([])


class CountingEngine:
    def __init__(self):
        self.calls = 0

    def ask_sheet_quantity(self, *args):
        self.calls += 1
        return engine.ask_sheet_quantity(*args)

    def __getattr__(self, name):
        return getattr(engine, name)


def dataset(items=20, details=10, steel=False):
    rows = []
    catalog = sc.initial_catalog()
    for i in range(items):
        item = new_row('item', str(i), f'Partida {i}', 'kg' if steel else 'm3', 0)
        if steel:
            sc.adopt(item, catalog)
        rows.append(item)
        for j in range(details):
            row = new_row('detail', description=f'Detalle {j}', unit=item['cells'][2], level=1)
            if steel:
                row['cells'][4], row['cells'][7], row['cells'][10] = '10', '1/2"', '8'
                sc.adopt(row, catalog)
            else:
                row['cells'][4:7] = ['2', '3', '4']
            rows.append(row)
    ensure_ids(rows)
    return rows


class IncrementalCalculationTests(unittest.TestCase):
    def setUp(self):
        self.engine = CountingEngine()
        self.model = SheetModel(self.engine, dataset())
        self.model.set_reference(12, self.model.rows[0]['id'])
        self.model.set_reference(23, self.model.rows[11]['id'])

    def tearDown(self):
        self.model.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)

    def equivalent(self):
        values, errors = calculate(self.model.rows, engine)
        self.assertEqual(self.model.values, values)
        self.assertEqual(self.model.errors, errors)

    def test_unrelated_edit_only_computes_one_item_and_emits_local_range(self):
        self.engine.calls = 0
        changed = []
        self.model.dataChanged.connect(lambda first, last, *_: changed.append((first.row(), last.row())))
        graph = self.model._dependencies
        self.model.setData(self.model.index(34, 4), '5')
        self.assertEqual(self.engine.calls, 10)
        self.assertEqual(changed, [(33, 43)])
        self.assertIs(self.model._dependencies, graph)
        self.equivalent()

    def test_chain_recalculates_affected_items_once(self):
        self.engine.calls = 0
        self.model.setData(self.model.index(1, 4), '5')
        # 28 ordinary rows + two reference rows with three checked products each.
        self.assertEqual(self.engine.calls, 34)
        self.equivalent()
        self.model.undo_stack.undo()
        self.equivalent()
        self.model.undo_stack.redo()
        self.equivalent()

    def test_diamond_dependency_uses_topological_order(self):
        self.model.set_reference(34, self.model.rows[0]['id'])
        self.model.set_reference(24, self.model.rows[33]['id'])
        self.model.setData(self.model.index(1, 3), '-2')
        self.equivalent()
        self.model.set_swelling([1, 2], dict(factor='1.2', note=''))
        self.equivalent()

    def test_pending_unit_edit_and_undo_equal_full_calculation(self):
        for column, value in [(4, ''), (4, '8'), (3, '-1')]:
            self.model.setData(self.model.index(1, column), value)
            self.equivalent()
        self.model.setData(self.model.index(0, 2), 'm2')
        self.equivalent()
        self.model.undo_stack.undo()
        self.equivalent()

    def test_rename_updates_reference_descriptions_without_rebuilding_graph(self):
        graph = self.model._dependencies
        self.model.setData(self.model.index(0, 1), 'Excavación nueva')
        self.assertIn('Excavación nueva', self.model.data(self.model.index(12, 1)))
        self.assertIs(self.model._dependencies, graph)
        self.model.undo_stack.undo()
        self.assertIn('Partida 0', self.model.data(self.model.index(12, 1)))

    def test_structure_rebuilds_graph_and_missing_source_is_pending(self):
        before = self.model._dependencies
        self.model.replace(deepcopy(self.model.rows[11:]), 'eliminar')
        self.assertIsNot(self.model._dependencies, before)
        self.equivalent()
        self.model.undo_stack.undo()
        self.equivalent()


class SnapshotTests(unittest.TestCase):
    def test_equal_catalogs_share_immutable_snapshot(self):
        original = sc.initial_catalog()
        snapshot = freeze(original)
        self.assertIs(snapshot, freeze(deepcopy(original)))
        self.assertIs(snapshot, deepcopy(snapshot))
        with self.assertRaises(TypeError):
            snapshot['1/2"']['weight'] = '99'
        with self.assertRaises(TypeError):
            snapshot.update({})
        with self.assertRaises(TypeError):
            snapshot.__init__(original)
        with self.assertRaises(ValueError):
            CatalogSnapshot({})
        original['1/2"']['weight'] = '99'
        self.assertNotEqual(original, snapshot)
        self.assertIsNot(freeze(original), snapshot)

    def test_invalid_raw_catalog_is_not_hidden_by_cache(self):
        original = sc.initial_catalog()
        freeze(original)
        for bad in ('NaN', '0', '-1', '', None):
            original['1/2"']['weight'] = bad
            with self.assertRaises(ValueError):
                freeze(original)

    def test_model_undo_reuses_snapshot_and_global_changes_do_not_mutate_it(self):
        model = SheetModel(engine, dataset(2, 2, True))
        try:
            snapshot = model.rows[0]['steel_catalog']
            self.assertTrue(all(row['steel_catalog'] is snapshot for row in model.rows))
            model.setData(model.index(1, 4), '12')
            command = model.undo_stack.command(0)
            self.assertIs(command.before[0]['steel_catalog'], snapshot)
            self.assertIs(command.after[0]['steel_catalog'], snapshot)
            changed = model.steel_catalog_for(1)
            changed['1/2"']['weight'] = '99'
            model.update_steel_catalog(changed)
            self.assertNotEqual(model.rows[0]['steel_catalog'], snapshot)
            model.undo_stack.undo()
            self.assertIs(model.rows[0]['steel_catalog'], snapshot)
        finally:
            model.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)

    def test_storage_preserves_distinct_historical_catalogs_and_input(self):
        rows = dataset(2, 2, True)
        rows[1]['steel_catalog']['1/2"']['weight'] = '9.99'
        before = deepcopy(rows)
        with tempfile.TemporaryDirectory() as folder:
            db, json_path = Path(folder) / 'obra.db', Path(folder) / 'obra.json'
            rev = write_database(db, 'Obra', rows)
            self.assertEqual(rows, before)
            _, restored, _ = read_database(db)
            self.assertEqual(calculate(restored, engine), calculate(rows, engine))
            self.assertIs(restored[0]['steel_catalog'], restored[2]['steel_catalog'])
            self.assertNotEqual(restored[0]['steel_catalog'], restored[1]['steel_catalog'])
            self.assertEqual(write_database(db, 'Obra', restored, rev), rev)
            write_project(json_path, 'Obra', restored)
            self.assertEqual(calculate(read_project(json_path)[1], engine), calculate(rows, engine))
            with closing(sqlite3.connect(db)) as con:
                self.assertEqual(con.execute('PRAGMA user_version').fetchone()[0], 5)
                self.assertEqual(con.execute('SELECT count(*) FROM steel_catalog').fetchone()[0], 54)


class FastSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.window = PlantillaWindow(engine, CatalogStore(Path(self.temp.name) / 'catalog.db'))
        self.window._load('Selección', dataset(100, 99))
        self.window.show()
        self.window._select(1, 1)
        self.window.table.setFocus()
        APP.processEvents()

    def tearDown(self):
        with patch.object(self.window, '_can_discard', return_value=True):
            self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        self.temp.cleanup()

    def test_ctrl_a_only_selects_current_item_details(self):
        QTest.keyClick(self.window.table, Qt.Key_A, Qt.ControlModifier)
        self.assertEqual(self.window.table.selected_row_numbers(), set(range(1, 100)))
        selected = self.window.table.selectionModel().selection()
        self.assertEqual(len(selected), 1)
        self.assertEqual((selected[0].top(), selected[0].bottom()), (1, 99))

    def test_actions_do_not_enumerate_selected_cell_indexes(self):
        table = self.window.table
        with patch.object(table.selectionModel(), 'selectedIndexes', side_effect=AssertionError('Do not enumerate cells')):
            table.selectAll()
            self.window._selection_status()
            self.assertEqual(self.window._selected_rows()[0], set(range(1, 100)))
            self.window.copy_selection()
            block = decode_rows(APP.clipboard().mimeData().data(ROW_MIME))
            self.assertEqual(len(block), 99)

    def test_old_hidden_selection_is_filtered_using_ranges(self):
        model = self.window.model
        selection = QItemSelection(model.index(0, 0), model.index(9999, 13))
        self.window.table.selectionModel().select(selection, QItemSelectionModel.ClearAndSelect)
        self.assertEqual(self.window.table.selected_row_numbers(), set(range(1, 100)))

    def test_disjoint_cells_and_partial_rows_are_preserved(self):
        table = self.window.table
        table.selectionModel().clearSelection()
        for row, column in [(1, 3), (2, 4), (4, 7)]:
            table.selectionModel().select(self.window.model.index(row, column), QItemSelectionModel.Select)
        self.assertEqual(table.selected_row_numbers(), {1, 2, 4})
        self.assertFalse(table.selection_has_full_row())
