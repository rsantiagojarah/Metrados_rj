"""Consecutive FE blocks: quantities, history, interchange, migration and UI."""
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
from PySide6.QtCore import QEvent, QItemSelection, QItemSelectionModel, QPoint, Qt
from PySide6.QtGui import QHelpEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QLineEdit, QMessageBox, QTableView

import metrado._enlace as engine
from metrado.clipboard import ROW_MIME, decode_rows, encode_rows, insert_rows, parse_tsv
from metrado.database import SCHEMA_VERSION, ConflictError, read_database, write_database
from metrado.grid import FOOTER_HEIGHT, ROW_HEIGHT, SheetModel
from metrado.hierarchy import move_to
from metrado.sheet import calculate, example_rows, new_row, read_project, validate_project, write_project
from metrado.swelling import factor_number, volume_blocks
from metrado.swelling_dialog import SwellingDialog
from metrado.window import PlantillaWindow

APP = QApplication.instance() or QApplication([])


def config(factor='1,20', note='Criterio del proyecto'):
    return dict(factor=factor, note=note)


def volume_rows():
    rows = [new_row('chapter', '01', 'MOVIMIENTO DE TIERRAS', level=0),
            new_row('item', '01.01', 'ELIMINACIÓN DE MATERIAL', 'm3', level=1),
            new_row('detail_group', description='ZANJAS', unit='m3', level=2)]
    rows += [new_row('detail', description=f'Tramo {i}', unit='m3', level=3) for i in range(1, 5)]
    rows += [new_row('item', '01.02', 'OTRO VOLUMEN', 'm3', level=1),
             new_row('detail', description='Volumen libre', unit='m3', level=2),
             new_row('item', '01.03', 'ACERO', 'kg', level=1)]
    for row in rows:
        if row['kind'] == 'detail':
            row['cells'][4:7] = ['2', '3', '4']
    return rows


