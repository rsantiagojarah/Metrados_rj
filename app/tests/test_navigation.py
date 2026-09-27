"""Two live panels over one document: selection, edits, history and clipboard."""
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QItemSelection, QItemSelectionModel, QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit, QMessageBox

import metrado._enlace as engine
from metrado.clipboard import ROW_MIME, decode_rows
from metrado.database import read_database
from metrado.hierarchy import renumber
from metrado.sheet import calculate, new_row, steel_detail
from metrado.window import PlantillaWindow

APP = QApplication.instance() or QApplication([])


def split_rows():
    rows = [new_row('chapter', description='OBRAS', level=0),
            new_row('chapter', description='TIERRAS', level=1),
            new_row('item', description='EXCAVACIÓN', unit='m3', level=2),
            new_row('detail_group', description='ZANJAS', unit='m3', level=3),
            new_row('detail', description='Tramo A', unit='m3', level=4),
            new_row('detail', description='Tramo B', unit='m3', level=4),
            new_row('item', description='ÁREAS', unit='m2', level=1),
            new_row('detail', description='Zona A', unit='m2', level=2),
            new_row('chapter', description='ESTRUCTURA', level=0),
            new_row('item', description='ACERO', unit='kg', level=1),
            dict(steel_detail('BARRAS', 1, 2, 0, 0, '1"', 5), level=2)]
    rows[4]['cells'][4:7] = rows[5]['cells'][4:7] = ['2', '3', '4']
    rows[7]['cells'][4:6] = ['2', '3']
    return renumber(rows)


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.window = PlantillaWindow(engine)
        self.window._load('Vista dividida', split_rows())
        self.window.show()
        self.window.activateWindow()
        APP.processEvents()
        self.model = self.window.model
        self.tree = self.window.navigator
        self.outline = self.window.workspace.outline
        self.table = self.window.table

    def tearDown(self):
        with patch.object(self.window, '_can_discard', return_value=True):
            self.window.close()
        self.window.deleteLater()
        APP.processEvents()
        QApplication.clipboard().clear()

    def visible(self):
        return [r for r in range(self.model.rowCount()) if not self.table.isRowHidden(r)]

    def navigate(self, row, column=1):
        self.tree.setCurrentIndex(self.outline.for_row(row, column))
        self.tree.setFocus()
        APP.processEvents()

    def editor(self, view, row, column):
        if view is self.tree:
            self.navigate(row, column)
        else:
            self.window._select(row, column)
            self.table.setFocus()
        QTest.keyClick(view, Qt.Key_F2)
        APP.processEvents()
        editor = QApplication.focusWidget()
        self.assertIsInstance(editor, (QLineEdit, QComboBox))
        return editor

    def test_outline_only_contains_titles_subtitles_items_and_live_totals(self):
        self.assertEqual(self.outline.node_rows, [0, 1, 2, 6, 8, 9])
        self.assertEqual(self.outline.rowCount(), 2)
        self.assertEqual(self.outline.rowCount(self.outline.for_row(0)), 2)
        self.assertEqual(self.outline.source_row(self.outline.parent(self.outline.for_row(2))), 1)
        self.assertEqual(self.outline.data(self.outline.for_row(2, 2)), 'm3')
        self.assertEqual(self.outline.data(self.outline.for_row(2, 3)), '48.00')
        self.assertFalse(self.outline.flags(self.outline.for_row(2, 3)) & Qt.ItemIsEditable)
        self.assertFalse(self.outline.flags(self.outline.for_row(1, 2)) & Qt.ItemIsEditable)

    def test_item_codes_have_no_indentation_at_any_level(self):
        rows = [new_row('chapter', '01', 'Título', level=0),
                new_row('chapter', '01.01', 'Subtítulo', level=1),
                new_row('chapter', '01.01.01', 'Grupo', level=2),
                new_row('item', '01.01.01.01', 'Partida', 'm3', level=3)]
        self.window._load('Códigos alineados', rows)
        APP.processEvents()
        before = deepcopy(self.model.rows)
        self.assertEqual(self.tree.treePosition(), 1)
        self.assertEqual(self.tree.columnWidth(0), 94)
        code_rects = [self.tree.visualRect(self.outline.for_row(r, 0)) for r in range(4)]
        self.assertEqual(len({rect.left() for rect in code_rects}), 1)
        self.assertTrue(all(rect.width() == 94 for rect in code_rects))
        descriptions = [self.tree.visualRect(self.outline.for_row(r, 1)).left() for r in range(4)]
        self.assertEqual([x - descriptions[0] for x in descriptions], [0, 0, 0, 0])
        self.assertEqual(self.tree.indentation(), 0)
        self.assertEqual(self.model.rows, before)
        self.assertEqual(self.model.undo_stack.count(), 0)

    def test_expand_controls_in_description_keep_codes_and_widths_unchanged(self):
        before = deepcopy(self.model.rows)
        widths = [self.tree.columnWidth(c) for c in range(4)]
        parent = self.outline.for_row(1)
        self.assertTrue(self.tree.isExpanded(parent))
        arrow = self.tree.disclosure_rect(self.outline.for_row(1, 1)).center()
        QTest.mouseClick(self.tree.viewport(), Qt.LeftButton, pos=arrow)
        APP.processEvents()
        self.assertFalse(self.tree.isExpanded(parent))
        QTest.mouseClick(self.tree.viewport(), Qt.LeftButton, pos=arrow)
        APP.processEvents()
        self.assertTrue(self.tree.isExpanded(parent))
        code = self.tree.visualRect(self.outline.for_row(1, 0)).center()
        QTest.mouseClick(self.tree.viewport(), Qt.LeftButton, pos=code)
        self.assertTrue(self.tree.isExpanded(parent))
        self.assertEqual([self.tree.columnWidth(c) for c in range(4)], widths)
        self.assertEqual(self.model.rows, before)
        self.assertEqual(self.model.undo_stack.count(), 0)

    def test_flat_titles_expand_with_keyboard_and_leaves_have_no_arrow(self):
        self.navigate(1, 0)
        index = self.outline.for_row(1)
        self.assertTrue(self.tree.disclosure_rect(self.outline.for_row(2, 1)).isEmpty())
        self.assertTrue(self.tree.disclosure_rect(self.outline.for_row(1, 0)).isEmpty())
        QTest.keyClick(self.tree, Qt.Key_Left)
        self.assertFalse(self.tree.isExpanded(index))
        QTest.keyClick(self.tree, Qt.Key_Right)
        self.assertTrue(self.tree.isExpanded(index))
        self.assertEqual(self.model.undo_stack.count(), 0)

    def test_flat_title_double_click_on_arrow_does_not_start_editor(self):
        self.navigate(1)
        point = self.tree.disclosure_rect(self.outline.for_row(1, 1)).center()
        QTest.mouseDClick(self.tree.viewport(), Qt.LeftButton, pos=point)
        APP.processEvents()
        self.assertNotIsInstance(QApplication.focusWidget(), QLineEdit)
        self.assertEqual(self.model.undo_stack.count(), 0)

    def test_tables_start_at_same_height_after_resize_and_selection(self):
        workspace = self.window.workspace
        before = deepcopy(self.model.rows)
        for width, left in ((1280, 320), (1480, 600), (1600, 400)):
            self.window.resize(width, 780)
            workspace.splitter.setSizes([left, width - left])
            for row in (2, 9, 0):
                self.navigate(row)
                self.assertEqual(self.tree.mapTo(workspace, QPoint()).y(),
                                 self.table.mapTo(workspace, QPoint()).y())
        self.assertEqual(self.model.rows, before)
        self.assertEqual(self.model.undo_stack.count(), 0)

    def test_compact_columns_fit_and_keep_quantity_fe_and_steel(self):
        self.assertEqual(self.table.visible_columns(), [1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
        for width in (1280, 1480, 1600):
            self.window.resize(width, 780)
            APP.processEvents()
            widths = [self.table.columnWidth(c) for c in range(14)]
            for row in (2, 6, 9, 0, 2):
                self.navigate(row)
                self.assertEqual(self.table.horizontalScrollBar().maximum(), 0)
                self.assertLessEqual(self.table.horizontalHeader().length(), self.table.viewport().width())
                self.assertEqual([self.table.columnWidth(c) for c in range(14)], widths)
            self.assertGreaterEqual(self.table.columnWidth(1), 160)
        self.assertEqual(self.model.columnCount(), 14)

    def test_resize_and_splitter_fit_without_editing_document(self):
        rows = deepcopy(self.model.rows)
        self.navigate(9)
        initial = self.table.columnWidth(1)
        self.window.resize(1600, 780)
        APP.processEvents()
        self.assertGreater(self.table.columnWidth(1), initial)
        before = self.table.columnWidth(1)
        left, right = self.window.workspace.splitter.sizes()
        self.window.workspace.splitter.setSizes([left + 80, right - 80])
        APP.processEvents()
        self.assertLess(self.table.columnWidth(1), before)
        self.assertEqual(self.table.horizontalScrollBar().maximum(), 0)
        self.assertEqual(self.model.rows, rows)
        self.assertEqual(self.model.undo_stack.count(), 0)

    def test_visible_cell_copy_paste_skips_hidden_unit_and_is_undoable(self):
        self.window._select(4, 1)
        self.table.setFocus()
        selection = QItemSelection(self.model.index(4, 1), self.model.index(4, 4))
        self.table.selectionModel().select(selection, QItemSelectionModel.ClearAndSelect)
        self.window.copy_selection()
        self.assertEqual(QApplication.clipboard().text(), 'Tramo A\t1\t2\r\n')
        before = deepcopy(self.model.rows)
        self.window._select(5, 1)
        QApplication.clipboard().setText('Copiado\t3\t7')
        self.window.paste_selection()
        self.assertEqual(self.model.rows[5]['cells'][1:5], ['Copiado', 'm3', '3', '7'])
        self.assertEqual(self.model.undo_stack.count(), 1)
        self.model.undo_stack.undo()
        self.assertEqual(self.model.rows, before)

    def test_paste_cannot_overflow_visible_columns_into_hidden_total(self):
        self.window._select(4, 12)
        self.table.setFocus()
        before = deepcopy(self.model.rows)
        QApplication.clipboard().setText('1\t2')
        with patch.object(QMessageBox, 'warning') as warning:
            self.window.paste_selection()
        warning.assert_called_once()
        self.assertEqual(self.model.rows, before)

    def test_select_item_shows_only_its_complete_desagregado(self):
        self.navigate(2)
        self.assertEqual(self.visible(), [3, 4, 5])
        self.assertIn('EXCAVACIÓN', self.window.workspace.heading.text())
        self.assertIn('48.00', self.window.workspace.heading.text())
        self.navigate(6)
        self.assertEqual(self.visible(), [7])
        self.navigate(9)
        self.assertEqual(self.visible(), [10])
        self.assertEqual(self.table.horizontalHeader().mode, 'steel')

    def test_select_title_clears_planilla_without_losing_item_totals(self):
        self.navigate(0)
        self.assertEqual(self.visible(), [])
        self.assertIn('Selecciona una partida', self.window.workspace.heading.text())
        self.assertEqual(self.model.values[(2, 13)], 48)

    def test_development_numbers_restart_and_do_not_change_item_codes(self):
        codes = [r['cells'][0] for r in self.model.rows]
        for row in (2, 6, 9, 2):
            self.navigate(row)
            labels = [self.model.headerData(r, Qt.Vertical) for r in self.visible()]
            self.assertEqual(labels, [str(n) for n in range(1, len(labels) + 1)])
            self.assertEqual(self.model.headerData(row, Qt.Vertical), '')
        self.assertEqual([r['cells'][0] for r in self.model.rows], codes)
        self.assertEqual(self.model.undo_stack.count(), 0)

    def test_numbering_after_move_undo_and_fe_keeps_internal_titles(self):
        self.model.set_swelling([4, 5], dict(factor='1.2', note='FE'))
        self.navigate(2)
        self.window.move_to_parent(8)
        for undo in (False, True):
            if undo:
                self.model.undo_stack.undo()
            visible = self.visible()
            self.assertEqual([self.model.headerData(r, Qt.Vertical) for r in visible], ['1', '2', '3'])
            self.assertEqual(self.model.rows[visible[0]]['kind'], 'detail_group')
            self.assertEqual(self.table.rowHeight(visible[-1]), 56)

    def test_heading_is_single_line_with_live_total_and_long_title(self):
        self.navigate(2)
        heading = self.window.workspace.heading
        height = heading.height()
        self.model.setData(self.model.index(2, 1), 'Descripción muy extensa ' * 50 + '\nsegunda línea')
        APP.processEvents()
        self.assertFalse(heading.wordWrap())
        self.assertNotIn('\n', heading.text())
        self.assertTrue(heading.text().endswith(' · m3 · Total: 48.00'))
        self.assertEqual(heading.toolTip(), heading.text())
        self.assertEqual(heading.height(), height)
        self.assertEqual(self.tree.mapTo(self.window.workspace, QPoint()).y(),
                         self.table.mapTo(self.window.workspace, QPoint()).y())
        self.assertEqual(self.table.horizontalScrollBar().maximum(), 0)
        self.model.setData(self.model.index(4, 4), '4')
        self.assertTrue(heading.text().endswith('Total: 72.00'))

    def test_focusing_development_selects_first_visible_row_not_partida(self):
        self.navigate(2)
        self.table.setFocus()
        APP.processEvents()
        self.assertEqual(self.table.currentIndex().row(), 3)
        self.assertFalse(self.window.workspace.navigation_active)

    def test_switching_is_not_a_document_edit_or_recalculation(self):
        rows, values = deepcopy(self.model.rows), dict(self.model.values)
        with patch('metrado.grid.calculate', wraps=calculate) as calculation:
            for row in (2, 6, 9, 0, 2):
                self.navigate(row)
        calculation.assert_not_called()
        self.assertEqual(self.model.rows, rows)
        self.assertEqual(self.model.values, values)
        self.assertFalse(self.window._dirty)
        self.assertEqual(self.model.undo_stack.count(), 0)

    def test_edit_updates_tree_and_heading_without_reset(self):
        self.navigate(2)
        self.tree.collapse(self.outline.for_row(8))
        with patch.object(self.outline, 'rebuild', wraps=self.outline.rebuild) as rebuild:
            self.model.setData(self.model.index(4, 4), '4')
        rebuild.assert_not_called()
        self.assertEqual(self.outline.data(self.outline.for_row(2, 3)), '72.00')
        self.assertIn('72.00', self.window.workspace.heading.text())
        self.assertFalse(self.tree.isExpanded(self.outline.for_row(8)))
        self.model.setData(self.model.index(5, 4), '')
        self.assertEqual(self.outline.data(self.outline.for_row(2, 3)), 'Pendiente')

    def test_fe_summary_hidden_with_other_item_and_restored(self):
        self.model.set_swelling([4, 5], dict(factor='1.2', note='Test'))
        self.navigate(2)
        self.assertEqual(self.table.rowHeight(5), 56)
        self.assertEqual(self.outline.data(self.outline.for_row(2, 3)), '57.60')
        self.navigate(6)
        self.assertTrue(self.table.isRowHidden(5))
        self.navigate(2)
        self.assertEqual(self.table.rowHeight(5), 56)
        self.assertEqual(self.model.swelling_summary(4)[10], '57.60')

    def test_hidden_fe_does_not_leave_gap_before_other_development(self):
        self.navigate(2)
        self.model.set_swelling([4, 5], dict(factor='1.2', note='Test'))
        for owner, first in ((6, 7), (9, 10), (2, 3), (6, 7)):
            self.navigate(owner)
            self.assertEqual(self.table.rowViewportPosition(first), 0)
            self.assertEqual(self.table.verticalHeader().length(),
                             sum(self.table.rowHeight(r) for r in self.visible()))
        self.navigate(2)
        self.assertEqual(self.table.rowHeight(5), 56)
        self.assertEqual(self.model.swelling_summary(4)[10], '57.60')

    def test_first_detail_after_fe_has_no_gap_through_undo_redo(self):
        self.window._load('Primera fila', split_rows() + [
            new_row('item', description='VACÍA', unit='m3', level=0)])
        self.navigate(2)
        self.model.set_swelling([4, 5], dict(factor='1.2', note='Test'))
        self.navigate(11)
        self.assertEqual(self.visible(), [])
        self.assertEqual(self.table.verticalHeader().length(), 0)
        with patch.object(self.window.workspace, 'edit_description'):
            self.window.add_row('detail')
        for action in (None, self.model.undo_stack.undo, self.model.undo_stack.redo):
            if action:
                action()
            APP.processEvents()
            visible = self.visible()
            self.assertEqual(self.table.verticalHeader().length(), len(visible) * 28)
            if visible:
                self.assertEqual(visible, [12])
                self.assertEqual(self.table.rowViewportPosition(12), 0)
                self.assertEqual(self.model.headerData(12, Qt.Vertical), '1')
                self.assertEqual(self.table.rowHeight(12), 28)

    def test_visible_fe_still_preserves_its_minimum_height(self):
        self.navigate(2)
        self.model.set_swelling([4, 5], dict(factor='1.2', note='Test'))
        self.table.setRowHeight(5, 28)
        self.assertEqual(self.table.rowHeight(5), 56)
        self.navigate(6)
        self.table.sync_footers()
        APP.processEvents()
        self.assertEqual(self.table.rowViewportPosition(7), 0)
        self.navigate(2)
        self.assertEqual(self.table.rowHeight(5), 56)

    def test_navigation_commits_active_detail_editor(self):
        editor = self.editor(self.table, 4, 4)
        editor.selectAll()
        QTest.keyClicks(editor, '5')
        point = self.tree.visualRect(self.outline.for_row(6, 1)).center()
        QTest.mouseClick(self.tree.viewport(), Qt.LeftButton, pos=point)
        APP.processEvents()
        self.assertEqual(self.model.rows[4]['cells'][4], '5')
        self.assertEqual(self.visible(), [7])
        self.assertEqual(self.model.values[(2, 13)], 84)

    def test_click_same_item_after_detail_sets_correct_action_target(self):
        self.window._select(4)
        point = self.tree.visualRect(self.outline.for_row(2, 1)).center()
        QTest.mouseClick(self.tree.viewport(), Qt.LeftButton, pos=point)
        APP.processEvents()
        self.assertEqual(self.table.currentIndex().row(), 2)
        self.assertTrue(self.window.workspace.navigation_active)

    def test_titles_and_units_are_editable_from_tree(self):
        editor = self.editor(self.tree, 1, 1)
        editor.selectAll()
        QTest.keyClicks(editor, 'SUBTITULO EDITADO')
        QTest.keyClick(editor, Qt.Key_Return)
        APP.processEvents()
        self.assertEqual(self.model.rows[1]['cells'][1], 'SUBTITULO EDITADO')
        editor = self.editor(self.tree, 6, 2)
        self.assertIsInstance(editor, QComboBox)
        editor.setCurrentText('m3')
        QTest.keyClick(editor, Qt.Key_Return)
        APP.processEvents()
        self.assertEqual(self.model.rows[6]['cells'][2], 'm3')
        self.assertEqual(self.model.rows[7]['cells'][2], 'm3')
        self.assertEqual(self.outline.data(self.outline.for_row(6, 3)), 'Pendiente')

    def test_global_undo_reveals_partida_and_redo_updates_both_panels(self):
        self.window._select(4, 4)
        self.model.setData(self.model.index(4, 4), '4')
        self.navigate(6)
        QTest.keyClick(self.tree, Qt.Key_Z, Qt.ControlModifier)
        APP.processEvents()
        self.assertEqual(self.visible(), [3, 4, 5])
        self.assertEqual(self.table.currentIndex().row(), 4)
        self.assertEqual(self.outline.source_row(self.tree.currentIndex()), 2)
        self.assertEqual(self.outline.data(self.outline.for_row(2, 3)), '48.00')
        QTest.keyClick(self.table, Qt.Key_Y, Qt.ControlModifier)
        self.assertEqual(self.outline.data(self.outline.for_row(2, 3)), '72.00')

    def test_tree_text_editor_keeps_native_undo(self):
        self.model.setData(self.model.index(4, 4), '4')
        count = self.model.undo_stack.count()
        editor = self.editor(self.tree, 1, 1)
        original = editor.text()
        editor.selectAll()
        QTest.keyClicks(editor, 'ABC')
        QTest.keyClick(editor, Qt.Key_Z, Qt.ControlModifier)
        self.assertEqual(editor.text(), original)
        self.assertEqual(self.model.undo_stack.count(), count)
        QTest.keyClick(editor, Qt.Key_Escape)

    def test_tree_copy_paste_keeps_descendants_and_fe(self):
        self.model.set_swelling([4, 5], dict(factor='1.2', note='Test'))
        self.navigate(2)
        QTest.keyClick(self.tree, Qt.Key_C, Qt.ControlModifier)
        block = decode_rows(QApplication.clipboard().mimeData().data(ROW_MIME))
        self.assertEqual(len(block), 4)
        self.assertIn('volume_factor', block[-1])
        self.navigate(8)
        QTest.keyClick(self.tree, Qt.Key_V, Qt.ControlModifier)
        index = self.table.currentIndex().row()
        self.assertEqual(self.model.rows[index]['kind'], 'item')
        self.assertAlmostEqual(self.model.values[(index, 13)], 57.6)
        self.assertEqual(self.visible(), list(range(index + 1, index + 4)))

    def test_select_all_copy_from_table_cannot_include_hidden_partidas(self):
        self.window._select(4)
        self.table.setFocus()
        self.table.selectAll()
        self.window.copy_selection()
        block = decode_rows(QApplication.clipboard().mimeData().data(ROW_MIME))
        self.assertEqual(len(block), 3)
        self.assertEqual(block[0]['cells'][1], 'ZANJAS')

    def test_plain_paste_cannot_modify_following_hidden_partida(self):
        self.window._select(5, 1)
        self.table.setFocus()
        before = deepcopy(self.model.rows)
        QApplication.clipboard().setText('A\nB')
        with patch.object(QMessageBox, 'warning') as warning:
            self.window.paste_selection()
        warning.assert_called_once()
        self.assertEqual(self.model.rows, before)

    def test_tree_plain_paste_skips_measurements_and_undo_is_atomic(self):
        self.navigate(2)
        details = deepcopy(self.model.rows[3:6])
        QApplication.clipboard().setText('PRIMERA\nSEGUNDA')
        self.window.paste_selection()
        self.assertEqual(self.model.rows[2]['cells'][1], 'PRIMERA')
        self.assertEqual(self.model.rows[6]['cells'][1], 'SEGUNDA')
        self.assertEqual(self.model.rows[3:6], details)
        self.assertEqual(self.model.undo_stack.count(), 1)
        self.model.undo_stack.undo()
        self.assertEqual(self.model.rows[2]['cells'][1], 'EXCAVACIÓN')
        self.assertEqual(self.model.rows[6]['cells'][1], 'ÁREAS')

    def test_tree_invalid_plain_paste_rejects_whole_batch(self):
        self.navigate(2)
        before = deepcopy(self.model.rows)
        QApplication.clipboard().setText('PRIMERA\tm3\nSEGUNDA\tINVALIDA')
        with patch.object(QMessageBox, 'warning') as warning:
            self.window.paste_selection()
        warning.assert_called_once()
        self.assertEqual(self.model.rows, before)
        self.assertEqual(self.model.undo_stack.count(), 0)

    def test_tree_multiselection_copies_exact_roots_and_all_their_details(self):
        self.navigate(2)
        self.tree.selectionModel().select(self.outline.for_row(6), QItemSelectionModel.Select | QItemSelectionModel.Rows)
        self.window.copy_selection()
        block = decode_rows(QApplication.clipboard().mimeData().data(ROW_MIME))
        self.assertEqual([r['cells'][1] for r in block if r['kind'] == 'item'], ['EXCAVACIÓN', 'ÁREAS'])
        self.assertEqual(len(block), 6)

    def test_ctrl_click_tree_keeps_both_selected_partidas(self):
        self.navigate(2)
        point = self.tree.visualRect(self.outline.for_row(6, 1)).center()
        QTest.mouseClick(self.tree.viewport(), Qt.LeftButton, Qt.ControlModifier, point)
        APP.processEvents()
        selected = {self.outline.source_row(i) for i in self.tree.selectionModel().selectedRows()}
        self.assertEqual(selected, {2, 6})
        self.window.copy_selection()
        block = decode_rows(QApplication.clipboard().mimeData().data(ROW_MIME))
        self.assertEqual(len(block), 6)

    def test_tree_tab_and_alt_arrows_keep_hierarchy_actions(self):
        self.navigate(6)
        QTest.keyClick(self.tree, Qt.Key_Tab)
        APP.processEvents()
        row = self.table.currentIndex().row()
        self.assertEqual(self.model.outline.parents[row], 1)
        QTest.keyClick(self.tree, Qt.Key_Backtab, Qt.ShiftModifier)
        APP.processEvents()
        row = self.table.currentIndex().row()
        self.assertEqual(self.model.outline.parents[row], 0)
        QTest.keyClick(self.tree, Qt.Key_Up, Qt.AltModifier)
        APP.processEvents()
        row = self.table.currentIndex().row()
        self.assertEqual(self.model.rows[row]['cells'][1], 'ÁREAS')
        self.assertEqual(row, 1)

    def test_move_item_between_titles_preserves_selection_and_collapsed_branch(self):
        self.navigate(2)
        identity = self.model.rows[2]['id']
        self.window.move_to_parent(8)
        row = self.outline.by_id[identity]
        self.assertEqual(self.table.currentIndex().row(), row)
        self.assertEqual(self.outline.source_row(self.tree.currentIndex()), row)
        self.assertEqual(self.visible(), list(range(row + 1, row + 4)))
        self.model.undo_stack.undo()
        self.assertEqual(self.visible(), [3, 4, 5])

    def test_unrelated_collapsed_title_stays_collapsed_after_detail_insert(self):
        self.navigate(2)
        self.tree.collapse(self.outline.for_row(8))
        identity = self.model.rows[8]['id']
        with patch.object(self.table, 'edit'):
            self.window.add_row('detail')
        self.assertFalse(self.tree.isExpanded(self.outline.for_row(self.outline.by_id[identity])))

    def test_delete_visible_item_then_undo_restores_and_reveals_it(self):
        self.navigate(2)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            self.window.remove_row()
        self.assertNotIn('EXCAVACIÓN', [r['cells'][1] for r in self.model.rows])
        self.model.undo_stack.undo()
        self.assertEqual(self.visible(), [3, 4, 5])
        self.assertEqual(self.outline.data(self.outline.for_row(2, 3)), '48.00')

    def test_create_first_title_and_item_from_empty_document(self):
        self.window._load('', [])
        self.assertEqual(self.outline.rowCount(), 0)
        self.window.add_row('chapter')
        self.window._commit_editors()
        self.assertEqual(self.outline.rowCount(), 1)
        self.window.add_row('item')
        self.window._commit_editors()
        self.assertEqual(self.model.rows[1]['kind'], 'item')
        self.assertEqual(self.visible(), [])
        self.assertIn('Total: 0.00', self.window.workspace.heading.text())
        self.window.add_row('detail')
        self.window._commit_editors()
        self.assertEqual(self.visible(), [2])
        self.assertEqual(self.model.headerData(2, Qt.Vertical), '1')

    def test_widths_and_splitter_survive_switches_structure_and_undo(self):
        # Geometry changes refit the description; manual widths then survive
        # navigation/history until the next explicit resize.
        self.window.workspace.splitter.setSizes([350, 1100])
        APP.processEvents()
        self.table.setColumnWidth(1, 550)
        widths = [self.table.columnWidth(i) for i in range(14)]
        sizes = self.window.workspace.splitter.sizes()
        for row in (2, 6, 9):
            self.navigate(row)
        self.window.move_to_parent(0)
        self.model.undo_stack.undo()
        self.assertEqual([self.table.columnWidth(i) for i in range(14)], widths)
        self.assertEqual(self.window.workspace.splitter.sizes(), sizes)

    def test_save_commits_tree_editor_and_persists_all_hidden_items(self):
        editor = self.editor(self.tree, 2, 1)
        editor.selectAll()
        QTest.keyClicks(editor, 'NOMBRE GUARDADO')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'split.db'
            self.window._path = path
            self.assertTrue(self.window.save_project())
            title, rows, revision = read_database(path)
            self.assertEqual(len(rows), 11)
            self.assertEqual(rows[2]['cells'][1], 'NOMBRE GUARDADO')
            self.assertEqual(calculate(rows, engine), calculate(self.model.rows, engine))
            self.window._load(title, rows, path, revision)
            self.assertEqual(len(self.outline.node_rows), 6)


if __name__ == '__main__':
    unittest.main(verbosity=2)
