import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import Qt
from openpyxl import load_workbook
import metrado._enlace as engine
from metrado.database import read_database, write_database
from metrado.excel_export import export_workbook
from metrado.grid import SheetModel
from metrado.sheet import calculate, new_row


class UnitDimensionsTests(unittest.TestCase):
    def test_legacy_and_dimensioned_units(self):
        rows = [new_row('item', '01', 'Ladrillos', 'und', 0),
                new_row('detail', description='Anterior', unit='und', level=1),
                new_row('detail', description='Paño', unit='und', level=1)]
        rows[1]['cells'][3], rows[1]['cells'][7] = '2', '3'
        rows[2]['cells'][4:7] = ['3.9', '3.63', '9']
        values, errors = calculate(rows, engine)
        self.assertFalse(errors)
        self.assertEqual(values[(1, 12)], 6)
        self.assertAlmostEqual(values[(2, 12)], 127.413)
        rows[2]['cells'][6] = ''
        self.assertIn(2, calculate(rows, engine)[1])

    def test_edit_save_and_export_dimensions(self):
        rows = [new_row('item', '01', 'Ladrillos', 'und', 0),
                new_row('detail', description='Paño', unit='und', level=1)]
        model = SheetModel(engine, rows)
        for column, value in ((4, '3.9'), (5, '3.63'), (6, '9')):
            self.assertTrue(model.flags(model.index(1, column)) & Qt.ItemIsEditable)
            self.assertTrue(model.setData(model.index(1, column), value))
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / 'losa.db'
            write_database(database, 'Losa', model.rows)
            restored = read_database(database)[1]
            self.assertAlmostEqual(calculate(restored, engine)[0][(1, 12)], 127.413)
            path = Path(folder) / 'losa.xlsx'
            export_workbook(path, 'Losa', restored, engine)
            formulas = load_workbook(path)
            values = load_workbook(path, data_only=True)
            try:
                self.assertIn('D13*H13*E13*F13*G13', formulas['Desarrollo']['M13'].value)
                self.assertAlmostEqual(values['Desarrollo']['M13'].value, 127.413)
            finally:
                formulas.close()
                values.close()