class BlockCalculationTests(unittest.TestCase):
    def setUp(self):
        self.model = SheetModel(engine, volume_rows())

    def test_two_details_match_screenshot_and_free_details_sum_once(self):
        self.model.set_swelling([3, 4], config())
        self.assertAlmostEqual(self.model.values[(4, 14)], 57.6)
        self.assertAlmostEqual(self.model.values[(1, 13)], 105.6)
        self.assertEqual(self.model.values[(3, 10)], 24)
        self.assertEqual(self.model.values[(4, 10)], 24)
        self.assertEqual(self.model.values[(7, 13)], 24)
        self.assertEqual(self.model.swelling_footers, {4: 3})
        self.assertEqual(self.model.swelling_summary(3)[8:11], ['FE', '1,20', '57.60'])
        self.assertEqual(sum(bool(c) for c in self.model.swelling_summary(3)), 3)
        self.assertEqual(len(self.model.rows), 10)

    def test_several_blocks_in_one_item(self):
        self.model.set_swelling([3, 4], config())
        self.model.set_swelling([5], config('1.50'))
        self.assertEqual(self.model.swelling_footers, {4: 3, 5: 5})
        self.assertAlmostEqual(self.model.values[(1, 13)], 117.6)
        for _ in range(3):
            self.model.recalculate(4)
        self.assertAlmostEqual(self.model.values[(1, 13)], 117.6)

    def test_adjacent_independent_blocks_with_same_factor_stay_separate(self):
        self.model.set_swelling([3, 4], config())
        self.model.set_swelling([5, 6], config())
        self.assertEqual(self.model.swelling_footers, {4: 3, 6: 5})
        self.assertAlmostEqual(self.model.values[(1, 13)], 115.2)

    def test_apply_edit_remove_undo_redo(self):
        self.model.set_swelling([3, 4], config())
        before = deepcopy(self.model.rows)
        self.model.set_swelling([3, 4], config('1.5'))
        self.assertEqual(self.model.values[(1, 13)], 120)
        self.model.undo_stack.undo()
        self.assertEqual(self.model.rows, before)
        self.model.undo_stack.redo()
        self.model.set_swelling([3, 4], None)
        self.assertEqual(self.model.values[(1, 13)], 96)
        self.assertEqual(self.model.swelling_footers, {})
        self.model.undo_stack.undo()
        self.assertEqual(self.model.values[(1, 13)], 120)

    def test_unchanged_configuration_is_noop(self):
        self.model.set_swelling([3, 4], config())
        self.model.set_swelling([3, 4], config())
        self.assertEqual(self.model.undo_stack.count(), 1)

    def test_replacing_part_of_a_block_splits_without_overlap(self):
        self.model.set_swelling(range(3, 7), config())
        self.model.set_swelling([4, 5], config('1.5'))
        self.assertEqual(self.model.swelling_footers, {3: 3, 5: 4, 6: 6})
        self.assertAlmostEqual(self.model.values[(1, 13)], 129.6)
        self.model.set_swelling([4], None)
        self.assertAlmostEqual(self.model.values[(1, 13)], 117.6)

    def test_nonconsecutive_titles_units_and_cross_item_selection_rejected(self):
        before = deepcopy(self.model.rows)
        for selected in ([], [3, 5], [1], [2, 3], [6, 7, 8], [9], [-1], [999]):
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                self.model.set_swelling(selected, config())
        self.assertEqual(self.model.rows, before)
        self.assertEqual(self.model.undo_stack.count(), 0)

    def test_bad_factors_rejected_atomically(self):
        before = deepcopy(self.model.rows)
        for value in ('0', '0.9', '-1', 'nan', 'inf', '1e999', '', 'text', 1.2):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.model.set_swelling([3, 4], config(value))
        for value in (config(note=1), config(note='x' * 1201), {}):
            with self.assertRaises(ValueError):
                self.model.set_swelling([3], value)
        self.assertEqual(self.model.rows, before)
        self.assertEqual(factor_number('1,125'), 1.125)

    def test_one_is_valid_and_extra_precision_not_rounded_for_calculation(self):
        self.model.set_swelling([3], config('1'))
        self.assertEqual(self.model.values[(1, 13)], 96)
        self.model.set_swelling([3], config('1.125'))
        self.assertEqual(self.model.swelling_summary(3)[9], '1,125')
        self.assertEqual(self.model.values[(1, 13)], 99)

    def test_edit_and_pending_only_affect_their_block(self):
        self.model.set_swelling([3, 4], config())
        self.model.set_swelling([5, 6], config('1.5'))
        self.model.setData(self.model.index(4, 4), '')
        self.assertEqual(self.model.swelling_summary(3)[10], 'Pendiente')
        self.assertEqual(self.model.swelling_summary(5)[10], '72.00')
        self.assertNotIn((1, 13), self.model.values)
        self.model.setData(self.model.index(4, 4), '4')
        self.assertAlmostEqual(self.model.values[(1, 13)], 158.4)

    def test_direct_measurements_keep_similar_and_repetitions(self):
        self.model.set_direct(3, '10')
        self.model.setData(self.model.index(3, 3), '2')
        self.model.set_swelling([3], config('1.5'))
        self.assertEqual(self.model.values[(3, 10)], 20)
        self.assertEqual(self.model.values[(3, 14)], 30)

    def test_overflow_rejected_and_loaded_overflow_pending(self):
        self.model.set_direct(3, '1e308')
        with self.assertRaises((ValueError, OverflowError)):
            self.model.set_swelling([3], config('10'))
        rows = deepcopy(self.model.rows)
        rows[3]['volume_factor'] = dict(config('10'), block='a')
        loaded = SheetModel(engine, rows)
        self.assertNotIn((3, 14), loaded.values)
        self.assertNotIn((1, 13), loaded.values)
        self.assertIn(1, loaded.errors)

    def test_move_detail_to_other_item_preserves_factor_and_splits_source(self):
        self.model.set_swelling([3, 4], config())
        rows, position = move_to(self.model.rows, 4, 7)
        self.model.replace(rows, 'mover')
        owner = self.model.outline.owners[position]
        self.assertAlmostEqual(self.model.values[(owner, 13)], 52.8)
        self.assertAlmostEqual(self.model.values[(1, 13)], 76.8)
        self.assertEqual(len(self.model.swelling_footers), 2)
        self.model.undo_stack.undo()
        self.assertEqual(self.model.swelling_footers, {4: 3})

    def test_inserting_unadjusted_detail_splits_block_without_inheriting(self):
        self.model.set_swelling([3, 4], config())
        rows = deepcopy(self.model.rows)
        row = new_row('detail', unit='m3', level=3)
        row['direct'] = '10'
        rows.insert(4, row)
        self.model.replace(rows, 'insertar')
        self.assertEqual(self.model.swelling_footers, {3: 3, 5: 5})
        self.assertAlmostEqual(self.model.values[(1, 13)], 115.6)
        self.model.undo_stack.undo()
        self.assertEqual(self.model.swelling_footers, {4: 3})

    def test_unit_change_removes_factors_and_undo_restores(self):
        self.model.set_swelling([3, 4], config())
        before = deepcopy(self.model.rows)
        self.model.setData(self.model.index(1, 2), 'm2')
        self.assertFalse(any('volume_factor' in row for row in self.model.rows))
        self.assertEqual(self.model.swelling_footers, {})
        self.model.undo_stack.undo()
        self.assertEqual(self.model.rows, before)

    def test_copy_partial_block_retains_factor_with_new_identity_and_correct_tsv(self):
        self.model.set_swelling([3, 4], config())
        mime = encode_rows(self.model, [4])
        matrix = parse_tsv(mime.text())
        self.assertEqual(matrix[-1][8:11], ['FE', '1,20', '28.80'])
        self.assertEqual(json.loads(bytes(mime.data(ROW_MIME)))['version'], 4)
        block = decode_rows(mime.data(ROW_MIME))
        rows, position = insert_rows(self.model.rows, 4, block)
        self.assertNotEqual(rows[position]['volume_factor']['block'], rows[4]['volume_factor']['block'])
        self.model.replace(rows, 'pegar')
        self.assertEqual(self.model.swelling_footers, {4: 3, 5: 5})
        self.assertAlmostEqual(self.model.values[(1, 13)], 134.4)
        self.model.undo_stack.undo()
        self.assertAlmostEqual(self.model.values[(1, 13)], 105.6)

    def test_copy_complete_block_tsv_and_whole_item(self):
        self.model.set_swelling([3, 4], config())
        self.assertEqual(parse_tsv(encode_rows(self.model, [3, 4]).text())[-1][10], '57.60')
        mime = encode_rows(self.model, [1])
        rows, position = insert_rows(self.model.rows, 7, decode_rows(mime.data(ROW_MIME)))
        model = SheetModel(engine, rows)
        self.assertAlmostEqual(model.values[(position, 13)], 105.6)
        self.assertAlmostEqual(model.values[(1, 13)], 105.6)

    def test_legacy_enabled_disabled_and_empty_preserved(self):
        for enabled, expected in ((True, 120), (False, 96)):
            rows = volume_rows()
            rows[1]['swelling'] = dict(enabled=enabled, percent='25', note='Origen')
            model = SheetModel(engine, rows)
            self.assertNotIn('swelling', model.rows[1])
            self.assertEqual(model.values[(1, 13)], expected)
            self.assertIn('Origen', model.rows[3]['volume_factor']['note'])
            if not enabled:
                self.assertIn('25 %', model.rows[3]['volume_factor']['note'])
        rows = [new_row('item', unit='m3', level=0)]
        rows[0]['swelling'] = dict(enabled=True, percent='25', note='Origen')
        model = SheetModel(engine, rows)
        updated = deepcopy(model.rows)
        updated.append(dict(new_row('detail', unit='m3', level=1), direct='10'))
        model.replace(updated, 'crear')
        self.assertEqual(model.values[(0, 13)], 12.5)
        model.undo_stack.undo()
        self.assertEqual(model.rows[0]['swelling']['percent'], '25')
        model.undo_stack.redo()
        self.assertEqual(model.values[(0, 13)], 12.5)


class BlockStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'obra.metrado.db'
        self.model = SheetModel(engine, volume_rows())

    def tearDown(self):
        self.temp.cleanup()

    def create_old(self, version):
        revision = write_database(self.path, 'Obra', self.model.rows)
        with closing(sqlite3.connect(self.path)) as con, con:
            con.execute('DROP TABLE detail_swelling')
            con.execute('DROP TABLE steel_hooks')
            con.execute('DROP TABLE steel_catalog')
            con.execute('DROP TABLE detail_references')
            if version == 1:
                con.execute('DROP TABLE item_swelling')
            else:
                con.execute('INSERT INTO item_swelling VALUES (?, 1, ?, ?)',
                            (self.model.rows[1]['id'], '25', 'Origen previo'))
            con.execute(f'PRAGMA user_version={version}')
        return revision

    def test_roundtrip_queryable_factors_and_noop_save(self):
        self.model.set_swelling([3, 4], config())
        revision = write_database(self.path, 'Obra', self.model.rows)
        self.assertEqual(read_database(self.path), ('Obra', self.model.rows, revision))
        self.assertEqual(write_database(self.path, 'Obra', self.model.rows, revision), revision)
        with closing(sqlite3.connect(self.path)) as con:
            self.assertEqual(con.execute('PRAGMA user_version').fetchone()[0], SCHEMA_VERSION)
            self.assertEqual(con.execute('SELECT factor, note FROM detail_swelling').fetchall(),
                             [('1,20', 'Criterio del proyecto')] * 2)
            self.assertEqual(con.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_versions_1_and_2_read_only_then_transactional_migration(self):
        for version in (1, 2):
            with self.subTest(version=version):
                self.path = self.path.with_name(f'old-{version}.db')
                revision = self.create_old(version)
                before = self.path.read_bytes()
                title, rows, _ = read_database(self.path)
                self.assertEqual(self.path.read_bytes(), before)
                self.assertEqual(calculate(rows, engine)[0][(1, 13)], 96 if version == 1 else 120)
                if version == 2:
                    self.assertEqual(rows[3]['volume_factor']['note'], 'Origen previo')
                revision2 = write_database(self.path, title, rows, revision)
                self.assertEqual(revision2, revision + 1)
                self.assertEqual(read_database(self.path)[1], rows)

    def test_migration_rollback_and_conflict_do_not_modify_old_schema(self):
        for version in (1, 2):
            self.path = self.path.with_name(f'rollback-{version}.db')
            revision = self.create_old(version)
            before = self.path.read_bytes()
            with self.assertRaises(ConflictError):
                write_database(self.path, 'Obra', self.model.rows, revision + 1)
            self.assertEqual(self.path.read_bytes(), before)
            with closing(sqlite3.connect(self.path)) as con, con:
                con.execute("CREATE TRIGGER fail_save BEFORE UPDATE ON project BEGIN SELECT RAISE(ABORT, 'failure'); END")
            rows = read_database(self.path)[1]
            with self.assertRaises(sqlite3.IntegrityError):
                write_database(self.path, 'Obra', rows, revision)
            with closing(sqlite3.connect(self.path)) as con:
                self.assertEqual(con.execute('PRAGMA user_version').fetchone()[0], version)
                self.assertEqual(con.execute("SELECT name FROM sqlite_master WHERE name='detail_swelling'").fetchall(), [])
                self.assertEqual(con.execute('SELECT revision FROM project').fetchone()[0], revision)

    def test_only_factor_change_does_not_update_nodes(self):
        revision = write_database(self.path, 'Obra', self.model.rows)
        with closing(sqlite3.connect(self.path)) as con, con:
            con.execute('CREATE TABLE audit (id TEXT)')
            con.execute('CREATE TRIGGER updates AFTER UPDATE ON nodes BEGIN INSERT INTO audit VALUES (NEW.id); END')
        self.model.set_swelling([3, 4], config())
        self.assertEqual(write_database(self.path, 'Obra', self.model.rows, revision), revision + 1)
        with closing(sqlite3.connect(self.path)) as con:
            self.assertEqual(con.execute('SELECT * FROM audit').fetchall(), [])

    def test_deleted_rows_cascade_and_undo_can_restore(self):
        self.model.set_swelling([3, 4], config())
        revision = write_database(self.path, 'Obra', self.model.rows)
        revision = write_database(self.path, 'Obra', [], revision)
        with closing(sqlite3.connect(self.path)) as con:
            self.assertEqual(con.execute('SELECT * FROM detail_swelling').fetchall(), [])
        write_database(self.path, 'Obra', self.model.rows, revision)
        self.assertEqual(read_database(self.path)[1], self.model.rows)

    def test_json_5_roundtrip_and_json_4_conversion(self):
        path = self.path.with_suffix('.json')
        self.model.set_swelling([3, 4], config())
        write_project(path, 'Obra', self.model.rows)
        self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['version'], 5)
        self.assertEqual(read_project(path)[1], self.model.rows)
        rows = volume_rows()
        rows[1]['swelling'] = dict(enabled=True, percent='25', note='Origen JSON')
        write_project(path, 'Anterior', rows)
        loaded = read_project(path)[1]
        self.assertEqual(calculate(loaded, engine)[0][(1, 13)], 120)
        self.assertEqual(loaded[3]['volume_factor']['note'], 'Origen JSON')
        write_project(path, 'Anterior', example_rows())
        self.assertEqual(read_project(path)[1], example_rows())

    def test_invalid_scope_or_factor_and_old_format_rejected(self):
        self.model.set_swelling([3, 4], config())
        for version in (1, 2, 3, 4):
            with self.assertRaises(ValueError):
                validate_project(dict(version=version, title='', rows=deepcopy(self.model.rows)))
        for version in (1, 2, 3):
            with self.assertRaises(ValueError):
                decode_rows(json.dumps(dict(version=version, rows=self.model.rows)).encode())
        rows = deepcopy(self.model.rows)
        rows[1]['volume_factor'] = rows[3]['volume_factor']
        with self.assertRaises(ValueError):
            validate_project(dict(version=5, title='', rows=rows))
        write_database(self.path, 'Obra', self.model.rows)
        with closing(sqlite3.connect(self.path)) as con, con:
            con.execute("UPDATE detail_swelling SET factor='nan'")
        with self.assertRaises(ValueError):
            read_database(self.path)

    def test_legacy_and_detail_adjustments_cannot_be_combined(self):
        self.model.set_swelling([3, 4], config())
        rows = deepcopy(self.model.rows)
        rows[1]['swelling'] = dict(enabled=True, percent='25', note='Origen')
        with self.assertRaises(ValueError):
            write_database(self.path, 'Obra', rows)
        self.assertFalse(self.path.exists())
        with self.assertRaises(ValueError):
            write_project(self.path.with_suffix('.json'), 'Obra', rows)

    def test_legacy_clipboard_conversion_preserves_total(self):
        rows = volume_rows()[1:7]
        for row in rows:
            row['level'] -= 1
        rows[0]['swelling'] = dict(enabled=True, percent='25', note='Origen')
        decoded = decode_rows(json.dumps(dict(version=3, rows=rows)).encode())
        self.assertNotIn('swelling', decoded[0])
        self.assertEqual(calculate(decoded, engine)[0][(0, 13)], 120)


