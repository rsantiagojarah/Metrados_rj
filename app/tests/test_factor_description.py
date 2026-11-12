"""A factor's purpose is its description, shared by UI, clipboard and Excel."""
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QLabel
from openpyxl import load_workbook
import metrado._enlace as engine
from metrado.clipboard import encode_rows, decode_rows, parse_tsv
from metrado.database import write_database, read_database
from metrado.excel_export import ExcelReport, export_workbook
from metrado.grid import SheetModel
from metrado.sheet import new_row, calculate
from metrado.swelling_dialog import SwellingDialog
from metrado.window import PlantillaWindow

APP = QApplication.instance() or QApplication([])
LOAN = 'Reparto de relleno: material de préstamo — 70 %'
OWN = 'Reparto de relleno: material propio — 30 %'


def sample():
    rows = []
    for number, (factor, description) in enumerate((('0.70', LOAN), ('0.30', OWN)), 1):
        rows += [new_row('item', str(number), description, 'm3', 0),
                 new_row('detail', description='Relleno', unit='m3', level=1)]
        rows[-1]['direct'] = '410.76'
        rows[-1]['volume_factor'] = dict(block=str(number), factor=factor, note=description)
    return rows


class FactorDescriptionTests(unittest.TestCase):
    def tearDown(self):
        APP.clipboard().clear()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)

    def test_ui_uses_description_and_neutral_symbol_with_unchanged_amounts(self):
        model = SheetModel(engine, sample())
        self.assertEqual(model.swelling_summary(1)[1], LOAN)
        self.assertEqual(model.swelling_summary(1)[8], 'F')
        self.assertEqual(model.swelling_summary(3)[1], OWN)
        self.assertEqual(model.values[0, 13], 287.53)
        self.assertEqual(model.values[2, 13], 123.23)
        self.assertEqual(engine.ask_sheet_total([model.values[0, 13], model.values[2, 13]]), 410.76)

    def test_blank_description_has_neutral_fallback(self):
        for note in ('', '  '):
            rows = sample();rows[1]['volume_factor']['note'] = note
            model = SheetModel(engine, rows)
            self.assertEqual(model.swelling_summary(1)[1], 'Ajuste por factor')
            report = ExcelReport('Prueba', rows, engine, formulas=False)
            try:
                self.assertEqual(report.dev[f'B{report.footers[1]}'].value, 'Ajuste por factor')
            finally:
                report.book.close()

    def test_dialog_names_existing_note_as_description(self):
        dialog = SwellingDialog(1, 410.76, engine, dict(factor='0.70', note=LOAN))
        try:
            self.assertEqual(dialog.windowTitle(), 'Ajuste por factor')
            self.assertIn('Descripción del ajuste:', [label.text() for label in dialog.findChildren(QLabel)])
            self.assertEqual(dialog.note.text(), LOAN)
            self.assertEqual(dialog.configuration(), dict(factor='0.70', note=LOAN))
        finally:
            dialog.deleteLater()

    def test_menu_uses_neutral_name_and_preserves_action_identity(self):
        window = PlantillaWindow(engine)
        try:
            self.assertEqual(window.swelling_action.text(), 'Ajuste por factor…')
            self.assertEqual(window.swelling_action.property('shortcut_id'), 'measure.swelling')
        finally:
            with patch.object(window, '_can_discard', return_value=True):
                window.close()
            window.deleteLater()

    def test_row_clipboard_contains_description_and_keeps_stored_note(self):
        model = SheetModel(engine, sample())
        mime = encode_rows(model, [1])
        matrix = parse_tsv(mime.text())
        self.assertEqual(matrix[-1][1], LOAN)
        self.assertEqual(matrix[-1][8], 'F')
        from metrado.clipboard import ROW_MIME
        self.assertEqual(decode_rows(mime.data(ROW_MIME))[0]['volume_factor']['note'], LOAN)

    def test_both_excel_modes_use_exact_description_and_preserve_results(self):
        rows = sample();before = deepcopy(rows)
        with tempfile.TemporaryDirectory() as folder:
            for formulas in (True, False):
                report = ExcelReport('Reparto', rows, engine, formulas=formulas)
                path = Path(folder) / ('formulas.xlsx' if formulas else 'valores.xlsx')
                export_workbook(path, 'Reparto', rows, engine, formulas=formulas)
                book = load_workbook(path, data_only=True)
                try:
                    for i, expected, quantity in ((1, LOAN, 287.53), (3, OWN, 123.23)):
                        row = report.footers[i]
                        self.assertEqual(book['Desarrollo'][f'B{row}'].value, expected)
                        self.assertEqual(book['Desarrollo'][f'I{row}'].value, 'F')
                        self.assertEqual(book['Desarrollo'][f'K{row}'].value, quantity)
                finally:
                    book.close();report.book.close()
        self.assertEqual(rows, before)

    def test_sqlite_and_history_keep_existing_note_and_factor(self):
        model = SheetModel(engine, sample())
        before = deepcopy(model.rows)
        model.set_swelling([1], dict(factor='0.70', note='Otra descripción'))
        self.assertEqual(model.swelling_summary(1)[1], 'Otra descripción')
        model.undo_stack.undo()
        self.assertEqual(model.rows, before)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'obra.db'
            write_database(path, 'Obra', model.rows)
            loaded = read_database(path)[1]
            self.assertEqual(loaded[1]['volume_factor'], before[1]['volume_factor'])
            self.assertEqual(calculate(loaded, engine), calculate(before, engine))

    def test_description_that_looks_like_a_formula_remains_literal_in_excel(self):
        rows = sample()
        rows[1]['volume_factor']['note'] = '=1+1'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'literal.xlsx'
            report = ExcelReport('Literal', rows, engine)
            export_workbook(path, 'Literal', rows, engine)
            book = load_workbook(path)
            try:
                cell = book['Desarrollo'][f'B{report.footers[1]}']
                self.assertEqual(cell.value, '=1+1')
                self.assertEqual(cell.data_type, 's')
            finally:
                book.close();report.book.close()


if __name__ == '__main__':
    unittest.main()
