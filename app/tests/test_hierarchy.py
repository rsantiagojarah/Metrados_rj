"""Hierarchy, persistence and keyboard/clipboard integration with the real engine."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QItemSelection, QItemSelectionModel, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QMessageBox

import metrado._enlace as engine
from metrado.clipboard import ROW_MIME, decode_rows, encode_rows, insert_rows, parse_tsv, tsv
from metrado.grid import SheetModel
from metrado.hierarchy import Outline, change_level, materialize, move_sibling, move_to, renumber
from metrado.organize import DestinationDialog
from metrado.sheet import calculate, example_rows, new_row, read_project, validate_project, write_project
from metrado.window import PlantillaWindow

APP = QApplication.instance() or QApplication([])


def outline_rows():
    rows = [new_row('chapter', '01', 'OBRAS', level=0),
            new_row('chapter', '01.01', 'CIMENTACIÓN', level=1),
            new_row('item', '01.01.01', 'Excavación', 'm3', level=2),
            new_row('detail', description='Zapata', unit='m3', level=3),
            new_row('chapter', '01.02', 'ESTRUCTURAS', level=1),
            new_row('item', '01.02.01', 'Concreto', 'm3', level=2),
            new_row('detail', description='Columna', unit='m3', level=3),
            new_row('chapter', '02', 'EXTERIORES', level=0)]
    rows[3]['cells'][4:7] = ['2', '3', '4']
    rows[6]['cells'][4:7] = ['1', '2', '3']
    return rows


def totals_by_description(rows):
    values, errors = calculate(rows, engine)
    assert not errors, errors
    return {row['cells'][1]: values[(i, 13)] for i, row in enumerate(rows) if row['kind'] == 'item'}


class HierarchyTests(unittest.TestCase):
    def test_legacy_and_nested_outline(self):
        outline = Outline(outline_rows(), strict=True)
        self.assertEqual(outline.parents, [None, 0, 1, 2, 0, 4, 5, None])
        self.assertEqual(outline.ends, [7, 4, 4, 4, 7, 7, 7, 8])
        old = Outline(example_rows(), strict=True)
        self.assertEqual(old.parents[4], 3)
        self.assertEqual(old.ends[0], 5)

    def test_move_subtitle_preserves_subtree_and_quantities(self):
        rows = outline_rows()
        before = deepcopy(rows)
        moved, selected = move_sibling(rows, 1, 1)
        self.assertEqual(selected, 4)
        self.assertEqual([r['cells'][1] for r in moved[4:7]], ['CIMENTACIÓN', 'Excavación', 'Zapata'])
        self.assertEqual(totals_by_description(moved), totals_by_description(rows))
        restored, selected = move_sibling(moved, selected, -1)
        self.assertEqual(restored, rows)
        self.assertEqual(rows, before)

    def test_indent_outdent_preserves_other_children(self):
        rows = outline_rows()
        nested, position = change_level(rows, 4, True)
        self.assertEqual(nested[position]['level'], 2)
        self.assertEqual(nested[position + 2]['level'], 4)
        restored, _ = change_level(nested, position, False)
        self.assertEqual(restored, rows)
        # Moving an early child out must not adopt its remaining siblings.
        promoted, position = change_level(rows, 1, False)
        self.assertEqual(position, 4)
        outline = Outline(promoted, strict=True)
        self.assertEqual(outline.parents[1], 0)
        self.assertIsNone(outline.parents[position])

    def test_move_item_to_title_and_subtitle(self):
        rows = outline_rows()
        moved, position = move_to(rows, 2, 7)
        outline = Outline(moved, strict=True)
        self.assertEqual(moved[outline.parents[position]]['cells'][1], 'EXTERIORES')
        self.assertEqual(moved[position + 1]['cells'][1], 'Zapata')
        destination = next(i for i, r in enumerate(moved) if r['cells'][1] == 'ESTRUCTURAS')
        moved, position = move_to(moved, position, destination)
        self.assertEqual(Outline(moved).parents[position], destination)
        self.assertEqual(totals_by_description(moved), totals_by_description(rows))

    def test_move_details_between_compatible_items_updates_both_totals(self):
        rows = outline_rows()
        moved, position = move_to(rows, 3, 5)
        self.assertEqual(totals_by_description(moved), {'Excavación': 0, 'Concreto': 30})
        self.assertEqual(moved[position]['cells'][1], 'Zapata')
        rows[5]['cells'][2] = rows[6]['cells'][2] = 'm2'
        with self.assertRaises(ValueError):
            move_to(rows, 3, 5)

    def test_invalid_moves_are_non_mutating(self):
        rows = outline_rows()
        before = deepcopy(rows)
        for operation, index, argument in ((move_to, 0, 2), (move_to, 3, None),
                                           (move_sibling, 0, -1), (change_level, 3, True),
                                           (change_level, 0, False)):
            with self.assertRaises(ValueError):
                operation(rows, index, argument)
        self.assertEqual(rows, before)

    def test_save_nested_project_and_open_legacy(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'obra.json'
            rows = outline_rows()
            write_project(path, 'Obra', rows)
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['version'], 2)
            self.assertEqual(read_project(path), ('Obra', rows))
            write_project(path, 'Anterior', example_rows())
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['version'], 1)
            restored = read_project(path)[1]
            self.assertEqual(restored, example_rows())
            self.assertEqual(totals_by_description(materialize(restored)), totals_by_description(restored))

    def test_malformed_levels_and_parentage_are_rejected(self):
        for index, level in ((0, -1), (1, 5), (2, True), (3, 1), (4, 33)):
            rows = outline_rows()
            rows[index]['level'] = level
            with self.assertRaises(ValueError):
                validate_project({'version': 2, 'title': '', 'rows': rows})

    def test_copy_subtree_is_lossless_and_has_fresh_codes(self):
        model = SheetModel(engine, outline_rows())
        mime = encode_rows(model, [1, 2, 3])
        block = decode_rows(mime.data(ROW_MIME))
        self.assertEqual(len(block), 3)  # overlapping selections don't duplicate descendants
        rows, position = insert_rows(model.rows, 7, block)
        self.assertEqual(rows[position]['cells'][1], 'CIMENTACIÓN')
        self.assertEqual(rows[position + 2]['cells'][4:7], ['2', '3', '4'])
        self.assertEqual(calculate(rows, engine)[0][(position + 1, 13)], 24)
        codes = [r['cells'][0] for r in rows if r['kind'] != 'detail']
        self.assertEqual(len(codes), len(set(codes)))
        rows[position + 2]['cells'][4] = '99'
        self.assertEqual(model.rows[3]['cells'][4], '2')

    def test_copy_steel_and_details_roundtrip(self):
        model = SheetModel(engine, example_rows())
        for selected in ([14], [15, 16]):
            mime = encode_rows(model, selected)
            block = decode_rows(mime.data(ROW_MIME))
            rows, position = insert_rows(model.rows, 14, block)
            Outline(rows, strict=True)
            self.assertEqual(rows[position]['cells'][7], model.rows[selected[0]]['cells'][7])
            if selected == [14]:
                self.assertAlmostEqual(calculate(rows, engine)[0][(position, 13)], model.values[(14, 13)])
            else:
                self.assertAlmostEqual(calculate(rows, engine)[0][(position, 12)], model.values[(15, 12)])
                with self.assertRaises(ValueError):
                    insert_rows(model.rows, 3, block)

    def test_clipboard_rejects_malformed_data_and_tsv(self):
        for raw in (b'null', b'{}', b'{bad', b'{"version":1,"rows":[null]}',
                    b'{"version":1,"rows":[{"kind":"item","level":0,"cells":[]}]}'):
            with self.assertRaises(ValueError):
                decode_rows(raw)
        with self.assertRaises(ValueError):
            parse_tsv('1\t2\n3')
        matrix = [['Texto con\nsalto', '3/8"', '2,5'], ['A\tB', '1', '2']]
        self.assertEqual(parse_tsv(tsv(matrix)), matrix)

    def test_cell_paste_atomic_and_recalculates(self):
        model = SheetModel(engine, outline_rows())
        self.assertTrue(model.paste_cells(3, 4, [['5', '6', '7']]))
        self.assertEqual(model.values[(2, 13)], 210)
        before = deepcopy(model.rows)
        with self.assertRaises(ValueError):
            model.paste_cells(2, 1, [['Changed name', 'INVALID UNIT']])
        self.assertEqual(model.rows, before)
        with self.assertRaises(ValueError):
            model.paste_cells(7, 1, [['a'], ['b']])
        self.assertEqual(model.rows, before)

    def test_batch_steel_description_does_not_override_pasted_bar_count(self):
        model = SheetModel(engine, example_rows())
        model.setData(model.index(15, 7), '60')
        source = [str(model.data(model.index(15, c), Qt.EditRole) or '') for c in range(1, 10)]
        source[0] = 'Nuevo texto 53 Ø1"'
        model.paste_cells(15, 1, [source])
        self.assertEqual(model.data(model.index(15, 7)), '60')
        self.assertEqual(model.rows[15]['cells'][10], '60')


class InteractionTests(unittest.TestCase):
    def setUp(self):
        self.window = PlantillaWindow(engine)
        self.window.model.replace(outline_rows())
        self.window.show()
        self.window.activateWindow()
        APP.processEvents()
        self.window._select(0)

    def tearDown(self):
        self.window._dirty = False
        self.window.close()
        self.window.deleteLater()
        APP.processEvents()
        QApplication.clipboard().clear()

    def test_tab_shift_tab_and_alt_arrows(self):
        widths = [self.window.table.columnWidth(c) for c in range(14)]
        self.window._select(4)
        QTest.keyClick(self.window.table, Qt.Key_Tab)
        APP.processEvents()
        index = self.window.table.currentIndex().row()
        self.assertEqual(self.window.model.rows[index]['level'], 2)
        QTest.keyClick(self.window.table, Qt.Key_Backtab, Qt.ShiftModifier)
        APP.processEvents()
        self.assertEqual(self.window.model.rows[self.window.table.currentIndex().row()]['level'], 1)
        QTest.keyClick(self.window.table, Qt.Key_Up, Qt.AltModifier)
        APP.processEvents()
        self.assertEqual(self.window.model.rows[1]['cells'][1], 'ESTRUCTURAS')
        self.assertEqual([self.window.table.columnWidth(c) for c in range(14)], widths)

    def test_tab_in_numeric_column_navigates(self):
        self.window._select(3, 4)
        before = deepcopy(self.window.model.rows)
        QTest.keyClick(self.window.table, Qt.Key_Tab)
        self.assertEqual(self.window.table.currentIndex().column(), 5)
        self.assertEqual(self.window.model.rows, before)

    def test_new_subtitles_and_items_insert_in_selected_container(self):
        self.window._select(1)
        self.window.add_row('subtitle')
        i = self.window.table.currentIndex().row()
        self.assertEqual(self.window.model.rows[i]['level'], 2)
        self.window.add_row('item')
        j = self.window.table.currentIndex().row()
        self.assertEqual(self.window.model.outline.parents[j], i)
        self.window.add_row('detail')
        k = self.window.table.currentIndex().row()
        self.assertEqual(self.window.model.outline.parents[k], j)
        self.window._select(0)
        self.window.add_row('item')
        j = self.window.table.currentIndex().row()
        self.assertEqual(self.window.model.outline.parents[j], 0)

    def test_remove_title_includes_nested_descendants(self):
        self.window._select(0)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            self.window.remove_row()
        self.assertEqual(len(self.window.model.rows), 1)
        self.assertEqual(self.window.model.rows[0]['cells'][1], 'EXTERIORES')

    def test_ctrl_c_v_cells_and_native_editor_text(self):
        self.window._select(3, 4)
        QTest.keyClick(self.window.table, Qt.Key_C, Qt.ControlModifier)
        self.window._select(6, 4)
        QTest.keyClick(self.window.table, Qt.Key_V, Qt.ControlModifier)
        self.assertEqual(self.window.model.rows[6]['cells'][4], '2')
        self.assertEqual(self.window.model.values[(5, 13)], 12)
        QTest.keyClick(self.window.table, Qt.Key_F2)
        APP.processEvents()
        editor = self.window.table.findChild(QLineEdit)
        editor.selectAll()
        QApplication.clipboard().setText('9')
        QTest.keyClick(editor, Qt.Key_V, Qt.ControlModifier)
        QTest.keyClick(editor, Qt.Key_Return)
        APP.processEvents()
        self.assertEqual(self.window.model.rows[6]['cells'][4], '9')

    def test_ctrl_c_v_whole_rows_copies_descendants(self):
        # Titles now live in the left tree, not in the visible detail grid.
        self.window.navigator.setCurrentIndex(self.window.workspace.outline.for_row(1, 1))
        self.window.navigator.setFocus()
        QTest.keyClick(self.window.navigator, Qt.Key_C, Qt.ControlModifier)
        self.assertTrue(QApplication.clipboard().mimeData().hasFormat(ROW_MIME))
        self.window._select(7)
        QTest.keyClick(self.window.navigator, Qt.Key_V, Qt.ControlModifier)
        self.assertEqual(len(self.window.model.rows), 11)
        self.assertEqual(self.window.model.rows[8]['cells'][1], 'CIMENTACIÓN')
        self.assertEqual(self.window.model.outline.parents[8], 7)

    def test_ctrl_shift_c_copies_block_from_description(self):
        self.window._select(1)
        QTest.keyClick(self.window.navigator, Qt.Key_C, Qt.ControlModifier | Qt.ShiftModifier)
        self.assertEqual(len(decode_rows(QApplication.clipboard().mimeData().data(ROW_MIME))), 3)

    def test_rectangle_copy_paste(self):
        self.window._select(3, 4)
        selection = QItemSelection(self.window.model.index(3, 4), self.window.model.index(3, 6))
        self.window.table.selectionModel().select(selection, QItemSelectionModel.ClearAndSelect)
        self.window.copy_selection()
        self.window._select(6, 4)
        self.window.paste_selection()
        self.assertEqual(self.window.model.rows[6]['cells'][4:7], ['2', '3', '4'])

    def test_destination_picker_excludes_descendants_and_filters(self):
        dialog = DestinationDialog(self.window.model.rows, 1, self.window.model.outline, self.window)
        indexes = [item.data(0, Qt.UserRole) for item in dialog.entries]
        self.assertNotIn(1, indexes)
        self.assertNotIn(2, indexes)
        self.assertIn(4, indexes)
        dialog._filter('exteriores')
        target = next(item for item in dialog.entries if item.data(0, Qt.UserRole) == 7)
        self.assertFalse(target.isHidden())
        dialog.tree.setCurrentItem(target)
        self.assertEqual(dialog.destination, 7)
        self.assertTrue(dialog.accept_button.isEnabled())
        dialog.deleteLater()

    def test_move_keeps_manual_column_widths(self):
        self.window.table.setColumnWidth(1, 550)
        self.window._select(1)
        self.window.move_to_parent(7)
        self.assertEqual(self.window.table.columnWidth(1), 550)
        self.assertEqual(totals_by_description(self.window.model.rows), totals_by_description(outline_rows()))

    def test_screenshot_subtitle_outdent_updates_items_in_order(self):
        rows = outline_rows()[:4]
        rows.extend([new_row('item', '01.01.02', 'Segunda partida', level=2),
                     new_row('chapter', '01.01.03', 'Nuevo subtítulo', level=2)])
        self.window.model.replace(rows)
        self.window._select(5)
        QTest.keyClick(self.window.table, Qt.Key_Backtab, Qt.ShiftModifier)
        APP.processEvents()
        self.assertEqual([r['cells'][0] for r in self.window.model.rows],
                         ['01', '01.01', '01.01.01', '', '01.01.02', '01.02'])
        QTest.keyClick(self.window.table, Qt.Key_Up, Qt.AltModifier)
        APP.processEvents()
        self.assertEqual([r['cells'][0] for r in self.window.model.rows],
                         ['01', '01.01', '01.02', '01.02.01', '', '01.02.02'])
        self.assertEqual(self.window.model.rows[1]['cells'][1], 'Nuevo subtítulo')

    def test_insert_and_delete_renumber_following_rows(self):
        self.window._select(0)
        self.window.add_row('chapter')
        self.assertEqual(self.window.model.rows[7]['cells'][0], '02')
        self.assertEqual(self.window.model.rows[8]['cells'][0], '03')
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            self.window.remove_row()
        self.assertEqual(self.window.model.rows[-1]['cells'][0], '02')
        self.window._select(1)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            self.window.remove_row()
        self.assertEqual([r['cells'][0] for r in self.window.model.rows],
                         ['01', '01.01', '01.01.01', '', '02'])


class NumberingTests(unittest.TestCase):
    def codes(self, rows):
        return [r['cells'][0] for r in rows]

    def test_reorder_titles_renumbers_every_descendant(self):
        rows = outline_rows()
        moved, _ = move_sibling(rows, 7, -1)
        self.assertEqual(self.codes(moved), ['01', '02', '02.01', '02.01.01', '', '02.02', '02.02.01', ''])
        self.assertEqual(moved[0]['cells'][1], 'EXTERIORES')
        self.assertEqual(totals_by_description(rows), totals_by_description(moved))

    def test_indent_outdent_and_move_to_update_prefixes(self):
        rows = outline_rows()
        nested, selected = change_level(rows, 4, True)
        self.assertEqual(nested[selected]['cells'][0], '01.01.02')
        self.assertEqual(nested[selected + 1]['cells'][0], '01.01.02.01')
        restored, _ = change_level(nested, selected, False)
        self.assertEqual(restored, rows)
        moved, selected = move_to(rows, 1, 7)
        self.assertEqual(self.codes(moved), ['01', '01.01', '01.01.01', '', '02', '02.01', '02.01.01', ''])
        self.assertEqual(moved[selected]['cells'][1], 'CIMENTACIÓN')

    def test_paste_block_renumbers_following_siblings_and_persists(self):
        rows = outline_rows()
        block = decode_rows(encode_rows(SheetModel(engine, rows), [2]).data(ROW_MIME))
        pasted, _ = insert_rows(rows, 0, block)
        self.assertEqual(self.codes(pasted), ['01', '01.01', '01.01.01', '', '01.02', '01.02.01', '', '01.03', '', '02'])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'numerado.json'
            write_project(path, 'Numeración', pasted)
            self.assertEqual(self.codes(read_project(path)[1]), self.codes(pasted))

    def test_renumber_is_pure_and_ignores_detail_rows(self):
        rows = outline_rows()
        rows[0]['cells'][0] = '99'
        rows[2]['cells'][0] = 'MANUAL'
        before = deepcopy(rows)
        numbered = renumber(rows)
        self.assertEqual(self.codes(numbered), ['01', '01.01', '01.01.01', '', '01.02', '01.02.01', '', '02'])
        self.assertEqual(rows, before)
        self.assertEqual(renumber(numbered), numbered)
        self.assertEqual(renumber([]), [])
        self.assertEqual(calculate(numbered, engine), calculate(rows, engine))


if __name__ == '__main__':
    unittest.main(verbosity=2)
