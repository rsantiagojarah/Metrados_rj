"""Real key events across panels, editors and keyboard-first pickers."""
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QLineEdit
import metrado._enlace as engine
from metrado.sheet import new_row
from metrado.shortcuts import FinderDialog, searchable
from metrado.steel_store import CatalogStore
from metrado.window import PlantillaWindow
from test_navigation import split_rows

APP = QApplication.instance() or QApplication([])


class KeyboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.window = PlantillaWindow(engine, CatalogStore(Path(self.temp.name) / 'steel.db'))
        self.window._load('Atajos', split_rows())
        self.window.show()
        self.window.activateWindow()
        APP.processEvents()
        self.keyboard = self.window.keyboard
        self.table = self.window.table
        self.tree = self.window.navigator
        self.model = self.window.model

    def tearDown(self):
        with patch.object(self.window, '_can_discard', return_value=True):
            self.window.close()
        self.window.deleteLater()
        APP.processEvents()
        self.temp.cleanup()

    def key(self, key, modifiers=Qt.NoModifier):
        QTest.keyClick(QApplication.focusWidget(), key, modifiers)
        APP.processEvents()

    def tree_row(self, row):
        self.tree.setCurrentIndex(self.window.workspace.outline.for_row(row, 1))
        self.tree.setFocus()
        APP.processEvents()

    def detail(self, row=4, column=4):
        self.window._select(row, column)
        self.table.setFocus()
        APP.processEvents()

    def test_shortcuts_are_unique_and_commands_cover_existing_actions(self):
        seen = {}
        for action in self.keyboard.commands:
            for sequence in action.shortcuts():
                key = sequence.toString(QKeySequence.PortableText)
                self.assertNotIn(key, seen, (key, action.text(), seen.get(key)))
                seen[key] = action.text()
        self.assertGreater(len(seen), 35)
        self.assertIn(self.window.update_steel_action, self.keyboard.commands)
        self.assertTrue(all(a in self.keyboard.commands for a in self.window.command_actions))

    def test_f6_roundtrip_restores_last_detail_and_column(self):
        self.detail(5, 6)
        before = deepcopy(self.model.rows)
        self.key(Qt.Key_F6)
        self.assertIs(QApplication.focusWidget(), self.tree)
        self.assertTrue(self.window.workspace.navigation_active)
        self.key(Qt.Key_F6)
        self.assertIs(QApplication.focusWidget(), self.table)
        self.assertEqual((self.table.currentIndex().row(), self.table.currentIndex().column()), (5, 6))
        self.assertEqual(self.model.rows, before)
        self.assertFalse(self.window._dirty)

    def test_direct_panel_keys_and_enter_escape(self):
        self.tree_row(2)
        self.key(Qt.Key_Return)
        self.assertIs(QApplication.focusWidget(), self.table)
        self.assertEqual(self.table.currentIndex().row(), 3)
        self.key(Qt.Key_Escape)
        self.assertIs(QApplication.focusWidget(), self.tree)
        self.key(Qt.Key_2, Qt.ControlModifier)
        self.assertIs(QApplication.focusWidget(), self.table)
        self.key(Qt.Key_1, Qt.ControlModifier)
        self.assertIs(QApplication.focusWidget(), self.tree)
        self.key(Qt.Key_F6, Qt.ShiftModifier)
        self.assertIs(QApplication.focusWidget(), self.table)

    def test_next_previous_skip_titles_and_keep_panel_and_memory(self):
        self.detail(5, 4)
        self.key(Qt.Key_PageDown, Qt.ControlModifier)
        self.assertEqual(self.table.currentIndex().row(), 7)
        self.assertIs(QApplication.focusWidget(), self.table)
        self.key(Qt.Key_PageDown, Qt.ControlModifier)
        self.assertEqual(self.table.currentIndex().row(), 10)
        self.key(Qt.Key_PageUp, Qt.ControlModifier)
        self.key(Qt.Key_PageUp, Qt.ControlModifier)
        self.assertEqual((self.table.currentIndex().row(), self.table.currentIndex().column()), (5, 4))
        self.key(Qt.Key_1, Qt.ControlModifier)
        self.key(Qt.Key_PageDown, Qt.ControlModifier)
        self.assertIs(QApplication.focusWidget(), self.tree)
        self.assertEqual(self.window.workspace.outline.source_row(self.tree.currentIndex()), 6)

    def test_navigation_through_collapsed_titles_and_boundaries(self):
        self.tree_row(0)
        self.tree.collapseAll()
        self.key(Qt.Key_PageDown, Qt.ControlModifier)
        self.assertEqual(self.table.currentIndex().row(), 2)
        self.assertTrue(self.tree.isExpanded(self.window.workspace.outline.for_row(0)))
        self.key(Qt.Key_PageUp, Qt.ControlModifier)
        self.assertEqual(self.table.currentIndex().row(), 2)
        self.assertIn('No hay otra partida', self.window.statusBar().currentMessage())

    def test_empty_partida_and_no_selection_are_safe(self):
        self.window._load('Vacía', [new_row('item', description='Vacía', unit='m3', level=0)])
        self.tree_row(0)
        self.key(Qt.Key_2, Qt.ControlModifier)
        self.assertIs(QApplication.focusWidget(), self.table)
        self.assertEqual(self.table.currentIndex().row(), 0)
        self.assertTrue(self.table.isRowHidden(0))
        self.key(Qt.Key_Return, Qt.ControlModifier)
        self.window._commit_editors()
        self.assertEqual(self.model.rows[1]['kind'], 'detail')
        self.window._load('', [])
        self.keyboard.next_item(1)
        self.keyboard.focus_panel(False)
        self.assertEqual(self.model.rowCount(), 0)

    def test_title_is_not_opened_as_a_measurement(self):
        self.tree_row(0)
        self.key(Qt.Key_Return)
        self.assertIs(QApplication.focusWidget(), self.tree)
        self.assertIn('Elige una partida', self.window.statusBar().currentMessage())

    def test_switching_panels_commits_editor_and_preserves_undo(self):
        self.detail()
        self.key(Qt.Key_F2)
        editor = QApplication.focusWidget()
        self.assertIsInstance(editor, QLineEdit)
        editor.setText('15')
        self.key(Qt.Key_F6)
        self.assertEqual(self.model.rows[4]['cells'][4], '15')
        self.assertIs(QApplication.focusWidget(), self.tree)
        self.key(Qt.Key_Z, Qt.ControlModifier)
        self.assertEqual(self.model.rows[4]['cells'][4], '2')

    def test_escape_in_editor_cancels_without_switching_panel(self):
        self.detail()
        self.key(Qt.Key_F2)
        QApplication.focusWidget().setText('987')
        self.key(Qt.Key_Escape)
        self.assertEqual(self.model.rows[4]['cells'][4], '2')
        self.assertIs(QApplication.focusWidget(), self.table)
        self.assertFalse(self.window.workspace.navigation_active)

    def test_text_undo_and_copy_are_not_hijacked(self):
        self.detail()
        self.key(Qt.Key_F2)
        editor = QApplication.focusWidget()
        editor.selectAll()
        QTest.keyClicks(editor, '123')
        self.key(Qt.Key_Z, Qt.ControlModifier)
        self.assertEqual(self.model.undo_stack.count(), 0)
        self.assertIs(QApplication.focusWidget(), editor)
        editor.setText('Texto')
        editor.selectAll()
        self.key(Qt.Key_C, Qt.ControlModifier)
        self.assertEqual(QApplication.clipboard().text(), 'Texto')
        self.key(Qt.Key_Escape)

    def test_shift_space_selects_whole_detail_for_copy(self):
        self.detail()
        self.key(Qt.Key_Space, Qt.ShiftModifier)
        selected = self.table.selectionModel().selectedRows()
        self.assertEqual([i.row() for i in selected], [4])
        self.assertEqual(self.model.undo_stack.count(), 0)

    def test_ctrl_home_end_stay_inside_current_partida(self):
        self.detail(4, 4)
        self.key(Qt.Key_End, Qt.ControlModifier)
        self.assertEqual(self.table.currentIndex().row(), 5)
        self.key(Qt.Key_Home, Qt.ControlModifier)
        self.assertEqual(self.table.currentIndex().row(), 3)

    def test_global_and_contextual_form_shortcuts(self):
        self.detail(10, 4)
        for action, key in ((self.window.hooks_action, Qt.Key_H),
                             (self.window.catalog_action, Qt.Key_A),
                             (self.window.update_steel_action, Qt.Key_U),
                             (self.window.export_action, Qt.Key_J)):
            action.triggered.disconnect()
            seen = []
            action.triggered.connect(lambda checked=False: seen.append(True))
            self.key(key, Qt.ControlModifier | Qt.ShiftModifier)
            self.assertEqual(seen, [True], action.text())
        self.detail(4, 4)
        self.window.swelling_action.triggered.disconnect()
        seen = []
        self.window.swelling_action.triggered.connect(lambda checked=False: seen.append(True))
        self.key(Qt.Key_E, Qt.ControlModifier | Qt.ShiftModifier)
        self.assertEqual(seen, [True])

    def test_rename_project_shortcut_and_help(self):
        self.detail()
        self.key(Qt.Key_L, Qt.ControlModifier)
        self.assertIs(QApplication.focusWidget(), self.window.title_edit)
        self.assertEqual(self.window.title_edit.selectedText(), 'Atajos')
        with patch.object(self.keyboard, 'picker', return_value=None) as picker:
            self.key(Qt.Key_F1)
        self.assertEqual(picker.call_args.args[0], 'Atajos de teclado')
        self.assertTrue(picker.call_args.kwargs['reference'])

    def test_find_partida_by_keyboard_opens_selected_result(self):
        self.detail()
        with patch.object(self.keyboard, 'picker', return_value=9) as picker:
            self.key(Qt.Key_F, Qt.ControlModifier)
        entries = picker.call_args.args[1]
        self.assertEqual([e[2] for e in entries], [2, 6, 9])
        self.assertEqual(self.table.currentIndex().row(), 10)
        self.assertIs(QApplication.focusWidget(), self.table)

    def test_palette_executes_same_existing_action_and_disabled_cannot_run(self):
        self.detail()
        before = deepcopy(self.model.rows)
        with patch.object(self.keyboard, 'picker', return_value=self.window.row_actions['down']):
            self.key(Qt.Key_K, Qt.ControlModifier)
        self.assertEqual(self.model.rows[5]['cells'][1], before[4]['cells'][1])
        self.key(Qt.Key_Z, Qt.ControlModifier)
        self.assertEqual(self.model.rows, before)
        self.window.hooks_action.setEnabled(False)
        with patch.object(self.keyboard, 'picker', return_value=self.window.hooks_action), \
             patch.object(self.window, 'edit_steel_hooks') as hook:
            self.keyboard.command_palette()
        hook.assert_not_called()

    def test_memory_survives_reorder_and_undo_by_identity(self):
        self.detail(4, 5)
        identity = self.model.rows[4]['id']
        self.window.move_row(1)
        self.key(Qt.Key_F6)
        self.key(Qt.Key_F6)
        self.assertEqual(self.model.rows[self.table.currentIndex().row()]['id'], identity)
        self.key(Qt.Key_Z, Qt.ControlModifier)
        self.key(Qt.Key_F6)
        self.key(Qt.Key_F6)
        self.assertEqual(self.model.rows[self.table.currentIndex().row()]['id'], identity)

    def test_modal_picker_blocks_window_shortcuts_and_escape_restores_focus(self):
        self.detail()
        before = deepcopy(self.model.rows)
        seen = []
        def interact():
            dialog = QApplication.activeModalWidget()
            seen.append(isinstance(dialog, FinderDialog))
            QTest.keyClick(dialog.search, Qt.Key_Return, Qt.ControlModifier)
            QTest.keyClick(dialog.search, Qt.Key_Escape)
        QTimer.singleShot(20, interact)
        self.keyboard.picker('Prueba', [])
        APP.processEvents()
        self.assertEqual(seen, [True])
        self.assertEqual(self.model.rows, before)
        self.assertIs(QApplication.focusWidget(), self.table)

    def test_real_ctrl_f_dialog_accepts_result_without_mouse(self):
        self.detail()
        observed = []
        def interact():
            dialog = QApplication.activeModalWidget()
            observed.append(isinstance(dialog, FinderDialog))
            QTest.keyClicks(dialog.search, 'areas')
            QTest.keyClick(dialog.search, Qt.Key_Return)
        QTimer.singleShot(20, interact)
        self.key(Qt.Key_F, Qt.ControlModifier)
        self.assertEqual(observed, [True])
        self.assertEqual(self.table.currentIndex().row(), 7)
        self.assertIs(QApplication.focusWidget(), self.table)

    def test_real_ctrl_k_move_is_one_undo_operation(self):
        self.detail()
        before = deepcopy(self.model.rows)
        def interact():
            dialog = QApplication.activeModalWidget()
            QTest.keyClicks(dialog.search, 'bajar')
            QTest.keyClick(dialog.search, Qt.Key_Return)
        QTimer.singleShot(20, interact)
        self.key(Qt.Key_K, Qt.ControlModifier)
        self.assertEqual(self.model.rows[5]['cells'][1], before[4]['cells'][1])
        self.assertEqual(self.model.undo_stack.count(), 1)
        self.key(Qt.Key_Z, Qt.ControlModifier)
        self.assertEqual(self.model.rows, before)

    def test_picker_cancel_restores_title_focus(self):
        self.window.title_edit.setFocus()
        APP.processEvents()
        QTimer.singleShot(20, lambda: QApplication.activeModalWidget().reject())
        self.keyboard.help()
        APP.processEvents()
        self.assertIs(QApplication.focusWidget(), self.window.title_edit)

    def test_switching_from_edited_tree_commits_before_opening_sheet(self):
        self.tree_row(2)
        self.key(Qt.Key_F2)
        editor = QApplication.focusWidget()
        self.assertIsInstance(editor, QLineEdit)
        editor.setText('Excavación modificada')
        self.key(Qt.Key_2, Qt.ControlModifier)
        self.assertEqual(self.model.rows[2]['cells'][1], 'Excavación modificada')
        self.assertIs(QApplication.focusWidget(), self.table)
        self.key(Qt.Key_Z, Qt.ControlModifier)
        self.assertEqual(self.model.rows[2]['cells'][1], 'EXCAVACIÓN')


