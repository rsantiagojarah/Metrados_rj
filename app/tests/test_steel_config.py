"""Steel defaults, project isolation, exact splice boundaries, persistence and UI."""
from contextlib import closing
from copy import deepcopy
from decimal import Decimal
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import Qt, QItemSelectionModel
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QMessageBox
import metrado._enlace as engine
from metrado import steel_config as sc
from metrado.clipboard import ROW_MIME, decode_rows, encode_rows, insert_rows
from metrado.database import ConflictError, SCHEMA_VERSION, read_database, write_database
from metrado.grid import SheetModel
from metrado.hierarchy import materialize
from metrado.sheet import calculate, new_row, read_project, steel_detail, validate_project, write_project
from metrado.steel_dialog import CatalogDialog, HooksDialog
from metrado.steel_store import CatalogStore
from metrado.window import PlantillaWindow

APP = QApplication.instance() or QApplication([])


def sample(managed=True):
    rows = materialize([new_row('item', description='Acero', unit='kg'),
        steel_detail('Barra A', 2, 8.5, .4, .7, '1/2"', 3),
        steel_detail('Barra B', 1, 18, .6, 1.2, '3/4"', 2)])
    if managed:
        for row in rows:
            sc.adopt(row, sc.initial_catalog())
    return rows


class SteelRulesTests(unittest.TestCase):
    def test_initial_reference_geometry_and_weights(self):
        catalog = sc.initial_catalog()
        sc.validate_catalog(catalog)
        self.assertEqual(catalog['1/2"']['hook'], '0.23')
        self.assertEqual(catalog['1"']['hook'], '0.45')
        self.assertEqual(catalog['1 3/8"']['hook'], '0.67')
        self.assertAlmostEqual(float(catalog['3/4"']['weight']), 2.237, places=3)
        self.assertGreaterEqual(float(catalog['6mm']['lap']), .39)

    def test_exact_nine_meter_boundaries(self):
        row = sample()[1]
        for length, expected in [('8.99', 0), ('9', 0), ('9.000000001', 1),
                                  ('18', 1), ('18.000000001', 2), ('27', 2), ('27.01', 3)]:
            with self.subTest(length=length):
                row['cells'][4] = length
                self.assertEqual(sc.dimensions(row)[2], expected)

    def test_hooks_count_but_laps_and_repetitions_do_not_count(self):
        row = sample()[1]
        row['cells'][4] = '8,5'
        row['steel_hooks'] = dict(count=2, override='0,25')
        self.assertEqual(sc.dimensions(row), (Decimal('.50'), Decimal(0), 0))
        row['steel_hooks']['override'] = '.26'
        hook, lap, count = sc.dimensions(row)
        self.assertEqual(count, 1)
        row['cells'][3], row['cells'][9], row['cells'][10] = '100', '200', '300'
        row['steel_catalog']['1/2"']['lap'] = '100'
        self.assertEqual(sc.dimensions(row)[2], 1)

    def test_catalog_rejects_invalid_entries(self):
        for bad in ('0', '-1', 'NaN', 'Infinity', '', 'abc', '1e999'):
            for field in sc.FIELDS:
                with self.subTest(bad=bad, field=field):
                    catalog = sc.initial_catalog()
                    catalog['6mm'][field] = bad
                    with self.assertRaises(ValueError):
                        sc.validate_catalog(catalog)
        with self.assertRaises(ValueError):
            sc.validate_catalog({})

    def test_row_metadata_validation(self):
        for change in (lambda r: r.update(steel_hooks={'count': True, 'override': None}),
                       lambda r: r.update(steel_hooks={'count': 3, 'override': None}),
                       lambda r: r.update(steel_hooks={'count': 1, 'override': 'NaN'}),
                       lambda r: r.pop('steel_catalog'),
                       lambda r: r['cells'].__setitem__(2, 'm3')):
            row = sample()[1]
            change(row)
            with self.assertRaises(ValueError):
                sc.validate_row(row)

    def test_calculation_uses_snapshot_weight_and_ignores_stale_dimension_cache(self):
        rows = sample()
        row = rows[1]
        row['steel_catalog']['1/2"']['weight'] = '2'
        row['cells'][5:7] = ['999', '999']
        values, errors = calculate(rows, engine)
        self.assertFalse(errors)
        self.assertEqual(values[(1, 11)], 2)
        self.assertEqual(values[(1, 12)], 2 * 8.5 * 3 * 2)
        self.assertEqual(row['cells'][5:7], ['999', '999'])  # Pure calculation


