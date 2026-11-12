"""Agreed rounding boundaries, preserved coefficients and both XLSX modes."""
from copy import deepcopy
from decimal import Decimal
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from openpyxl import load_workbook
import metrado._enlace as engine
from metrado.grid import SheetModel
from metrado.sheet import new_row, steel_detail, calculate
from metrado.excel_export import export_workbook
from metrado.database import write_database, read_database
from metrado import steel_config as sc
from metrado.references import make_reference
from metrado.steel_distribution import distributed_bar_count

APP = QApplication.instance() or QApplication([])


def area_rows():
    rows = [new_row('item', '01', 'Área', 'm2', 0)]
    for _ in range(2):
        row = new_row('detail', unit='m2', level=1)
        row['cells'][4:6] = ['0.05', '0.70']
        rows.append(row)
    return rows


class PrecisionPolicyTests(unittest.TestCase):
    def test_half_cents_and_totals_equal_sum_of_visible_details(self):
        model = SheetModel(engine, area_rows())
        self.assertEqual(model.values[1, 9], 0.04)
        self.assertEqual(model.values[0, 13], 0.08)
        self.assertEqual(model.data(model.index(1, 9)), '0.04')
        model.setData(model.index(1, 3), '-1')
        self.assertEqual(model.values[1, 9], -0.04)
        self.assertEqual(model.values[0, 13], 0)

    def test_general_inputs_normalized_in_load_edit_paste_history_and_save(self):
        rows = area_rows()
        rows[1]['cells'][4] = '1.234'
        model = SheetModel(engine, rows)
        self.assertEqual(Decimal(model.rows[1]['cells'][4]), Decimal('1.23'))
        self.assertTrue(model.setData(model.index(1, 4), '1.235'))
        self.assertEqual(Decimal(model.rows[1]['cells'][4]), Decimal('1.24'))
        model.undo_stack.undo()
        self.assertEqual(Decimal(model.rows[1]['cells'][4]), Decimal('1.23'))
        model.undo_stack.redo()
        model.paste_cells(1, 4, [['2.345']])
        self.assertEqual(Decimal(model.rows[1]['cells'][4]), Decimal('2.35'))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'obra.db'
            write_database(path, 'Obra', model.rows)
            self.assertEqual(Decimal(read_database(path)[1][1]['cells'][4]), Decimal('2.35'))

    def test_steel_keeps_weight_precision_until_final_product(self):
        row = steel_detail('Barra', 1, 100, 0, 0, '1/2"', 1)
        row['level'] = 1
        catalog = sc.initial_catalog()
        catalog['1/2"']['weight'] = '0.994413'
        sc.adopt(row, catalog)
        row['steel_hooks']['laps'] = False
        model = SheetModel(engine, [new_row('item', '01', 'Acero', 'kg', 0), row])
        self.assertEqual(model.values[1, 11], 0.994413)
        self.assertEqual(model.data(model.index(1, 10)), '0.994413')
        self.assertEqual(model.values[1, 12], 99.44)
        self.assertEqual(model.values[0, 13], 99.44)
        self.assertEqual(distributed_bar_count(27.5, '0.275'), 101)

    def test_reference_rounds_once_after_all_factors(self):
        model = SheetModel(engine, area_rows())
        rows = deepcopy(model.rows)
        rows += [new_row('item', '02', 'Volumen', 'm3', 0),
                 new_row('detail', unit='m3', level=1)]
        rows[-1]['cells'][3] = '3'
        rows[-1]['reference'] = make_reference(rows[0], 'm3', 'Espesor', '0.125')
        values, errors = calculate(rows, engine)
        self.assertFalse(errors)
        self.assertEqual(values[4, 10], 0.03)
        self.assertEqual(rows[-1]['reference']['factor'], '0.125')

    def test_xlsx_modes_store_same_rounded_results_and_formula_boundaries(self):
        model = SheetModel(engine, area_rows())
        with tempfile.TemporaryDirectory() as folder:
            for formulas in (True, False):
                path = Path(folder) / ('formulas.xlsx' if formulas else 'values.xlsx')
                export_workbook(path, 'Prueba', model.rows, engine, formulas=formulas)
                book = load_workbook(path, data_only=True)
                try:
                    self.assertEqual(book['Desarrollo']['J13'].value, 0.04)
                    self.assertEqual(book['Desarrollo']['N12'].value, 0.08)
                    self.assertEqual(book['Resumen']['D12'].value, 0.08)
                finally:
                    book.close()
                if formulas:
                    book = load_workbook(path)
                    try:
                        self.assertIn('ROUND(', book['Desarrollo']['J13'].value)
                    finally:
                        book.close()


if __name__ == '__main__':
    unittest.main()
