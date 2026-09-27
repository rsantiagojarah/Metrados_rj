"""Live links, signed takeoffs, persistence and the actual slash keyboard path."""
from copy import deepcopy
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QCoreApplication, QEvent, QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QLineEdit
import metrado._enlace as engine
from metrado.clipboard import ROW_MIME, decode_rows, encode_rows, insert_rows, parse_tsv
from metrado.database import SCHEMA_VERSION, read_database, write_database
from metrado.grid import SheetModel, labels_for_mode
from metrado.hierarchy import materialize
from metrado.identity import ensure_ids
from metrado.reference_dialog import ConversionDialog, ReferencePicker
from metrado.references import check_cycles, make_reference, validate_row
from metrado.sheet import calculate, new_row, read_project, steel_detail, write_project
from metrado.steel_store import CatalogStore
from metrado.window import PlantillaWindow

APP = QApplication.instance() or QApplication([])


def fixture():
    rows = []
    for name, unit, quantity in [('Excavación', 'm3', '100'), ('Eliminación', 'm3', ''),
                                  ('Superficie', 'm2', '20'), ('Peso', 'kg', '')]:
        rows += [new_row('item', str(len(rows) // 2 + 1), name, unit, 0),
                 new_row('detail', description='Detalle', unit=unit, level=1)]
        rows[-1]['direct'] = quantity
    ensure_ids(rows)
    return rows


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.model = SheetModel(engine, fixture())

    def tearDown(self):
        self.model.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)

    def link(self, target=3, source=0, name='', factor=''):
        self.model.set_reference(target, self.model.rows[source]['id'], name, factor)

    def text(self, row, column):
        return self.model.data(self.model.index(row, column))

    def test_same_unit_no_factor_no_suffix(self):
        self.link()
        self.assertEqual(self.model.values[(2, 13)], 100)
        self.assertEqual(self.text(3, 4), '100.00')
        self.assertEqual(self.text(3, 5), '')
        self.assertEqual(self.model.rows[3]['reference']['factor'], '')
        self.assertEqual(self.text(3, 1).strip(), '↗ 1 · Excavación')
        self.assertEqual(labels_for_mode(self.model.selection_mode(3))[5], '')

    def test_conversion_visible_and_named(self):
        self.link(source=4, name='Espesor', factor='0,15')
        self.assertEqual(self.model.values[(2, 13)], 3)
        self.assertEqual(self.text(3, 4), '20.00')
        self.assertEqual(self.text(3, 5), '0,15')
        self.assertIn('Espesor: 0,15', self.text(3, 1))
        self.assertEqual(labels_for_mode(self.model.selection_mode(3))[5], 'Factor')

    def test_negatives_and_zero_source(self):
        self.link()
        self.model.setData(self.model.index(3, 7), '-2')
        self.assertEqual(self.model.values[(2, 13)], -200)
        self.model.setData(self.model.index(3, 3), '-3')
        self.assertEqual(self.model.values[(2, 13)], 600)
        self.model.setData(self.model.index(1, 3), '-1')
        self.assertEqual(self.model.values[(2, 13)], -600)
        rows = deepcopy(self.model.rows)
        del rows[1]
        self.model.replace(rows)
        self.assertEqual(self.model.values[(1, 13)], 0)

    def test_chains_work_even_when_sources_come_later(self):
        self.link()
        self.link(7, 2, 'Densidad', '2')
        self.model.set_direct(1, '150')
        self.assertEqual(self.model.values[(6, 13)], 300)
        rows = deepcopy(self.model.rows)
        self.model.replace(rows[6:8] + rows[2:6] + rows[:2])
        self.assertEqual(self.model.values[(0, 13)], 300)

    def test_rename_is_live_and_undo_restores(self):
        self.link()
        self.model.setData(self.model.index(0, 1), 'Corte de terreno')
        self.assertIn('Corte de terreno', self.text(3, 1))
        self.model.undo_stack.undo()
        self.assertIn('Excavación', self.text(3, 1))
        self.model.setData(self.model.index(0, 0), '99.01')
        self.assertIn('99.01', self.text(3, 1))

    def test_reference_undo_and_redo_is_one_operation(self):
        before = deepcopy(self.model.rows)
        self.link()
        self.assertEqual(self.model.undo_stack.count(), 1)
        self.model.undo_stack.undo()
        self.assertEqual(self.model.rows, before)
        self.model.undo_stack.redo()
        self.assertEqual(self.model.values[(2, 13)], 100)

    def test_source_deletion_is_pending_and_undo_recovers(self):
        self.link()
        self.model.replace(deepcopy(self.model.rows[2:]), 'eliminar')
        self.assertIn(1, self.model.errors)
        self.assertEqual(self.text(0, 13), 'Pendiente')
        self.assertIn('no disponible', self.text(1, 1))
        self.model.undo_stack.undo()
        self.assertEqual(self.model.values[(2, 13)], 100)

    def test_pending_source_propagates_through_chain(self):
        self.link()
        self.link(7, 2, 'Densidad', '2')
        self.model.set_direct(1, '')
        self.assertNotIn((2, 13), self.model.values)
        self.assertNotIn((6, 13), self.model.values)

    def test_cycles_rejected_atomically(self):
        self.link()
        before = deepcopy(self.model.rows)
        with self.assertRaisesRegex(ValueError, 'circular'):
            self.link(1, 2)
        self.assertEqual(self.model.rows, before)
        with self.assertRaisesRegex(ValueError, 'circular'):
            self.link(3, 2)

    def test_corrupt_cycle_calculation_never_recurses(self):
        self.link()
        rows = deepcopy(self.model.rows)
        rows[1]['direct'] = ''
        rows[1]['reference'] = make_reference(rows[2], 'm3')
        values, errors = calculate(rows, engine)
        self.assertIn(0, errors)
        self.assertIn(2, errors)
        self.assertNotIn((0, 13), values)

    def test_source_unit_change_requires_new_conversion(self):
        self.link()
        self.model.setData(self.model.index(0, 2), 'm2')
        self.model.set_direct(1, '100')
        self.assertIn('Cambió la unidad', self.model.errors[3])
        self.assertNotIn((2, 13), self.model.values)
        self.link(name='Espesor', factor='0.2')
        self.assertEqual(self.model.values[(2, 13)], 20)

    def test_target_unit_change_to_equal_hides_old_factor(self):
        self.link(source=4, name='Espesor', factor='0.2')
        self.model.setData(self.model.index(2, 2), 'm2')
        self.assertEqual(self.model.values[(2, 13)], 20)
        self.assertEqual(self.text(3, 5), '')
        self.assertNotIn('Espesor', self.text(3, 1))
        self.model.undo_stack.undo()
        self.assertEqual(self.model.values[(2, 13)], 4)

    def test_kg_reference_has_no_bar_suffix_and_sign_edit_works(self):
        self.link(7, 0, 'Densidad', '2.5')
        self.assertEqual(self.text(7, 11), '250.00')
        self.assertEqual(self.text(7, 9), '')
        self.assertNotIn('Ø', self.text(7, 1))
        self.model.setData(self.model.index(7, 7), '-1')
        self.assertEqual(self.model.values[(6, 13)], -250)
        self.model.update_steel_catalog(self.model.steel_catalog_for(6))
        self.assertNotIn('steel_hooks', self.model.rows[7])
        self.assertEqual(self.model.values[(6, 13)], -250)

    def test_factor_validation_rejects_bad_input(self):
        for name, factor in [('', '2'), ('X', ''), ('X', '0'), ('X', '-1'), ('X', 'NaN'), ('X', 'inf')]:
            with self.subTest(name=name, factor=factor), self.assertRaises(ValueError):
                self.link(source=4, name=name, factor=factor)

    def test_negative_geometry_and_steel(self):
        self.model.set_direct(1, '')
        for c, value in [(4, '2'), (5, '3'), (6, '4'), (7, '-1')]:
            self.model.setData(self.model.index(1, c), value)
        self.assertEqual(self.model.values[(0, 13)], -24)
        rows = [new_row('item', unit='kg'), steel_detail('Barras', -2, 2, 0, 0, '1/2"', 3)]
        values, errors = calculate(rows, engine)
        self.assertFalse(errors)
        self.assertLess(values[(0, 13)], 0)

    def test_fe_uses_signed_link_total_and_updates(self):
        self.link()
        self.model.set_swelling([3], dict(factor='1.2', note=''))
        self.assertEqual(self.model.values[(2, 13)], 120)
        self.model.setData(self.model.index(3, 7), '-1')
        self.assertEqual(self.model.values[(2, 13)], -120)
        self.model.set_direct(1, '50')
        self.assertEqual(self.model.values[(2, 13)], -60)
        self.assertEqual(parse_tsv(encode_rows(self.model, [3]).text())[-1][10], '-60.00')

    def test_references_use_adjusted_source_total(self):
        self.link()
        self.model.set_swelling([1], dict(factor='1.2', note=''))
        self.assertEqual(self.model.values[(2, 13)], 120)

    def test_sqlite_json_roundtrip_and_unchanged_save(self):
        self.link(source=4, name='Espesor', factor='0,15')
        with tempfile.TemporaryDirectory() as folder:
            db, json_path = Path(folder) / 'obra.db', Path(folder) / 'obra.json'
            revision = write_database(db, 'Obra', self.model.rows)
            self.assertEqual(write_database(db, 'Obra', self.model.rows, revision), revision)
            _, rows, _ = read_database(db)
            self.assertEqual(rows[3]['reference'], self.model.rows[3]['reference'])
            self.assertEqual(calculate(rows, engine)[0][(2, 13)], 3)
            write_project(json_path, 'Obra', rows)
            self.assertEqual(json.loads(json_path.read_text('utf-8'))['version'], 7)
            _, restored = read_project(json_path)
            self.assertEqual(calculate(restored, engine)[0][(2, 13)], 3)
            self.assertEqual(rows, restored)

    def test_sqlite_v4_migration_keeps_data(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'old.db'
            revision = write_database(path, 'Anterior', self.model.rows)
            with closing(sqlite3.connect(path)) as con, con:
                con.execute('DROP TABLE detail_references')
                con.execute('PRAGMA user_version=4')
            self.assertEqual(read_database(path)[0], 'Anterior')
            self.link()
            write_database(path, 'Anterior', self.model.rows, revision)
            _, rows, _ = read_database(path)
            self.assertEqual(calculate(rows, engine)[0][(2, 13)], 100)

    def test_missing_source_roundtrip_retains_reference(self):
        self.link()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'missing.db'
            write_database(path, 'Obra', self.model.rows[2:])
            _, rows, _ = read_database(path)
            self.assertIn('reference', rows[1])
            self.assertIn(0, calculate(rows, engine)[1])

    def test_copy_item_pair_remaps_internal_link(self):
        self.link()
        block = decode_rows(encode_rows(self.model, [0, 2]).data(ROW_MIME))
        rows, pos = insert_rows(self.model.rows, 6, block)
        self.assertNotEqual(rows[pos]['id'], self.model.rows[0]['id'])
        self.assertEqual(rows[pos + 3]['reference']['source'], rows[pos]['id'])
        self.assertEqual(calculate(rows, engine)[0][(pos + 2, 13)], 100)

    def test_copy_detail_preserves_external_source_and_rejects_cycle(self):
        self.link()
        block = decode_rows(encode_rows(self.model, [3]).data(ROW_MIME))
        with self.assertRaisesRegex(ValueError, 'circular'):
            insert_rows(self.model.rows, 0, block)
        rows, pos = insert_rows(self.model.rows, 3, block)
        self.assertEqual(rows[pos]['reference']['source'], self.model.rows[0]['id'])
        self.assertEqual(calculate(rows, engine)[0][(2, 13)], 200)

    def test_long_chain_uses_iterative_order(self):
        rows = []
        for i in range(1500):
            item = new_row('item', description=str(i), unit='m3', level=0)
            item['id'] = f'item-{i}'
            detail = new_row('detail', unit='m3', level=1)
            if i == 0:
                detail['direct'] = '2'
            else:
                detail['reference'] = make_reference(rows[-2], 'm3')
            rows.extend([item, detail])
        values, errors = calculate(rows, engine)
        self.assertFalse(errors)
        self.assertEqual(values[(2998, 13)], 2)


class ReferenceUiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.window = PlantillaWindow(engine, CatalogStore(Path(self.temp.name) / 'steel.db'))
        self.window._load('Referencias', fixture())
        self.window.show()
        self.window.activateWindow()
        self.window._select(3, 1)
        self.window.table.setFocus()
        APP.processEvents()

    def tearDown(self):
        with patch.object(self.window, '_can_discard', return_value=True):
            self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        self.temp.cleanup()

    def choose(self, text):
        def callback():
            picker = QApplication.activeModalWidget()
            if not isinstance(picker, ReferencePicker):
                if picker:
                    picker.reject()
                return
            QTest.keyClicks(picker.search, text)
            QTest.keyClick(picker.search, Qt.Key_Return)
        QTimer.singleShot(50, callback)

    def test_slash_type_filter_enter_same_unit_no_dialog(self):
        self.choose('excavacion')
        with patch('metrado.window.ConversionDialog') as conversion:
            QTest.keyClicks(self.window.table, '/')
            conversion.assert_not_called()
        self.assertEqual(self.window.model.values[(2, 13)], 100)
        self.assertEqual(self.window.model.undo_stack.count(), 1)

    def test_slash_from_existing_editor(self):
        QTest.keyClick(self.window.table, Qt.Key_F2)
        editor = QApplication.focusWidget()
        self.assertIsInstance(editor, QLineEdit)
        editor.selectAll()
        self.choose('excavacion')
        QTest.keyClicks(editor, '/')
        self.assertEqual(self.window.model.values[(2, 13)], 100)

    def test_escape_does_not_mutate(self):
        before = deepcopy(self.window.model.rows)
        QTimer.singleShot(50, lambda: QApplication.activeModalWidget().reject())
        QTest.keyClicks(self.window.table, '/')
        self.assertEqual(self.window.model.rows, before)
        self.assertEqual(self.window.model.undo_stack.count(), 0)

    def test_mismatch_conversion_cancel_does_not_mutate(self):
        before = deepcopy(self.window.model.rows)
        self.choose('superficie')
        with patch.object(ConversionDialog, 'exec', return_value=QDialog.Rejected):
            QTest.keyClicks(self.window.table, '/')
        self.assertEqual(self.window.model.rows, before)

    def test_conversion_form_validates_and_applies(self):
        self.choose('superficie')
        original_exec = ConversionDialog.exec
        def enter(dialog):
            def fill():
                dialog.accept()
                self.assertTrue(dialog.error.text())
                dialog.name.setText('Espesor')
                dialog.factor.setText('0,15')
                dialog.accept()
            QTimer.singleShot(30, fill)
            return original_exec(dialog)
        with patch.object(ConversionDialog, 'exec', enter):
            QTest.keyClicks(self.window.table, '/')
        self.assertEqual(self.window.model.values[(2, 13)], 3)

    def test_empty_item_slash_creates_one_undoable_detail(self):
        rows = fixture()
        del rows[3]
        self.window._load('Vacía', rows)
        self.window._select(2, 1)
        self.window.table.setFocus()
        self.choose('excavacion')
        QTest.keyClicks(self.window.table, '/')
        self.assertEqual(self.window.model.values[(2, 13)], 100)
        self.window.model.undo_stack.undo()
        self.assertEqual(len(self.window.model.rows), len(rows))

    def test_widths_stay_fixed_between_geometry_and_links(self):
        self.window.model.set_reference(3, self.window.model.rows[4]['id'], 'Espesor', '0.2')
        before = [self.window.table.columnWidth(c) for c in range(14)]
        self.window._select(1, 1)
        self.window._select(3, 1)
        self.assertEqual(before, [self.window.table.columnWidth(c) for c in range(14)])

    def test_move_reference_into_source_is_rejected_without_changes(self):
        self.window.model.set_reference(3, self.window.model.rows[0]['id'])
        before = deepcopy(self.window.model.rows)
        self.window._select(3, 1)
        self.window.move_to_parent(0)
        self.assertEqual(self.window.model.rows, before)
        self.assertIn('circular', self.window.statusBar().currentMessage())

    def test_picker_arrows_enter_and_escape(self):
        picker = ReferencePicker([('Primera', 'm3', 'a', True), ('Segunda', 'm3', 'b', True)])
        picker.show()
        QTest.keyClick(picker.search, Qt.Key_Down)
        QTest.keyClick(picker.search, Qt.Key_Return)
        self.assertEqual(picker.chosen, 'b')
        picker.deleteLater()

    def test_two_reference_rows_can_add_and_subtract(self):
        model = self.window.model
        model.set_reference(3, model.rows[0]['id'])
        block = decode_rows(encode_rows(model, [3]).data(ROW_MIME))
        rows, position = insert_rows(model.rows, 3, block)
        model.replace(rows)
        model.setData(model.index(position, 7), '-1')
        self.assertEqual(model.values[(2, 13)], 0)
