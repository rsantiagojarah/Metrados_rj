"""Deletion follows the active panel's selection, not only its current cell."""
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QItemSelectionModel, QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
import metrado._enlace as engine
from metrado.steel_store import CatalogStore
from metrado.window import PlantillaWindow
from test_navigation import split_rows

APP = QApplication.instance() or QApplication([])


class DeleteSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.window = PlantillaWindow(engine, CatalogStore(Path(self.temp.name) / 'steel.db'))
        self.window._load('Eliminar selección', split_rows())
        self.window.show()
        self.window.activateWindow()
        APP.processEvents()
        self.model = self.window.model
        self.table = self.window.table
        self.tree = self.window.navigator

    def tearDown(self):
        with patch.object(self.window, '_can_discard', return_value=True):
            self.window.close()
        self.window.deleteLater()
        APP.processEvents()
        self.temp.cleanup()

    def select_details(self, rows):
        self.window._select(rows[0], 1)
        self.table.setFocus()
        for row in rows[1:]:
            self.table.selectionModel().select(self.model.index(row, 1), QItemSelectionModel.Select)
        APP.processEvents()

    def select_nodes(self, rows):
        outline = self.window.workspace.outline
        self.tree.setCurrentIndex(outline.for_row(rows[0], 1))
        self.tree.setFocus()
        for row in rows[1:]:
            self.tree.selectionModel().select(outline.for_row(row), QItemSelectionModel.Select | QItemSelectionModel.Rows)
        APP.processEvents()

    def remove(self):
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes) as question:
            self.window.remove_row()
        return question

    def test_consecutive_details_delete_together_and_undo_once(self):
        self.select_details([4, 5])
        before = deepcopy(self.model.rows)
        question = self.remove()
        self.assertEqual(len(self.model.rows), len(before) - 2)
        self.assertNotIn('Tramo A', [r['cells'][1] for r in self.model.rows])
        self.assertNotIn('Tramo B', [r['cells'][1] for r in self.model.rows])
        question.assert_called_once()
        self.assertIn('2 fila(s)', question.call_args.args[2])
        self.assertEqual(self.model.undo_stack.count(), 1)
        after = deepcopy(self.model.rows)
        self.model.undo_stack.undo()
        self.assertEqual(self.model.rows, before)
        self.model.undo_stack.redo()
        self.assertEqual(self.model.rows, after)

    def test_non_consecutive_details_keep_unselected_middle(self):
        rows = deepcopy(self.model.rows)
        extra = deepcopy(rows[5])
        extra.pop('id')
        extra['cells'][1] = 'Tramo C'
        rows.insert(6, extra)
        self.model.replace(rows)
        self.select_details([4, 6])
        self.remove()
        descriptions = [r['cells'][1] for r in self.model.rows]
        self.assertIn('Tramo B', descriptions)
        self.assertNotIn('Tramo A', descriptions)
        self.assertNotIn('Tramo C', descriptions)
        self.assertEqual(self.table.currentIndex().row(), 4)
        self.assertEqual(self.model.values[(2, 13)], 24)

    def test_two_partidas_remove_their_details_but_keep_other_partida(self):
        self.select_nodes([2, 6])
        before = deepcopy(self.model.rows)
        question = self.remove()
        self.assertIn('6 fila(s)', question.call_args.args[2])
        descriptions = [r['cells'][1] for r in self.model.rows]
        self.assertNotIn('EXCAVACIÓN', descriptions)
        self.assertNotIn('ÁREAS', descriptions)
        self.assertIn('ACERO', descriptions)
        self.assertTrue(self.window.workspace.navigation_active)
        self.model.undo_stack.undo()
        self.assertEqual(self.model.rows, before)

    def test_parent_and_child_selection_counts_each_row_once(self):
        self.select_nodes([0, 2])
        question = self.remove()
        self.assertIn('8 fila(s)', question.call_args.args[2])
        self.assertEqual(len(self.model.rows), 3)
        self.assertEqual(self.model.rows[0]['cells'][1], 'ESTRUCTURA')
        self.assertEqual(self.model.rows[0]['cells'][0], '01')

    def test_detail_group_and_selected_descendant_not_double_counted(self):
        self.select_details([3, 5])
        question = self.remove()
        self.assertIn('3 fila(s)', question.call_args.args[2])
        self.assertEqual(self.model.values[(2, 13)], 0)
        self.assertEqual(self.table.currentIndex().row(), 2)  # Stay in the emptied item
        self.assertIn('EXCAVACIÓN', self.window.workspace.heading.text())

    def test_hidden_selection_from_another_partida_is_not_deleted(self):
        self.select_details([4, 7])
        other_id = self.model.rows[7]['id']
        self.assertTrue(self.table.isRowHidden(7))
        question = self.remove()
        self.assertIn('1 fila(s)', question.call_args.args[2])
        self.assertIn(other_id, [r['id'] for r in self.model.rows])

    def test_visible_details_take_priority_over_hidden_current_item(self):
        self.window._select(2)
        self.table.selectionModel().select(self.model.index(4, 1), QItemSelectionModel.ClearAndSelect)
        self.table.selectionModel().select(self.model.index(5, 1), QItemSelectionModel.Select)
        self.window.workspace.navigation_active = False
        self.assertEqual(self.table.currentIndex().row(), 2)
        question = self.remove()
        self.assertIn('2 fila(s)', question.call_args.args[2])
        self.assertEqual(self.model.rows[2]['cells'][1], 'EXCAVACIÓN')

    def test_ctrl_a_and_ctrl_delete_only_remove_visible_development(self):
        self.select_details([4])
        item_ids = [r['id'] for r in self.model.rows if r['kind'] == 'item']
        QTest.keyClick(self.table, Qt.Key_A, Qt.ControlModifier)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            QTest.keyClick(self.table, Qt.Key_Delete, Qt.ControlModifier)
        APP.processEvents()
        self.assertEqual(len(self.model.rows), 8)
        self.assertEqual(item_ids, [r['id'] for r in self.model.rows if r['kind'] == 'item'])
        self.assertEqual(self.model.values[(2, 13)], 0)
        self.assertIn('EXCAVACIÓN', self.window.workspace.heading.text())
        QTest.keyClick(self.table, Qt.Key_Z, Qt.ControlModifier)
        APP.processEvents()
        self.assertEqual(len(self.model.rows), 11)

    def test_ctrl_click_and_shift_arrow_still_extend_user_selection(self):
        self.select_details([4])
        point = self.table.visualRect(self.model.index(5, 1)).center()
        QTest.mouseClick(self.table.viewport(), Qt.LeftButton, Qt.ControlModifier, point)
        APP.processEvents()
        self.assertEqual({i.row() for i in self.table.selectionModel().selectedIndexes()}, {4, 5})
        self.window._select(4)
        QTest.keyClick(self.table, Qt.Key_Down, Qt.ShiftModifier)
        APP.processEvents()
        self.assertEqual({i.row() for i in self.table.selectionModel().selectedIndexes()}, {4, 5})
        question = self.remove()
        self.assertIn('2 fila(s)', question.call_args.args[2])
        self.assertEqual(len(self.model.rows), 9)

    def test_cancel_keeps_data_selection_and_history(self):
        self.select_details([4, 5])
        before = deepcopy(self.model.rows)
        selected = set(i.row() for i in self.table.selectionModel().selectedIndexes())
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.No):
            self.window.remove_row()
        self.assertEqual(self.model.rows, before)
        self.assertEqual(self.model.undo_stack.count(), 0)
        self.assertEqual(set(i.row() for i in self.table.selectionModel().selectedIndexes()), selected)

    def test_no_selection_does_not_delete_current_row(self):
        self.select_details([4])
        self.table.clearSelection()
        with patch.object(QMessageBox, 'question') as question:
            self.window.remove_row()
        question.assert_not_called()
        self.select_nodes([2])
        self.tree.clearSelection()
        with patch.object(QMessageBox, 'question') as question:
            self.window.remove_row()
        question.assert_not_called()
        self.assertEqual(len(self.model.rows), 11)

    def test_programmatic_navigation_after_shortcut_replaces_selection(self):
        self.select_details([4])
        QTest.keyClick(self.table, Qt.Key_C, Qt.ControlModifier)
        self.window._select(5)
        self.assertEqual({i.row() for i in self.table.selectionModel().selectedIndexes()}, {5})

    def test_delete_every_node_and_undo_restores_whole_work(self):
        self.select_nodes([0, 8])
        before = deepcopy(self.model.rows)
        question = self.remove()
        self.assertIn('11 fila(s)', question.call_args.args[2])
        self.assertEqual(self.model.rows, [])
        self.model.undo_stack.undo()
        self.assertEqual(self.model.rows, before)
        self.model.undo_stack.redo()
        self.assertEqual(self.model.rows, [])

    def test_fe_partial_deletion_and_undo_keep_factor_and_total(self):
        rows = deepcopy(self.model.rows)
        extra = deepcopy(rows[5])
        extra.pop('id')
        rows.insert(6, extra)
        self.model.replace(rows)
        self.model.set_swelling([4, 5, 6], dict(factor='1.2', note='Prueba'))
        self.select_details([4, 6])
        before = deepcopy(self.model.rows)
        self.remove()
        self.assertAlmostEqual(self.model.values[(2, 13)], 24 * 1.2)
        self.model.undo_stack.undo()
        self.assertEqual(self.model.rows, before)
        self.assertAlmostEqual(self.model.values[(2, 13)], 72 * 1.2)

    def test_context_menu_on_selected_row_preserves_multi_selection(self):
        self.select_details([4, 5])
        index = self.model.index(5, 4)  # A different column in an already selected row
        point = self.table.visualRect(index).center()
        self.assertEqual(self.table.indexAt(point), index)
        def execute():
            menu = QApplication.activePopupWidget()
            action = next(a for a in menu.actions() if a.text() == 'Eliminar bloque…')
            menu.close()
            action.trigger()
        QTimer.singleShot(20, execute)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            self.window._context_menu(point)
        self.assertEqual(len(self.model.rows), 9)

    def test_tree_context_menu_preserves_selected_partidas(self):
        self.select_nodes([2, 6])
        point = self.tree.visualRect(self.window.workspace.outline.for_row(6, 1)).center()
        def execute():
            menu = QApplication.activePopupWidget()
            action = next(a for a in menu.actions() if a.text() == 'Eliminar bloque…')
            menu.close()
            action.trigger()
        QTimer.singleShot(20, execute)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            self.window._navigation_menu(point)
        self.assertEqual(len(self.model.rows), 5)


if __name__ == '__main__':
    unittest.main()