class SteelModelTests(unittest.TestCase):
    def setUp(self):
        self.model = SheetModel(engine, sample())
        self.model.steel_defaults = sc.initial_catalog()

    def tearDown(self):
        self.model.deleteLater()

    def test_batch_hooks_mixed_diameters_and_single_undo(self):
        before = deepcopy(self.model.rows)
        self.model.apply_steel_hooks([1, 2], 2)
        self.assertEqual(self.model.undo_stack.count(), 1)
        for i in (1, 2):
            row = self.model.rows[i]
            entry = row['steel_catalog'][row['cells'][7]]
            self.assertEqual(Decimal(row['cells'][5]), 2 * Decimal(entry['hook']))
        after = deepcopy(self.model.rows)
        self.model.undo_stack.undo()
        self.assertEqual(self.model.rows, before)
        self.model.undo_stack.redo()
        self.assertEqual(self.model.rows, after)

    def test_reapplying_replaces_and_custom_length_is_shared(self):
        self.model.apply_steel_hooks([1, 2], 2, '0,4')
        self.model.apply_steel_hooks([1, 2], 1, '.3')
        for row in self.model.rows[1:]:
            self.assertEqual(Decimal(row['cells'][5]), Decimal('.3'))
        self.assertEqual(self.model.undo_stack.count(), 2)
        self.model.undo_stack.undo()
        self.assertEqual(Decimal(self.model.rows[1]['cells'][5]), Decimal('.8'))

    def test_length_and_diameter_edits_recalculate_and_undo(self):
        self.model.apply_steel_hooks([1], 2)
        self.assertTrue(self.model.setData(self.model.index(1, 4), '9'))
        self.assertEqual(sc.dimensions(self.model.rows[1])[2], 1)
        self.assertTrue(self.model.setData(self.model.index(1, 9), '1"'))
        self.assertEqual(Decimal(self.model.rows[1]['cells'][5]), Decimal('.90'))
        self.model.undo_stack.undo()
        self.assertEqual(self.model.rows[1]['cells'][7], '1/2"')
        self.assertFalse(self.model.editable(1, 5))
        self.assertFalse(self.model.editable(1, 6))

    def test_description_suffix_diameter_edit_uses_own_catalog(self):
        self.model.apply_steel_hooks([1], 1)
        self.model.setData(self.model.index(1, 1), 'Barra editada 3 Ø1"')
        self.assertEqual(Decimal(self.model.rows[1]['cells'][5]), Decimal('.45'))
        self.model.setData(self.model.index(1, 4), 'pendiente')
        self.assertIn(1, self.model.errors)
        self.assertEqual(self.model.rows[1]['cells'][5:7], ['', ''])
        self.model.setData(self.model.index(1, 4), '18')
        self.assertEqual(sc.dimensions(self.model.rows[1])[2], 2)

    def test_invalid_batch_is_atomic(self):
        before = deepcopy(self.model.rows)
        for selected, count, override in [([0, 1], 1, None), ([1], 0, None),
                                          ([1], 2, 'NaN'), ([], 1, None)]:
            with self.assertRaises(ValueError):
                self.model.apply_steel_hooks(selected, count, override)
            self.assertEqual(self.model.rows, before)
        self.assertEqual(self.model.undo_stack.count(), 0)

    def test_unknown_legacy_diameter_rejects_update_atomically(self):
        self.model.replace(sample(False))
        self.model.rows[1]['cells'][7] = '11mm'
        before = deepcopy(self.model.rows)
        with self.assertRaises(ValueError):
            self.model.update_steel_catalog(sc.initial_catalog())
        self.assertEqual(self.model.rows, before)
        self.assertEqual(self.model.undo_stack.count(), 0)

    def test_pasting_cells_recalculates_managed_dimensions_atomically(self):
        before = deepcopy(self.model.rows)
        self.model.paste_mapped_cells([(1, 4, '18'), (2, 4, '27')], (1, 4))
        self.assertEqual(sc.dimensions(self.model.rows[1])[2], 1)
        self.assertEqual(sc.dimensions(self.model.rows[2])[2], 2)
        self.assertEqual(self.model.undo_stack.count(), 1)
        self.model.undo_stack.undo()
        self.assertEqual(self.model.rows, before)

    def test_direct_quantity_stays_direct_during_update(self):
        self.model.set_direct(1, '25')
        before = self.model.values[(1, 12)]
        with self.assertRaises(ValueError):
            self.model.apply_steel_hooks([1, 2], 2)
        catalog = sc.initial_catalog()
        catalog['1/2"']['weight'] = '99'
        self.model.update_steel_catalog(catalog)
        self.assertEqual(self.model.values[(1, 12)], before)

    def test_explicit_update_is_undoable_and_preserves_custom_hook(self):
        self.model.apply_steel_hooks([1], 2, '.31')
        before = deepcopy(self.model.rows)
        catalog = sc.initial_catalog()
        catalog['1/2"'].update(weight='4', hook='.99', lap='2')
        self.model.update_steel_catalog(catalog)
        self.assertEqual(Decimal(self.model.rows[1]['cells'][5]), Decimal('.62'))
        self.assertEqual(self.model.values[(1, 11)], 4)
        self.assertEqual(Decimal(self.model.rows[1]['cells'][6]), Decimal(2))
        self.model.undo_stack.undo()
        self.assertEqual(self.model.rows, before)

    def test_legacy_unchanged_until_explicit_application(self):
        self.model.replace(sample(False))
        before = deepcopy(self.model.rows)
        values = dict(self.model.values)
        self.model.steel_defaults['1/2"']['weight'] = '99'
        self.model.recalculate()
        self.assertEqual(self.model.rows, before)
        self.assertEqual(self.model.values, values)
        self.model.apply_steel_hooks([1], 1)
        self.assertNotIn('steel_hooks', self.model.rows[2])
        self.model.undo_stack.undo()
        self.assertEqual(self.model.rows, before)

    def test_update_legacy_retains_total_manual_hook_as_custom(self):
        self.model.replace(sample(False))
        self.model.update_steel_catalog(sc.initial_catalog())
        self.assertEqual(self.model.rows[1]['steel_hooks'], dict(count=1, override='0.4'))
        self.assertEqual(Decimal(self.model.rows[1]['cells'][6]), 0)

    def test_unit_transition_initializes_without_hooks_and_undo_restores(self):
        before = deepcopy(self.model.rows)
        self.model.setData(self.model.index(0, 2), 'm3')
        self.assertTrue(all('steel_catalog' not in row for row in self.model.rows))
        self.model.undo_stack.undo()
        self.assertEqual(self.model.rows, before)
        self.model.setData(self.model.index(0, 2), 'm')
        self.model.setData(self.model.index(0, 2), 'kg')
        self.assertEqual(self.model.rows[1]['steel_hooks']['count'], 0)
        self.assertEqual(self.model.rows[1]['cells'][7], '')

    def test_copy_paste_preserves_values_even_in_another_catalog(self):
        self.model.apply_steel_hooks([1, 2], 2, '.4')
        mime = encode_rows(self.model, [1, 2])
        self.assertEqual(json.loads(bytes(mime.data(ROW_MIME)))['version'], 5)
        block = decode_rows(mime.data(ROW_MIME))
        destination = sample()
        destination[0]['steel_catalog']['1/2"']['weight'] = '99'
        result, position = insert_rows(destination, 0, block)
        self.assertEqual(result[position]['steel_catalog'], self.model.rows[1]['steel_catalog'])
        self.assertEqual(calculate(result, engine)[0][(position, 12)], self.model.values[(1, 12)])


class SteelStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = CatalogStore(self.root / 'settings' / 'steel.db')
        self.path = self.root / 'obra.db'

    def tearDown(self):
        self.temp.cleanup()

    def test_global_read_is_lazy_save_persists_and_detects_conflict(self):
        catalog, revision = self.store.read()
        self.assertIsNone(revision)
        self.assertFalse(self.store.path.exists())
        revision = self.store.save(catalog, revision)
        self.assertEqual(self.store.read(), (catalog, revision))
        self.assertEqual(self.store.save(catalog, revision), revision)
        with self.assertRaises(ConflictError):
            self.store.save(catalog, None)
        changed = deepcopy(catalog)
        changed['6mm']['weight'] = '.5'
        self.store.save(changed, revision)
        with self.assertRaises(ConflictError):
            self.store.save(catalog, revision)
        self.assertEqual(self.store.read()[0], changed)

    def test_global_update_never_changes_saved_work(self):
        rows = sample()
        before = calculate(rows, engine)
        write_database(self.path, 'Obra', rows)
        catalog, revision = self.store.read()
        catalog['1/2"'].update(weight='100', lap='5', hook='1')
        self.store.save(catalog, revision)
        loaded = read_database(self.path)[1]
        self.assertEqual(calculate(loaded, engine), before)
        self.assertEqual(loaded[1]['steel_catalog'], rows[1]['steel_catalog'])

    def test_relational_roundtrip_noop_and_metadata_revision(self):
        rows = sample()
        revision = write_database(self.path, 'Acero', rows)
        title, loaded, _ = read_database(self.path)
        self.assertEqual(title, 'Acero')
        self.assertEqual(calculate(loaded, engine), calculate(rows, engine))
        self.assertEqual(write_database(self.path, title, loaded, revision), revision)
        with closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM steel_catalog').fetchone()[0], 27)
            self.assertEqual(connection.execute('PRAGMA foreign_key_check').fetchall(), [])
            self.assertEqual(connection.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        loaded[1]['steel_hooks']['count'] = 2
        self.assertEqual(write_database(self.path, title, loaded, revision), revision + 1)
        with self.assertRaises(ConflictError):
            write_database(self.path, title, loaded, revision)

    def test_json_roundtrip_and_old_version_rejects_metadata(self):
        path = self.root / 'export.json'
        rows = sample()
        write_project(path, 'Acero', rows)
        data = json.loads(path.read_text(encoding='utf8'))
        self.assertEqual(data['version'], 6)
        self.assertEqual(calculate(read_project(path)[1], engine), calculate(rows, engine))
        data['version'] = 5
        with self.assertRaises(ValueError):
            validate_project(data)

    def test_legacy_schema_3_read_does_not_write_and_save_migrates(self):
        rows = sample(False)
        revision = write_database(self.path, 'Antiguo', rows)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute('DROP TABLE steel_hooks')
            connection.execute('DROP TABLE steel_catalog')
            connection.execute('PRAGMA user_version=3')
        before = self.path.read_bytes()
        title, loaded, oldrevision = read_database(self.path)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(calculate(loaded, engine), calculate(rows, engine))
        self.assertEqual(oldrevision, revision)
        write_database(self.path, title, loaded, revision)
        with closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(connection.execute('PRAGMA user_version').fetchone()[0], SCHEMA_VERSION)

    def test_failed_metadata_write_rolls_back_entire_save(self):
        write_database(self.path, 'Antes', sample())
        before = read_database(self.path)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("""CREATE TRIGGER reject_hooks BEFORE INSERT ON steel_hooks
                WHEN NEW.count=2 BEGIN SELECT RAISE(ABORT, 'failure'); END""")
        rows = deepcopy(before[1])
        rows[1]['steel_hooks']['count'] = 2
        with self.assertRaises(sqlite3.IntegrityError):
            write_database(self.path, 'Después', rows, before[2])
        self.assertEqual(read_database(self.path), before)

    def test_invalid_global_file_is_not_overwritten(self):
        self.store.path.parent.mkdir()
        self.store.path.write_bytes(b'not a database')
        with self.assertRaises(sqlite3.DatabaseError):
            self.store.read()
        with self.assertRaises(ConflictError):
            self.store.save(sc.initial_catalog(), None)
        self.assertEqual(self.store.path.read_bytes(), b'not a database')

    def test_full_10000_row_steel_export_reopens_and_clipboard_decodes(self):
        item, template, _ = sample()
        rows = [item] + [deepcopy(template) for _ in range(9999)]
        path = self.root / 'large.json'
        write_project(path, 'Acero completo', rows)
        self.assertLess(path.stat().st_size, 10_000_000)
        self.assertEqual(len(read_project(path)[1]), 10000)
        model = SheetModel(engine, rows)
        mime = encode_rows(model, [0])
        self.assertEqual(len(decode_rows(mime.data(ROW_MIME))), 10000)
        model.deleteLater()


class SteelUiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = CatalogStore(Path(self.temp.name) / 'steel.db')
        self.window = PlantillaWindow(engine, catalog_store=self.store)
        self.window._load('Acero', sample())
        self.window.show()
        APP.processEvents()

    def tearDown(self):
        self.window.model.undo_stack.setClean()
        self.window._dirty = False
        self.window.close()
        self.window.deleteLater()
        APP.processEvents()
        self.temp.cleanup()

    def test_catalog_dialog_edits_validates_and_does_not_write_on_cancel(self):
        dialog = CatalogDialog(sc.initial_catalog(), self.window)
        self.assertFalse(dialog.table.item(0, 0).flags() & Qt.ItemIsEditable)
        dialog.table.item(0, 1).setText('-2')
        self.assertFalse(dialog.buttons.button(QDialogButtonBox.Save).isEnabled())
        dialog.table.item(0, 1).setText('0,222')
        self.assertTrue(dialog.buttons.button(QDialogButtonBox.Save).isEnabled())
        self.assertEqual(dialog.configuration()['6mm']['weight'], '0,222')
        dialog.reject()
        self.assertFalse(self.store.path.exists())

    def test_hooks_dialog_count_and_custom_length(self):
        rows = self.window.model.rows[1:]
        dialog = HooksDialog(rows, [r['steel_catalog'] for r in rows], self.window)
        self.assertEqual(dialog.configuration(), (1, None))
        dialog.count.setCurrentIndex(1)
        dialog.custom.setChecked(True)
        self.assertFalse(dialog.buttons.button(QDialogButtonBox.Ok).isEnabled())
        dialog.length.setText('0,35')
        self.assertEqual(dialog.configuration(), (2, '0,35'))
        self.assertTrue(dialog.buttons.button(QDialogButtonBox.Ok).isEnabled())
        dialog.reject()

    def test_global_edit_leaves_current_work_and_undo_stack_untouched(self):
        before = deepcopy(self.window.model.rows)
        changed = sc.initial_catalog()
        changed['1/2"']['weight'] = '9'
        with patch.object(CatalogDialog, 'exec', return_value=QDialog.Accepted), \
             patch.object(CatalogDialog, 'configuration', return_value=changed):
            self.window.edit_steel_catalog()
        self.assertEqual(self.window.model.rows, before)
        self.assertEqual(self.window.model.undo_stack.count(), 0)
        self.assertEqual(self.store.read()[0], changed)

    def test_update_requires_confirmation_and_undo_restores(self):
        before = deepcopy(self.window.model.rows)
        changed = sc.initial_catalog()
        changed['1/2"']['weight'] = '9'
        self.store.save(changed, None)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.No):
            self.window.update_project_steel()
        self.assertEqual(self.window.model.rows, before)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            self.window.update_project_steel()
        self.assertEqual(self.window.model.values[(1, 11)], 9)
        self.window.model.undo_stack.undo()
        self.assertEqual(self.window.model.rows, before)

    def test_selected_rows_only_and_real_ctrl_z(self):
        model, table = self.window.model, self.window.table
        before = deepcopy(model.rows)
        self.window._select(1)
        table.setFocus()
        APP.processEvents()
        table.selectionModel().select(model.index(2, 1), QItemSelectionModel.Select)
        with patch.object(HooksDialog, 'exec', return_value=QDialog.Accepted), \
             patch.object(HooksDialog, 'configuration', return_value=(2, '.3')):
            self.window.edit_steel_hooks()
        self.assertEqual(model.undo_stack.count(), 1)
        self.assertTrue(all(r['steel_hooks']['count'] == 2 for r in model.rows[1:]))
        table.setFocus()
        QTest.keyClick(table, Qt.Key_Z, Qt.ControlModifier)
        APP.processEvents()
        self.assertEqual(model.rows, before)

    def test_new_details_start_with_no_hooks_using_saved_item_catalog(self):
        self.window.model.steel_defaults['1/2"']['weight'] = '99'
        self.window._select(0)
        self.window.add_row('detail')
        self.window._commit_editors()
        row = self.window.model.rows[1]
        self.assertEqual(row['steel_hooks']['count'], 0)
        self.assertNotEqual(row['steel_catalog']['1/2"']['weight'], '99')
        self.assertFalse(self.store.path.exists())


if __name__ == '__main__':
    unittest.main()
