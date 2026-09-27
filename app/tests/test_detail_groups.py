"""Titles inside a work item's measured breakdown, including nested groups."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

import metrado._enlace as engine
from metrado.clipboard import ROW_MIME, decode_rows, encode_rows, insert_rows
from metrado.grid import SheetModel
from metrado.hierarchy import Outline, change_level, move_sibling, move_to, renumber
from metrado.organize import DestinationDialog
from metrado.sheet import calculate, new_row, read_project, steel_detail, validate_project, write_project
from metrado.window import PlantillaWindow

APP = QApplication.instance() or QApplication([])


def grouped_rows():
    rows = [new_row('chapter', '01', 'OBRAS DE CONCRETO', level=0),
            new_row('item', '01.01', 'CONCRETO 175 KG/CM2 EN UÑAS P/ VEREDAS', 'm3', level=1),
            new_row('detail_group', description='VEREDAS', unit='m3', level=2),
            new_row('detail', description='VEREDA INGRESO AV. HUALLAGA', unit='m3', level=3),
            new_row('detail', description='VEREDA INGRESO AV. HUALLAGA', unit='m3', level=3),
            new_row('detail_group', description='VEREDAS 2', unit='m3', level=2),
            new_row('detail_group', description='INGRESOS', unit='m3', level=3),
            new_row('detail', description='VEREDA INGRESO AV. SOL DE ORO', unit='m3', level=4),
            new_row('detail', description='VEREDA INGRESO AV. SOL DE ORO', unit='m3', level=4),
            new_row('item', '01.02', 'OTRA PARTIDA', 'm3', level=1),
            new_row('detail', description='Otra medición', unit='m3', level=2)]
    rows[3]['direct'] = '24'
    rows[4]['cells'][4:7] = ['37.73', '1', '0.06']
    rows[7]['cells'][4:7] = ['129.59', '1', '0.06']
    rows[8]['cells'][4:7] = ['141.39', '1', '0.06']
    rows[10]['cells'][4:7] = ['1', '1', '1']
    return rows


class GroupCalculationTests(unittest.TestCase):
    def test_image_quantities_sum_across_groups(self):
        rows = grouped_rows()
        values, errors = calculate(rows, engine)
        self.assertFalse(errors)
        self.assertAlmostEqual(values[(1, 13)], 42.5226)
        self.assertEqual(values[(9, 13)], 1)
        for index in (2, 5, 6):
            self.assertFalse(any(r == index for r, c in values))
        outline = Outline(rows, strict=True)
        self.assertEqual(outline.parents[7], 6)
        self.assertEqual(outline.owners[7], 1)
        self.assertEqual(outline.owners[6], 1)
        self.assertEqual(outline.ends[1], 9)

    def test_empty_groups_are_not_pending_measurements(self):
        model = SheetModel(engine, [new_row('item', unit='kg', level=0),
                                   new_row('detail_group', description='ACERO', unit='kg', level=1)])
        self.assertEqual(model.errors, {})
        self.assertEqual(model.values[(0, 13)], 0)
        self.assertEqual(model.summary_text, '1 partidas · 0 detalles · 0 detalles pendientes')
        self.assertEqual(model.selection_mode(1), 'steel')

    def test_invalid_detail_marks_item_despite_later_groups(self):
        rows = grouped_rows()
        rows[4]['cells'][4] = ''
        model = SheetModel(engine, rows)
        self.assertEqual(set(model.errors), {1, 4})
        self.assertNotIn((1, 13), model.values)
        self.assertEqual(model.values[(9, 13)], 1)
        model.setData(model.index(4, 4), '37.73')
        self.assertEqual(model.errors, {})
        self.assertAlmostEqual(model.values[(1, 13)], 42.5226)

    def test_edit_nested_detail_recalculates_only_its_item(self):
        class Counter:
            calls = 0
            def ask_sheet_quantity(self, *args):
                self.calls += 1
                return engine.ask_sheet_quantity(*args)
            def __getattr__(self, name):
                return getattr(engine, name)
        counter = Counter()
        model = SheetModel(counter, grouped_rows())
        counter.calls = 0
        model.setData(model.index(7, 4), '130')
        self.assertEqual(counter.calls, 4)
        self.assertEqual((model.values, model.errors), calculate(model.rows, engine))

    def test_unit_edit_updates_groups_and_all_nested_details(self):
        model = SheetModel(engine, grouped_rows())
        model.setData(model.index(1, 2), 'kg')
        for row in model.rows[2:9]:
            self.assertEqual(row['cells'][2], 'kg')
            self.assertEqual(row['direct'], '')
            if row['kind'] == 'detail_group':
                self.assertEqual(row['cells'][3:], [''] * 11)
            else:
                self.assertEqual(row['cells'][4:8], [''] * 4)
        self.assertEqual(model.rows[10]['cells'][2], 'm3')
        self.assertEqual((model.values, model.errors), calculate(model.rows, engine))

    def test_groups_have_description_only_and_no_item_number(self):
        model = SheetModel(engine, renumber(grouped_rows()))
        for r in (2, 5, 6):
            self.assertTrue(model.data(model.index(r, 1), Qt.FontRole).weight() >= 600)
            for c in range(14):
                self.assertEqual(model.editable(r, c), c == 1)
                if c != 1:
                    self.assertEqual(model.data(model.index(r, c)), '')
            self.assertFalse(model.setData(model.index(r, 3), '2'))
        self.assertEqual(model.rows[9]['cells'][0], '01.02')
        self.assertTrue(model.setData(model.index(6, 1), 'TRAMO A'))
        self.assertEqual(model.errors, {})

    def test_group_and_nested_steel_details_keep_exact_calculations(self):
        rows = [new_row('item', unit='kg', level=0),
                new_row('detail_group', description='COLUMNAS', unit='kg', level=1),
                new_row('detail_group', description='ESTRIBOS', unit='kg', level=2),
                steel_detail('Barra', 2, 10.85, .61, 1.15, '1"', 53)]
        rows[3]['level'] = 3
        model = SheetModel(engine, rows)
        self.assertAlmostEqual(model.values[(3, 8)], 1336.66)
        self.assertEqual(model.values[(0, 13)], model.values[(3, 12)])
        model.setData(model.index(3, 9), '1/2"')
        self.assertEqual((model.values, model.errors), calculate(rows, engine))
        block = decode_rows(encode_rows(model, [1]).data(ROW_MIME))
        pasted, pos = insert_rows(rows, 0, block)
        self.assertAlmostEqual(calculate(pasted, engine)[0][(0, 13)], 2 * model.values[(0, 13)])


class GroupStructureTests(unittest.TestCase):
    def test_move_group_with_descendants_between_items(self):
        rows = grouped_rows()
        moved, pos = move_to(rows, 5, 9)
        outline = Outline(moved, strict=True)
        values, errors = calculate(moved, engine)
        self.assertFalse(errors)
        self.assertEqual(moved[pos]['cells'][1], 'VEREDAS 2')
        self.assertEqual(moved[pos + 1]['cells'][1], 'INGRESOS')
        self.assertEqual(outline.owners[pos + 3], outline.owners[pos])
        self.assertAlmostEqual(values[(1, 13)], 26.2638)
        self.assertAlmostEqual(values[(outline.owners[pos], 13)], 17.2588)
        self.assertEqual(moved[outline.owners[pos]]['cells'][0], '01.02')

    def test_tab_details_and_groups_within_item_but_not_outside(self):
        rows = grouped_rows()
        nested, pos = change_level(rows, 5, True)
        self.assertEqual(Outline(nested).parents[pos], 2)
        restored, pos = change_level(nested, pos, False)
        self.assertEqual(restored, rows)
        detached, pos = change_level(rows, 7, False)
        self.assertEqual(Outline(detached).parents[pos], 5)
        restored, pos = change_level(detached, pos, True)
        self.assertEqual(Outline(restored).parents[pos], 6)
        values, errors = calculate(restored, engine)
        self.assertFalse(errors)
        self.assertAlmostEqual(values[(1, 13)], 42.5226)
        self.assertEqual(sorted(r['cells'][4] for r in restored if r['kind'] == 'detail'),
                         sorted(r['cells'][4] for r in rows if r['kind'] == 'detail'))
        with self.assertRaises(ValueError):
            change_level(rows, 2, False)
        with self.assertRaises(ValueError):
            move_to(rows, 2, 0)

    def test_reorder_groups_keeps_values_and_rejects_cycles_or_units(self):
        rows = grouped_rows()
        moved, pos = move_sibling(rows, 5, -1)
        self.assertEqual(moved[2]['cells'][1], 'VEREDAS 2')
        self.assertAlmostEqual(calculate(moved, engine)[0][(1, 13)], 42.5226)
        for destination in (6, 7, None):
            with self.assertRaises(ValueError):
                move_to(rows, 5, destination)
        rows[9]['cells'][2] = rows[10]['cells'][2] = 'm2'
        with self.assertRaises(ValueError):
            move_to(rows, 5, 9)

    def test_clipboard_nested_groups_and_mixed_measurement_roots(self):
        rows = grouped_rows()
        for selection in ([5], [3, 5], [1]):
            with self.subTest(selection=selection):
                model = SheetModel(engine, rows)
                block = decode_rows(encode_rows(model, selection).data(ROW_MIME))
                result, pos = insert_rows(rows, 9, block)
                Outline(result, strict=True)
                self.assertFalse(calculate(result, engine)[1])
                self.assertTrue(any(r['kind'] == 'detail_group' for r in result[pos:]))
        block = decode_rows(encode_rows(SheetModel(engine, rows), [5]).data(ROW_MIME))
        pasted, pos = insert_rows(rows, 2, block)
        self.assertEqual(Outline(pasted).parents[pos], 2)
        self.assertEqual(block[0]['level'], 0)

    def test_paste_item_on_nested_group_inserts_after_whole_item(self):
        rows = grouped_rows()
        block = decode_rows(encode_rows(SheetModel(engine, rows), [9]).data(ROW_MIME))
        result, pos = insert_rows(rows, 6, block)
        self.assertEqual(pos, 9)
        self.assertEqual(Outline(result).parents[pos], 0)

    def test_save_restore_groups_and_reject_malformed_groups(self):
        rows = grouped_rows()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'desagregado.json'
            write_project(path, 'Veredas', rows)
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['version'], 3)
            self.assertEqual(read_project(path), ('Veredas', rows))
        for index, field, value in ((2, 'level', 0), (2, 'direct', '10')):
            changed = deepcopy(rows)
            changed[index][field] = value
            with self.assertRaises(ValueError):
                validate_project({'version': 3, 'title': '', 'rows': changed})
        changed = deepcopy(rows)
        changed[2]['cells'][3] = '2'
        with self.assertRaises(ValueError):
            validate_project({'version': 3, 'title': '', 'rows': changed})


class GroupInteractionTests(unittest.TestCase):
    def setUp(self):
        self.window = PlantillaWindow(engine)
        self.window.model.replace(grouped_rows())
        self.window.show()
        self.window.activateWindow()
        APP.processEvents()

    def tearDown(self):
        self.window._dirty = False
        self.window.close()
        self.window.deleteLater()
        APP.processEvents()
        QApplication.clipboard().clear()

    def test_toolbar_title_subtitle_and_details(self):
        from metrado.chrome import ActionButton
        widths = [self.window.table.columnWidth(c) for c in range(14)]
        self.window._select(5)
        button = next(b for b in self.window.findChildren(ActionButton)
                      if b.accessibleName() == '+ Título de detalle')
        QTest.mouseClick(button, Qt.LeftButton)
        APP.processEvents()
        group = self.window.table.currentIndex().row()
        self.assertEqual(group, 9)
        self.assertEqual(self.window.model.outline.parents[group], 1)
        self.window.add_row('detail_subgroup')
        subgroup = self.window.table.currentIndex().row()
        self.assertEqual(self.window.model.outline.parents[subgroup], group)
        self.window.add_row('detail')
        detail = self.window.table.currentIndex().row()
        self.assertEqual(self.window.model.outline.parents[detail], subgroup)
        self.assertEqual(self.window.model.rows[detail]['cells'][2], 'm3')
        self.assertEqual([self.window.table.columnWidth(c) for c in range(14)], widths)

    def test_add_detail_from_nested_selection_keeps_its_group(self):
        self.window._select(7)
        self.window.add_row('detail')
        index = self.window.table.currentIndex().row()
        self.assertEqual(index, 8)
        self.assertEqual(self.window.model.outline.parents[index], 6)
        self.window._select(6)
        self.window.add_row('detail')
        index = self.window.table.currentIndex().row()
        self.assertEqual(self.window.model.outline.parents[index], 6)

    def test_add_item_from_nested_detail_does_not_split_original_item(self):
        self.window._select(7)
        self.window.add_row('item')
        index = self.window.table.currentIndex().row()
        self.assertEqual(index, 9)
        self.assertEqual(self.window.model.outline.parents[index], 0)
        self.assertAlmostEqual(self.window.model.values[(1, 13)], 42.5226)

    def test_keyboard_level_and_group_delete(self):
        self.window._select(5)
        QTest.keyClick(self.window.table, Qt.Key_Tab)
        APP.processEvents()
        index = self.window.table.currentIndex().row()
        self.assertEqual(self.window.model.outline.parents[index], 2)
        self.assertTrue(self.window.row_actions['outdent'].isEnabled())
        QTest.keyClick(self.window.table, Qt.Key_Backtab, Qt.ShiftModifier)
        APP.processEvents()
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            self.window.remove_row()
        self.assertAlmostEqual(self.window.model.values[(1, 13)], 26.2638)
        self.assertEqual(len(self.window.model.rows), 7)

    def test_copy_paste_group_with_keyboard_and_select_destination(self):
        self.window.table.selectRow(5)
        self.window.table.setFocus()
        QTest.keyClick(self.window.table, Qt.Key_C, Qt.ControlModifier)
        self.window._select(9)
        QTest.keyClick(self.window.table, Qt.Key_V, Qt.ControlModifier)
        APP.processEvents()
        index = self.window.table.currentIndex().row()
        self.assertEqual(self.window.model.rows[index]['kind'], 'detail_group')
        self.assertEqual(self.window.model.outline.owners[index], 9)
        self.assertAlmostEqual(self.window.model.values[(9, 13)], 17.2588)
        dialog = DestinationDialog(self.window.model.rows, index, self.window.model.outline, self.window)
        indexes = [i.data(0, Qt.UserRole) for i in dialog.entries]
        self.assertIn(2, indexes)
        self.assertIn(6, indexes)
        self.assertNotIn(index, indexes)
        dialog.deleteLater()

    def test_group_creation_requires_item_and_subgroup_requires_group(self):
        before = deepcopy(self.window.model.rows)
        self.window._select(0)
        self.window.add_row('detail_group')
        self.assertEqual(self.window.model.rows, before)
        self.window._select(1)
        self.window.add_row('detail_subgroup')
        self.assertEqual(self.window.model.rows, before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
