"""SQLite integrity, session history and real Qt keyboard/file workflows."""
from copy import deepcopy
from contextlib import closing
from pathlib import Path
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QLineEdit, QMessageBox

import metrado._enlace as engine
from metrado.database import ConflictError, open_document, read_database, write_database
from metrado.grid import SheetModel, WIDTHS
from metrado.hierarchy import materialize, move_sibling, move_to
from metrado.identity import ensure_ids
from metrado.sheet import calculate, example_rows, new_row, read_project, write_project
from metrado.window import PlantillaWindow
from test_detail_groups import grouped_rows

APP = QApplication.instance() or QApplication([])


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'Obra á ñ.metrado.db'
        self.rows = grouped_rows()
        ensure_ids(self.rows)

    def tearDown(self):
        self.temp.cleanup()

    def test_relational_roundtrip_unicode_groups_and_query(self):
        revision = write_database(self.path, 'Obra Perú', self.rows)
        self.assertEqual(read_database(self.path), ('Obra Perú', self.rows, revision))
        with closing(sqlite3.connect(self.path)) as con, con:
            self.assertEqual(con.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(con.execute('PRAGMA foreign_key_check').fetchall(), [])
            self.assertEqual(con.execute('SELECT description FROM nodes WHERE parent_id=? ORDER BY position',
                                         (self.rows[6]['id'],)).fetchall(),
                             [(self.rows[7]['cells'][1],), (self.rows[8]['cells'][1],)])
        self.assertEqual(open_document(self.path), read_database(self.path))

    def test_all_steel_inputs_and_incomplete_values_roundtrip(self):
        rows = materialize(example_rows())
        ensure_ids(rows)
        rows[15]['cells'][4] = '10,85'
        rows[16]['cells'][4] = 'pendiente'
        write_database(self.path, 'Acero', rows)
        loaded = read_database(self.path)[1]
        self.assertEqual(loaded, rows)
        self.assertEqual(calculate(loaded, engine), calculate(rows, engine))

    def test_incremental_save_only_updates_changed_node(self):
        revision = write_database(self.path, 'Obra', self.rows)
        with closing(sqlite3.connect(self.path)) as con, con:
            con.execute('CREATE TABLE audit (id TEXT)')
            con.execute('CREATE TRIGGER count_updates AFTER UPDATE ON nodes BEGIN INSERT INTO audit VALUES (NEW.id); END')
        self.rows[7]['cells'][4] = '130,10'
        next_revision = write_database(self.path, 'Obra', self.rows, revision)
        self.assertEqual(next_revision, revision + 1)
        with closing(sqlite3.connect(self.path)) as con, con:
            self.assertEqual(con.execute('SELECT id FROM audit').fetchall(), [(self.rows[7]['id'],)])
        self.assertEqual(write_database(self.path, 'Obra', self.rows, next_revision), next_revision)
        with closing(sqlite3.connect(self.path)) as con, con:
            self.assertEqual(con.execute('SELECT count(*) FROM audit').fetchone()[0], 1)

    def test_transaction_failure_rolls_back_nodes_and_title(self):
        revision = write_database(self.path, 'Antes', self.rows)
        with closing(sqlite3.connect(self.path)) as con, con:
            con.execute("CREATE TRIGGER reject_update BEFORE UPDATE ON nodes WHEN NEW.description='FAIL' BEGIN SELECT RAISE(ABORT, 'simulated disk write failure'); END")
        before = read_database(self.path)
        changed = deepcopy(self.rows)
        changed[0]['cells'][1] = 'Changed first'
        changed[-1]['cells'][1] = 'FAIL'
        with self.assertRaises(sqlite3.IntegrityError):
            write_database(self.path, 'Después', changed, revision)
        self.assertEqual(read_database(self.path), before)

    def test_revision_conflict_preserves_other_window_changes(self):
        revision = write_database(self.path, 'Inicial', self.rows)
        write_database(self.path, 'Otra ventana', self.rows, revision)
        with self.assertRaises(ConflictError):
            write_database(self.path, 'Mi cambio', self.rows, revision)
        self.assertEqual(read_database(self.path)[0], 'Otra ventana')

    def test_missing_original_is_not_silently_recreated(self):
        with self.assertRaises(ConflictError):
            write_database(self.path, 'Obra', self.rows, 1)
        self.assertFalse(self.path.exists())

    def test_failed_initial_save_leaves_no_partial_database(self):
        with patch('metrado.database._create_schema', side_effect=sqlite3.OperationalError('disk full')):
            with self.assertRaises(sqlite3.OperationalError):
                write_database(self.path, 'Obra', self.rows)
        self.assertFalse(self.path.exists())
        self.assertEqual(list(self.path.parent.iterdir()), [])
        write_database(self.path, 'Obra', self.rows)
        self.assertEqual(read_database(self.path)[0], 'Obra')

    def test_unknown_version_and_foreign_database_are_not_overwritten(self):
        with closing(sqlite3.connect(self.path)) as con, con:
            con.execute('CREATE TABLE unrelated (id INTEGER)')
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            write_database(self.path, 'Obra', self.rows)
        self.assertEqual(before, self.path.read_bytes())
        other = self.path.with_name('version.db')
        write_database(other, 'Obra', self.rows)
        with closing(sqlite3.connect(other)) as con, con:
            con.execute('PRAGMA user_version=999')
        before = other.read_bytes()
        with self.assertRaises(ValueError):
            read_database(other)
        with self.assertRaises(ValueError):
            write_database(other, 'Cambio', self.rows)
        self.assertEqual(other.read_bytes(), before)

    def test_legacy_json_import_remains_unchanged(self):
        for rows in (example_rows(), grouped_rows()):
            path = self.path.with_suffix('.json')
            write_project(path, 'Anterior', rows)
            before = path.read_bytes()
            title, imported, revision = open_document(path)
            self.assertIsNone(revision)
            self.assertEqual(title, 'Anterior')
            self.assertEqual(len({r['id'] for r in imported}), len(rows))
            self.assertEqual(calculate(rows, engine), calculate(imported, engine))
            self.assertEqual(before, path.read_bytes())

    def test_duplicate_ids_and_invalid_hierarchy_rejected_before_write(self):
        write_database(self.path, 'Original', self.rows)
        before = self.path.read_bytes()
        self.rows[1]['id'] = self.rows[0]['id']
        with self.assertRaises(ValueError):
            write_database(self.path, 'Cambio', self.rows)
        self.assertEqual(self.path.read_bytes(), before)

    def test_corrupt_parent_or_position_rejected(self):
        write_database(self.path, 'Obra', self.rows)
        with closing(sqlite3.connect(self.path)) as con, con:
            con.execute('UPDATE nodes SET parent_id=? WHERE id=?', (self.rows[2]['id'], self.rows[7]['id']))
        with self.assertRaises(ValueError):
            read_database(self.path)

    def test_corrupt_sqlite_file_reports_error_and_releases_handle(self):
        self.path.write_bytes(b'SQLite format 3\x00' + b'not a database' * 20)
        with self.assertRaises(sqlite3.DatabaseError):
            open_document(self.path)
        # On Windows replacement also verifies that failed setup closed its handle.
        self.path.rename(self.path.with_name('corrupt.db'))

    def test_moving_and_deleting_subtrees_preserves_ids(self):
        revision = write_database(self.path, 'Obra', self.rows)
        moved, _ = move_to(self.rows, 5, 9)
        revision = write_database(self.path, 'Obra', moved, revision)
        self.assertEqual(read_database(self.path)[1], moved)
        self.assertEqual({r['id'] for r in moved}, {r['id'] for r in self.rows})
        write_database(self.path, 'Obra', [], revision)
        self.assertEqual(read_database(self.path)[1], [])


class HistoryModelTests(unittest.TestCase):
    def setUp(self):
        self.model = SheetModel(engine, grouped_rows())
        self.stack = self.model.undo_stack

    def test_cell_undo_redo_restores_input_and_totals(self):
        before = deepcopy(self.model.rows)
        totals = dict(self.model.values)
        self.assertTrue(self.model.setData(self.model.index(4, 4), '50,2'))
        after = deepcopy(self.model.rows)
        self.assertEqual(self.stack.count(), 1)
        command = self.stack.command(0)
        self.assertEqual(len(command.before), 1)
        self.stack.undo()
        self.assertEqual(self.model.rows, before)
        self.assertEqual(self.model.values, totals)
        self.stack.redo()
        self.assertEqual(self.model.rows, after)

    def test_unit_undo_restores_nested_dimensions_and_direct_quantities(self):
        before = deepcopy(self.model.rows)
        totals = dict(self.model.values)
        self.model.setData(self.model.index(1, 2), 'kg')
        after = deepcopy(self.model.rows)
        self.assertEqual(after[6]['cells'][2], 'kg')
        self.assertEqual(after[3]['direct'], '')
        self.stack.undo()
        self.assertEqual(self.model.rows, before)
        self.assertEqual(self.model.values, totals)
        self.stack.redo()
        self.assertEqual(self.model.rows, after)

    def test_steel_diameter_description_and_bar_count_roundtrip(self):
        self.model.replace(example_rows())
        for column, value in ((9, '1/2"'), (7, '123'), (1, '45 Ø3/4"')):
            before = deepcopy(self.model.rows)
            self.assertTrue(self.model.setData(self.model.index(15, column), value))
            after = deepcopy(self.model.rows)
            totals = dict(self.model.values)
            self.stack.undo()
            self.assertEqual(self.model.rows, before)
            self.stack.redo()
            self.assertEqual(self.model.rows, after)
            self.assertEqual(self.model.values, totals)

    def test_direct_quantity_restores_dimensions(self):
        before = deepcopy(self.model.rows)
        self.model.set_direct(4, '456,7')
        self.stack.undo()
        self.assertEqual(self.model.rows, before)
        self.stack.redo()
        self.assertEqual(self.model.rows[4]['direct'], '456,7')
        self.assertEqual(self.model.rows[4]['cells'][4:7], ['', '', ''])

    def test_paste_is_single_operation_and_invalid_paste_has_no_history(self):
        before = deepcopy(self.model.rows)
        self.model.paste_cells(7, 4, [['12', '2', '0.1'], ['13', '3', '0.2']])
        after = deepcopy(self.model.rows)
        self.assertEqual(self.stack.count(), 1)
        self.stack.undo()
        self.assertEqual(self.model.rows, before)
        self.stack.redo()
        self.assertEqual(self.model.rows, after)
        with self.assertRaises(ValueError):
            self.model.paste_cells(1, 2, [['BAD']])
        self.assertEqual(self.stack.count(), 1)
        self.assertEqual(self.model.rows, after)

    def test_noop_and_rejected_edit_do_not_pollute_history(self):
        self.assertFalse(self.model.setData(self.model.index(1, 2), 'm3'))
        self.assertFalse(self.model.setData(self.model.index(1, 2), 'invalid'))
        self.assertFalse(self.model.setData(self.model.index(1, 13), '123'))
        self.model.set_direct(4, '123')
        self.model.set_direct(4, '123')
        self.assertEqual(self.stack.count(), 1)

    def test_edit_after_undo_clears_redo_and_load_clears_history(self):
        self.model.setData(self.model.index(4, 4), '50')
        self.stack.undo()
        self.model.setData(self.model.index(4, 4), '60')
        self.assertFalse(self.stack.canRedo())
        self.model.replace([])
        self.assertEqual(self.stack.count(), 0)
        self.assertTrue(self.stack.isClean())

    def test_cell_edits_use_incremental_calculation_for_undo_too(self):
        with patch('metrado.grid.calculate', wraps=calculate) as calc:
            self.model.setData(self.model.index(10, 4), '2')
            self.stack.undo()
            self.stack.redo()
        self.assertEqual([len(call.args[0]) for call in calc.call_args_list], [2, 2, 2])

    def test_history_is_bounded(self):
        for index in range(220):
            self.model.setData(self.model.index(10, 4), str(index + 2))
        self.assertEqual(self.stack.count(), 200)


class HistoryWindowTests(unittest.TestCase):
    def setUp(self):
        self.window = PlantillaWindow(engine)
        self.window._load('Obra', grouped_rows())
        self.window.show()
        self.window.activateWindow()
        self.window._select(4, 4)
        APP.processEvents()
        self.model = self.window.model
        self.stack = self.model.undo_stack
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'Obra.metrado.db'

    def tearDown(self):
        self.window._dirty = False
        self.window.close()
        self.window.deleteLater()
        APP.processEvents()
        QApplication.clipboard().clear()
        self.temp.cleanup()

    def save(self, path=None):
        with patch.object(QFileDialog, 'getSaveFileName', return_value=(str(path or self.path), '')):
            return self.window.save_project()

    def test_keyboard_undo_redo_and_dirty_marker(self):
        before = self.model.rows[4]['cells'][4]
        self.model.setData(self.model.index(4, 4), '50')
        self.assertTrue(self.window._dirty)
        QTest.keyClick(self.window.table, Qt.Key_Z, Qt.ControlModifier)
        self.assertEqual(self.model.rows[4]['cells'][4], before)
        self.assertFalse(self.window._dirty)
        QTest.keyClick(self.window.table, Qt.Key_Y, Qt.ControlModifier)
        self.assertEqual(self.model.rows[4]['cells'][4], '50')
        QTest.keyClick(self.window.table, Qt.Key_Z, Qt.ControlModifier)
        QTest.keyClick(self.window.table, Qt.Key_Z, Qt.ControlModifier | Qt.ShiftModifier)
        self.assertEqual(self.model.rows[4]['cells'][4], '50')
        self.assertIn('edición', self.window.undo_action.text())

    def test_native_cell_text_undo_does_not_undo_document(self):
        self.model.setData(self.model.index(4, 4), '50')
        self.window.table.edit(self.model.index(4, 4))
        APP.processEvents()
        editor = self.window.table.findChild(QLineEdit)
        self.assertIsNotNone(editor)
        editor.selectAll()
        QTest.keyClicks(editor, '789')
        QTest.keyClick(editor, Qt.Key_Z, Qt.ControlModifier)
        self.assertEqual(editor.text(), '50')
        self.assertEqual(self.stack.index(), 1)
        QTest.keyClick(editor, Qt.Key_Escape)

    def test_save_keeps_history_and_undo_makes_saved_document_dirty(self):
        before = deepcopy(self.model.rows)
        self.model.setData(self.model.index(4, 4), '50')
        self.assertTrue(self.save())
        self.assertFalse(self.window._dirty)
        self.assertEqual(self.stack.count(), 1)
        self.stack.undo()
        self.assertEqual(self.model.rows, before)
        self.assertTrue(self.window._dirty)
        self.stack.redo()
        self.assertFalse(self.window._dirty)
        self.stack.undo()
        self.assertTrue(self.window.save_project())
        self.assertEqual(read_database(self.path)[1], before)

    def test_ctrl_s_commits_active_cell_editor(self):
        self.window.table.edit(self.model.index(4, 4))
        APP.processEvents()
        editor = self.window.table.findChild(QLineEdit)
        editor.selectAll()
        QTest.keyClicks(editor, '55.7')
        with patch.object(QFileDialog, 'getSaveFileName', return_value=(str(self.path), '')):
            QTest.keyClick(editor, Qt.Key_S, Qt.ControlModifier)
        self.assertEqual(read_database(self.path)[1][4]['cells'][4], '55.7')
        self.assertEqual(self.stack.count(), 1)

    def test_discard_prompt_includes_uncommitted_cell(self):
        self.window.table.edit(self.model.index(4, 4))
        APP.processEvents()
        editor = self.window.table.findChild(QLineEdit)
        editor.selectAll()
        QTest.keyClicks(editor, '61')
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Cancel) as question:
            self.assertFalse(self.window._can_discard())
        question.assert_called_once()
        self.assertEqual(self.model.rows[4]['cells'][4], '61')

    def test_movement_levels_selection_and_widths_restore(self):
        self.window.table.setColumnWidth(1, 550)
        self.window._select(5)
        before = deepcopy(self.model.rows)
        self.window.move_to_parent(9)
        moved = deepcopy(self.model.rows)
        self.assertNotEqual(moved, before)
        self.stack.undo()
        self.assertEqual(self.model.rows, before)
        self.assertEqual(self.window.table.currentIndex().row(), 5)
        self.stack.redo()
        self.assertEqual(self.model.rows, moved)
        self.assertEqual(self.window.table.columnWidth(1), 550)
        self.stack.undo()
        self.window._select(5)
        self.window.indent_row(True)
        self.stack.undo()
        self.assertEqual(self.model.rows, before)

    def test_delete_entire_group_and_restore_its_children(self):
        self.window._select(5)
        before = deepcopy(self.model.rows)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            self.window.remove_row()
        self.assertEqual(len(self.model.rows), len(before) - 4)
        self.stack.undo()
        self.assertEqual(self.model.rows, before)
        self.assertAlmostEqual(self.model.values[(1, 13)], 42.5226)
        self.stack.redo()
        self.assertEqual(len(self.model.rows), len(before) - 4)

    def test_create_edit_undo_and_redo_independent_snapshots(self):
        self.window._select(1)
        before = deepcopy(self.model.rows)
        with patch.object(self.window.table, 'edit'):
            self.window.add_row('detail_group')
        created = deepcopy(self.model.rows)
        self.model.setData(self.model.index(2, 1), 'VEREDA NUEVA')
        edited = deepcopy(self.model.rows)
        self.stack.undo()
        self.stack.undo()
        self.assertEqual(self.model.rows, before)
        self.stack.redo()
        self.assertEqual(self.model.rows, created)
        self.stack.redo()
        self.assertEqual(self.model.rows, edited)

    def test_copy_block_has_new_ids_and_redo_keeps_them(self):
        self.window._select(5)
        self.window.copy_selection(True)
        self.window._select(9)
        before = deepcopy(self.model.rows)
        self.window.paste_selection()
        pasted = deepcopy(self.model.rows)
        self.assertEqual(len({r['id'] for r in pasted}), len(pasted))
        self.assertEqual(self.stack.count(), 1)
        self.stack.undo()
        self.assertEqual(self.model.rows, before)
        self.stack.redo()
        self.assertEqual(self.model.rows, pasted)
        self.assertTrue(self.save())
        self.assertEqual(read_database(self.path)[1], pasted)

    def test_title_undo_save_and_new_document_reset(self):
        self.window.title_edit.setFocus()
        self.window.title_edit.selectAll()
        QTest.keyClicks(self.window.title_edit, 'Obra nueva')
        self.window.table.setFocus()
        APP.processEvents()
        self.assertTrue(self.window._dirty)
        self.stack.undo()
        self.assertEqual(self.window.title_edit.text(), 'Obra')
        self.assertFalse(self.window._dirty)
        self.stack.redo()
        self.assertEqual(self.window.title_edit.text(), 'Obra nueva')
        self.assertTrue(self.save())
        self.assertEqual(read_database(self.path)[0], 'Obra nueva')
        self.window.new_project()
        self.assertEqual(self.stack.count(), 0)
        self.assertFalse(self.window._dirty)

    def test_import_save_export_and_reopen(self):
        source = self.path.with_suffix('.json')
        write_project(source, 'Importado', grouped_rows())
        original = source.read_bytes()
        with patch.object(QFileDialog, 'getOpenFileName', return_value=(str(source), '')):
            self.window.open_project()
        self.assertIsNone(self.window._path)
        self.assertTrue(self.window._dirty)
        self.assertTrue(self.save())
        self.assertEqual(original, source.read_bytes())
        exported = source.with_name('exportado.json')
        with patch.object(QFileDialog, 'getSaveFileName', return_value=(str(exported), '')):
            self.assertTrue(self.window.export_json())
        self.assertFalse(self.window._dirty)
        self.assertEqual(read_project(exported)[1], self.model.rows)
        with patch.object(QFileDialog, 'getOpenFileName', return_value=(str(self.path), '')):
            self.window.open_project()
        self.assertEqual(self.window._path, self.path)
        self.assertFalse(self.window._dirty)
        self.assertEqual(self.stack.count(), 0)

    def test_save_conflict_warns_without_marking_clean(self):
        self.assertTrue(self.save())
        write_database(self.path, 'Desde otra ventana', self.model.rows)
        self.model.setData(self.model.index(4, 4), '99')
        with patch.object(QMessageBox, 'warning') as warning:
            self.assertFalse(self.window.save_project())
        warning.assert_called_once()
        self.assertTrue(self.window._dirty)
        self.assertEqual(read_database(self.path)[0], 'Desde otra ventana')


if __name__ == '__main__':
    unittest.main(verbosity=2)