class FinderTests(unittest.TestCase):
    def setUp(self):
        self.dialog = FinderDialog('Buscar', [
            ('Excavación de zanjas', 'Ctrl+E', 2, True),
            ('Acero — Ganchos', 'Ctrl+H', 9, True),
            ('Aplicar ganchos', 'Ctrl+Shift+H', 10, False)])
        self.dialog.show()
        APP.processEvents()

    def tearDown(self):
        self.dialog.close()
        self.dialog.deleteLater()
        APP.processEvents()

    def test_search_ignores_case_accents_and_accepts_multiple_words(self):
        self.assertEqual(searchable('ÁREAS'), 'areas')
        self.dialog.search.setText('ZANJAS excava')
        self.assertEqual(self.dialog.results.count(), 1)
        QTest.keyClick(self.dialog.search, Qt.Key_Return)
        self.assertEqual(self.dialog.chosen, 2)

    def test_arrow_keys_choose_from_search_without_mouse(self):
        QTest.keyClick(self.dialog.search, Qt.Key_Down)
        self.assertEqual(self.dialog.results.currentRow(), 1)
        QTest.keyClick(self.dialog.search, Qt.Key_Down)
        self.assertEqual(self.dialog.results.currentRow(), 1)  # Disabled command is skipped
        QTest.keyClick(self.dialog.search, Qt.Key_Return)
        self.assertEqual(self.dialog.chosen, 9)

    def test_disabled_command_and_empty_results_cannot_be_accepted(self):
        self.dialog.search.setText('aplicar')
        self.assertFalse(self.dialog.buttons.button(QDialogButtonBox.Ok).isEnabled())
        self.dialog.accept()
        self.assertIsNone(self.dialog.chosen)
        self.dialog.search.setText('no existe')
        self.assertEqual(self.dialog.results.count(), 0)
        self.assertEqual(self.dialog.summary.text(), 'Sin coincidencias.')
        QTest.keyClick(self.dialog.search, Qt.Key_Escape)
        self.assertEqual(self.dialog.result(), QDialog.Rejected)


if __name__ == '__main__':
    unittest.main()
