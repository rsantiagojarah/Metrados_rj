"""Atomic multi-row indent/outdent in both panels, with real keyboard events."""
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QCoreApplication, QEvent, QItemSelectionModel, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
import metrado._enlace as engine
from metrado.hierarchy import Outline, change_levels, renumber
from metrado.sheet import new_row
from metrado.steel_store import CatalogStore
from metrado.window import PlantillaWindow

APP = QApplication.instance() or QApplication([])


def rows_fixture():
    spec = [('chapter', 'Principal', 0), ('chapter', 'Grupo', 1),
            ('item', 'Partida A', 1), ('detail_group', 'Zona', 2),
            ('detail', 'A', 2), ('detail', 'B', 2), ('detail', 'C', 2),
            ('item', 'Partida B', 1), ('detail', 'D', 2),
            ('item', 'Partida C', 1), ('detail', 'E', 2)]
    rows = [new_row(kind, description=name, unit='m3', level=level) for kind, name, level in spec]
    for row in rows:
        if row['kind'] == 'detail':
            row['direct'] = '10'
    return renumber(rows)


class BulkLevelTests(unittest.TestCase):
    def test_items_indent_as_siblings_not_nested_and_renumber(self):
        rows = rows_fixture()
        result = change_levels(rows, [2, 7, 9], True)
        outline = Outline(result, strict=True)
        self.assertEqual([outline.parents[i] for i in (2, 7, 9)], [1, 1, 1])
        self.assertEqual([result[i]['cells'][0] for i in (2, 7, 9)], ['01.01.01', '01.01.02', '01.01.03'])
        self.assertEqual(change_levels(result, [2, 7, 9], False), rows)

    def test_details_outdent_in_order_without_adopting_unselected(self):
        rows = change_levels(rows_fixture(), [4, 5, 6], True)
        result = change_levels(rows, [4, 6], False)
        self.assertEqual([r['cells'][1] for r in result[3:7]], ['Zona', 'B', 'A', 'C'])
        self.assertEqual([r['level'] for r in result[3:7]], [2, 3, 2, 2])

    def test_ancestor_and_child_only_move_once(self):
        result = change_levels(rows_fixture(), [2, 3, 4, 5, 7], True)
        self.assertEqual([r['level'] for r in result[2:9]], [2, 3, 3, 3, 3, 2, 3])

    def test_selected_titles_stay_siblings(self):
        rows = [new_row('chapter', description=str(i), level=0) for i in range(4)]
        result = change_levels(rows, [1, 2, 3], True)
        self.assertEqual(Outline(result, strict=True).parents, [None, 0, 0, 0])

    def test_invalid_selection_does_not_mutate_input(self):
        rows = rows_fixture()
        before = deepcopy(rows)
        for selected, inward in [([4, 6], True), ([3, 4], False), ([0, 2], False), ([1, 2], True), ([], True)]:
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                change_levels(rows, selected, inward)
            self.assertEqual(rows, before)

    def test_separate_parents_and_shared_end_boundaries(self):
        specs = [('chapter', 'P', 0), ('chapter', 'Y', 1), ('chapter', 'Q', 1), ('chapter', 'X', 2)]
        rows = [new_row(k, description=n, level=l) for k, n, l in specs]
        result = change_levels(rows, [1, 3], False)
        self.assertEqual([r['cells'][1] for r in result], ['P', 'Q', 'X', 'Y'])
        self.assertEqual([r['level'] for r in result], [0, 1, 1, 0])


class BulkLevelUiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.window = PlantillaWindow(engine, CatalogStore(Path(self.temp.name) / 'catalog.db'))
        self.window._load('Niveles', rows_fixture())
        self.window.show()
        self.window.activateWindow()
        APP.processEvents()

    def tearDown(self):
        with patch.object(self.window, '_can_discard', return_value=True):
            self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        self.temp.cleanup()

    def select(self, indexes, tree=False, current_last=False):
        window = self.window
        view = window.navigator if tree else window.table
        window.workspace.navigation_active = tree
        window._select(indexes[-1] if current_last else indexes[0], 1)
        view.setFocus()
        for row in indexes:
            index = window.workspace.outline.for_row(row, 1) if tree else window.model.index(row, 1)
            view.selectionModel().select(index, QItemSelectionModel.Select | (QItemSelectionModel.Rows if tree else QItemSelectionModel.NoUpdate))
        APP.processEvents()

    def test_buttons_details_preserve_selection_and_one_undo(self):
        self.select([4, 5, 6], current_last=True)
        before = deepcopy(self.window.model.rows)
        self.assertTrue(self.window.row_actions['indent'].isEnabled())
        self.window.row_actions['indent'].trigger()
        self.assertEqual([self.window.model.rows[i]['level'] for i in (4, 5, 6)], [3, 3, 3])
        self.assertEqual(self.window._selected_rows()[0], {4, 5, 6})
        self.assertEqual(self.window.model.undo_stack.count(), 1)
        self.window.model.undo_stack.undo()
        self.assertEqual(self.window.model.rows, before)
        self.window.model.undo_stack.redo()
        self.assertEqual([self.window.model.rows[i]['level'] for i in (4, 5, 6)], [3, 3, 3])

    def test_tab_and_shift_tab_move_whole_selection(self):
        self.select([4, 5, 6])
        before = deepcopy(self.window.model.rows)
        QTest.keyClick(self.window.table, Qt.Key_Tab)
        self.assertEqual(self.window._selected_rows()[0], {4, 5, 6})
        QTest.keyClick(self.window.table, Qt.Key_Backtab, Qt.ShiftModifier)
        self.assertEqual(self.window.model.rows, before)
        self.assertEqual(self.window._selected_rows()[0], {4, 5, 6})

    def test_tree_buttons_items_keep_totals_and_children(self):
        self.select([2, 7, 9], tree=True, current_last=True)
        before = deepcopy(self.window.model.rows)
        self.assertTrue(self.window.row_actions['indent'].isEnabled())
        self.window.row_actions['indent'].trigger()
        self.assertEqual(self.window._selected_rows(), ({2, 7, 9}, True))
        self.assertEqual([self.window.model.values[(i, 13)] for i in (2, 7, 9)], [30, 10, 10])
        self.window.row_actions['outdent'].trigger()
        self.assertEqual(self.window.model.rows, before)

    def test_tree_alt_arrows_move_all(self):
        self.select([2, 7, 9], tree=True)
        QTest.keyClick(self.window.navigator, Qt.Key_Right, Qt.AltModifier)
        self.assertEqual([self.window.model.rows[i]['level'] for i in (2, 7, 9)], [2, 2, 2])
        QTest.keyClick(self.window.navigator, Qt.Key_Left, Qt.AltModifier)
        self.assertEqual([self.window.model.rows[i]['level'] for i in (2, 7, 9)], [1, 1, 1])

    def test_references_and_ids_survive_bulk_movement(self):
        model = self.window.model
        model.set_reference(8, model.rows[2]['id'])
        identities = [row['id'] for row in model.rows]
        self.select([2, 7, 9], tree=True)
        self.window.indent_row(True)
        self.assertEqual([row['id'] for row in model.rows], identities)
        self.assertEqual(model.values[(7, 13)], 30)
        self.assertEqual(model.rows[8]['reference']['source'], model.rows[2]['id'])
        self.window.indent_row(False)
        self.assertEqual(model.values[(7, 13)], 30)

    def test_invalid_tab_is_atomic_and_explains(self):
        self.select([4, 6])
        before = deepcopy(self.window.model.rows)
        self.assertFalse(self.window.row_actions['indent'].isEnabled())
        QTest.keyClick(self.window.table, Qt.Key_Tab)
        self.assertEqual(self.window.model.rows, before)
        self.assertEqual(self.window.model.undo_stack.count(), 0)
        self.assertIn('No se cambió', self.window.statusBar().currentMessage())