class BlockUiTests(unittest.TestCase):
    def setUp(self):
        self.window = PlantillaWindow(engine)
        self.window._load('FE por bloques', volume_rows())
        self.window.show()
        self.window.activateWindow()
        self.window._select(3)
        APP.processEvents()

    def tearDown(self):
        with patch.object(self.window, '_can_discard', return_value=True):
            self.window.close()
        self.window.deleteLater()
        APP.processEvents()
        QApplication.clipboard().clear()

    def select_block(self, start, end):
        self.window._select(start)
        selection = QItemSelection(self.window.model.index(start, 1), self.window.model.index(end, 10))
        self.window.table.selectionModel().select(selection, QItemSelectionModel.ClearAndSelect)

    def test_direct_factor_dialog_preview_validation_cancel_and_remove(self):
        dialog = SwellingDialog(2, 48, engine, parent=self.window)
        self.assertEqual(dialog.factor.text(), '')
        self.assertFalse(dialog.buttons.button(QDialogButtonBox.Ok).isEnabled())
        dialog.factor.setText('1,20')
        self.assertIn('57.60 m³', dialog.preview.text())
        self.assertEqual(dialog.configuration()['factor'], '1,20')
        for value in ('0.9', 'nan', ''):
            dialog.factor.setText(value)
            self.assertFalse(dialog.buttons.button(QDialogButtonBox.Ok).isEnabled())
            dialog.accept()
            self.assertNotEqual(dialog.result(), QDialog.Accepted)
        dialog.reject()
        dialog.deleteLater()
        dialog = SwellingDialog(2, 48, engine, config(), self.window)
        dialog.remove_factor()
        self.assertIsNone(dialog.configuration())
        self.assertEqual(dialog.result(), QDialog.Accepted)
        dialog.deleteLater()

    def test_action_only_on_m3_details(self):
        for index in range(10):
            self.window._select(index)
            self.assertEqual(self.window.swelling_action.isEnabled(), index in (3, 4, 5, 6, 8))

    def test_selection_action_ctrl_z_ctrl_y(self):
        self.select_block(3, 4)
        with patch.object(SwellingDialog, 'exec', return_value=QDialog.Accepted), \
             patch.object(SwellingDialog, 'configuration', return_value=config()):
            self.window.swelling_action.trigger()
        self.assertEqual(self.window.model.swelling_footers, {4: 3})
        self.assertAlmostEqual(self.window.model.values[(1, 13)], 105.6)
        QTest.keyClick(self.window.table, Qt.Key_Z, Qt.ControlModifier)
        self.assertEqual(self.window.model.values[(1, 13)], 96)
        QTest.keyClick(self.window.table, Qt.Key_Y, Qt.ControlModifier)
        self.assertAlmostEqual(self.window.model.values[(1, 13)], 105.6)

    def test_single_member_edits_existing_whole_block(self):
        self.window.model.set_swelling([3, 4], config())
        self.window._select(4)
        with patch.object(SwellingDialog, 'exec', return_value=QDialog.Accepted), \
             patch.object(SwellingDialog, 'configuration', return_value=config('1.5')):
            self.window.edit_swelling()
        self.assertEqual(self.window.model.swelling_footers, {4: 3})
        self.assertEqual(self.window.model.values[(1, 13)], 120)

    def test_invalid_range_is_not_applied(self):
        # Other partidas are hidden now; a visible range containing a detail
        # title is still invalid for FE and must not open the factor dialog.
        self.select_block(2, 4)
        with patch.object(QMessageBox, 'information') as message:
            self.window.edit_swelling()
        message.assert_called_once()
        self.assertEqual(self.window.model.swelling_footers, {})

    def test_compact_footer_and_widths_survive_selection_and_undo(self):
        table = self.window.table
        table.setColumnWidth(1, 550)
        widths = [table.columnWidth(c) for c in range(14)]
        self.window.model.set_swelling([3, 4], config())
        self.assertEqual(FOOTER_HEIGHT, ROW_HEIGHT)
        self.assertEqual(table.rowHeight(4), 56)
        table.setRowHeight(4, 28)
        self.assertEqual(table.rowHeight(4), 56)
        self.window._select(9)
        self.window._select(3)
        self.window.model.undo_stack.undo()
        self.assertEqual(table.rowHeight(4), 28)
        self.window.model.undo_stack.redo()
        self.assertEqual(table.rowHeight(4), 56)
        self.assertEqual([table.columnWidth(c) for c in range(14)], widths)

    def test_footer_double_click_opens_dialog_not_editor(self):
        self.window.model.set_swelling([3, 4], config())
        APP.processEvents()
        table = self.window.table
        point = QPoint(table.columnViewportPosition(8) + 15, table.rowViewportPosition(4) + ROW_HEIGHT + 12)
        self.assertEqual(table.footer_owner_at(point), 3)
        with patch.object(SwellingDialog, 'exec', return_value=QDialog.Rejected) as dialog:
            QTest.mouseDClick(table.viewport(), Qt.LeftButton, pos=point)
        dialog.assert_called_once()
        self.assertNotEqual(table.state(), QTableView.EditingState)

    def test_tables_and_fe_footer_do_not_show_hover_comments(self):
        self.window.model.set_swelling([3, 4], config())
        APP.processEvents()
        model = self.window.model
        for row in range(model.rowCount()):
            for column in range(model.columnCount()):
                self.assertIsNone(model.data(model.index(row, column), Qt.ToolTipRole))
        outline = self.window.workspace.outline
        for row in outline.node_rows:
            for column in range(outline.columnCount()):
                self.assertIsNone(outline.data(outline.for_row(row, column), Qt.ToolTipRole))
        table = self.window.table
        point = QPoint(table.columnViewportPosition(8) + 15,
                       table.rowViewportPosition(4) + ROW_HEIGHT + 12)
        event = QHelpEvent(QEvent.ToolTip, point, table.viewport().mapToGlobal(point))
        with patch('PySide6.QtWidgets.QToolTip.showText') as show:
            table.viewportEvent(event)
        show.assert_not_called()

    def test_last_detail_editor_does_not_cover_footer(self):
        self.window.model.set_swelling([3, 4], config())
        self.window._select(4, 4)
        self.window.table.edit(self.window.model.index(4, 4))
        APP.processEvents()
        editor = self.window.table.findChild(QLineEdit)
        self.assertIsNotNone(editor)
        self.assertLessEqual(editor.height(), ROW_HEIGHT)
        editor.selectAll()
        QTest.keyClicks(editor, '4')
        QTest.keyClick(editor, Qt.Key_Return)
        APP.processEvents()
        self.assertAlmostEqual(self.window.model.values[(1, 13)], 134.4)

    def test_delete_member_and_undo_reposition_footer(self):
        self.window.model.set_swelling([3, 4], config())
        self.window._select(4)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            self.window.remove_row()
        self.assertEqual(self.window.model.swelling_footers, {3: 3})
        self.assertAlmostEqual(self.window.model.values[(1, 13)], 76.8)
        self.window.model.undo_stack.undo()
        self.assertEqual(self.window.model.swelling_footers, {4: 3})
        self.assertAlmostEqual(self.window.model.values[(1, 13)], 105.6)


if __name__ == '__main__':
    unittest.main(verbosity=2)
