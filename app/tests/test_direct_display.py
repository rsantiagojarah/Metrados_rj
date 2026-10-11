"""Individual direct measurements are visible without becoming dimensions."""
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import Qt
from openpyxl import load_workbook
import metrado._enlace as engine
from metrado.grid import SheetModel
from metrado.sheet import new_row
from metrado.excel_export import export_workbook


class DirectDisplayTests(unittest.TestCase):
    def model(self, unit):
        return SheetModel(engine, [new_row('item', '01', 'Prueba', unit, 0),
                                  new_row('detail', unit=unit, level=1)])

    def test_direct_label_value_readonly_factors_and_undo(self):
        for unit, label, result in [('m2', 'ÁREA', 9), ('m3', 'VOLUMEN', 10)]:
            with self.subTest(unit=unit):
                model = self.model(unit)
                model.setData(model.index(1, 3), '4')
                model.set_direct(1, '8,6275')
                self.assertEqual(model.data(model.index(1, 4)), label)
                self.assertEqual(model.data(model.index(1, 5)), '8,6275')
                self.assertFalse(model.flags(model.index(1, 5)) & Qt.ItemIsEditable)
                self.assertFalse(model.setData(model.index(1, 5), '20'))
                self.assertAlmostEqual(model.values[(1, result)], 34.51)
                model.setData(model.index(1, 7), '2')
                self.assertEqual(model.rows[1]['direct'], '8,6275')
                self.assertAlmostEqual(model.values[(1, result)], 69.02)
                model.set_direct(1, '10')
                self.assertEqual(model.data(model.index(1, 5)), '10')
                model.undo_stack.undo()
                self.assertEqual(model.data(model.index(1, 5)), '8,6275')
                model.set_direct(1, '')
                self.assertTrue(model.flags(model.index(1, 5)) & Qt.ItemIsEditable)
                self.assertEqual(model.data(model.index(1, 5)), '')

    def test_volume_from_area_stays_in_area_column(self):
        model = self.model('m3')
        model.set_direct(1, '10')
        self.assertTrue(model.setData(model.index(1, 9), '25'))
        self.assertTrue(model.setData(model.index(1, 5), '0,2'))
        self.assertEqual(model.rows[1]['direct'], '')
        self.assertEqual(model.data(model.index(1, 9)), '25.00')
        self.assertEqual(model.data(model.index(1, 5)), '0,2')
        self.assertEqual(model.values[(1, 10)], 5)

    def test_direct_length_uses_length_label_and_keeps_its_result_column(self):
        model = self.model('m')
        model.setData(model.index(1, 3), '4')
        model.set_direct(1, '8,6275')
        self.assertEqual(model.data(model.index(1, 4)), 'LONGITUD')
        self.assertAlmostEqual(model.values[(1, 8)], 34.51)

    def test_excel_matches_label_value_and_result(self):
        with tempfile.TemporaryDirectory() as folder:
            for unit, label, result in [('m2', 'ÁREA', 'J13'), ('m3', 'VOLUMEN', 'K13')]:
                model = self.model(unit)
                model.setData(model.index(1, 3), '4')
                model.set_direct(1, '8,6275')
                path = Path(folder) / 'direct.xlsx'
                export_workbook(path, 'Directo', model.rows, engine)
                book = load_workbook(path)
                cached = load_workbook(path, data_only=True)
                try:
                    sheet = book['Desarrollo']
                    self.assertEqual(sheet['E13'].value, label)
                    self.assertEqual(sheet['F13'].value, 8.6275)
                    self.assertIn('D13*H13*F13', sheet[result].value)
                    self.assertAlmostEqual(cached['Desarrollo'][result].value, 34.51)
                finally:
                    book.close()
                    cached.close()

    def test_excel_uses_length_label_for_direct_linear_measurement(self):
        model = self.model('m')
        model.setData(model.index(1, 3), '4')
        model.set_direct(1, '8,6275')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'longitud.xlsx'
            export_workbook(path, 'Longitud', model.rows, engine)
            book = load_workbook(path)
            try:
                sheet = book['Desarrollo']
                self.assertEqual(sheet['F13'].value, 'LONGITUD')
                self.assertEqual(sheet['E13'].value, 8.6275)
                self.assertIn('D13*H13*E13', sheet['I13'].value)
            finally:
                book.close()
