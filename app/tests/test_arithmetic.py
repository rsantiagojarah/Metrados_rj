import os
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QLineEdit
from PySide6.QtTest import QTest
from metrado.arithmetic import numeric_text
from metrado.numeric_edit import NumericEdit
from metrado.grid import SheetModel, SheetView
from metrado.sheet import new_row, write_project, read_project
from metrado.reference_dialog import ConversionDialog
from metrado.swelling_dialog import SwellingDialog
from metrado.steel_dialog import CatalogDialog, HooksDialog
from metrado import steel_config as sc
from metrado.window import PlantillaWindow
import metrado._enlace as engine

APP = QApplication.instance() or QApplication([])


class ArithmeticTests(unittest.TestCase):
    def test_operations_precedence_and_decimal_comma(self):
        for expression, result in [('2+3', '5'), ('10-2,5', '7.5'), ('2,4*3', '7.2'),
                                   ('12/4', '3'), ('(2+3)*4', '20'), ('2^3+4', '12'),
                                   ('2*3^2', '18'), ('9^(1/2)', '3'), ('4^(-1)', '0.25'),
                                   ('2^3^2', '512'), ('-2^2', '-4'), ('(-2)^2', '4'),
                                   ('0.1+0.2', '0.3'), ('1e-3*2', '0.002')]:
            with self.subTest(expression=expression):
                self.assertEqual(numeric_text(expression), result)

    def test_unsafe_invalid_and_extreme_expressions(self):
        for text in ['1/0', '2+', '1//2', '2%3', 'abs(-1)', '__import__("os")',
                     '(1).__class__', '[1][0]', 'True', '1<2', 'nan', 'inf',
                     '(-1)^0.5', '0^-1', '2^10001', '10^309', '1e309',
                     '1e-400', '1e-300*1e-300', '1+' * 300 + '1']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                numeric_text(text)

    def test_constraints_and_plain_values(self):
        self.assertEqual(numeric_text('0,350'), '0,350')
        self.assertEqual(numeric_text('01'), '01')
        self.assertEqual(numeric_text('', allow_blank=True), '')
        self.assertEqual(numeric_text('6/2', integer=True), '3')
        for value, rules in [('5/2', dict(integer=True)), ('1-1', dict(positive=True)),
                             ('1-2', dict(nonnegative=True)), ('2-2', dict(nonzero=True))]:
            with self.assertRaises(ValueError):
                numeric_text(value, **rules)

    def test_numeric_editor_commit_restore_and_integer(self):
        edit = NumericEdit('4', positive=True, integer=True)
        errors = []
        edit.inputError.connect(errors.append)
        edit.setText('2^3')
        edit.editingFinished.emit()
        self.assertEqual(edit.text(), '8')
        edit.setText('5/2')
        edit.editingFinished.emit()
        self.assertEqual(edit.text(), '8')
        self.assertTrue(errors)

    def test_sheet_save_undo_and_no_mutation_on_failure(self):
        model = SheetModel(engine, [new_row('item', unit='m3'), new_row('detail', unit='m3')])
        for col, expression in [(4, '2+3'), (5, '6/2'), (6, '2^2'), (3, '1+1')]:
            self.assertTrue(model.setData(model.index(1, col), expression))
        self.assertEqual(model.values[(0, 13)], 120)
        before = deepcopy(model.rows)
        count = model.undo_stack.count()
        errors = []
        model.inputError.connect(errors.append)
        self.assertFalse(model.setData(model.index(1, 4), '1/0'))
        self.assertEqual(model.rows, before)
        self.assertEqual(model.undo_stack.count(), count)
        self.assertTrue(errors)
        model.undo_stack.undo()
        self.assertEqual(model.values[(0, 13)], 60)
        model.undo_stack.redo()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'math.json'
            write_project(path, 'Math', model.rows)
            restored = read_project(path)[1]
            self.assertEqual(restored[1]['cells'][4:7], ['5', '3', '4'])

    def test_direct_and_area_base(self):
        model = SheetModel(engine, [new_row('item', unit='m3'), new_row('detail', unit='m3')])
        model.set_direct(1, '2^3+4')
        self.assertEqual(model.rows[1]['direct'], '12')
        model.set_direct(1, '1/0')
        self.assertEqual(model.rows[1]['direct'], '12')
        self.assertFalse(model.setData(model.index(1, 5), '2+3'))
        self.assertTrue(model.setData(model.index(1, 9), '5*5'))
        model.setData(model.index(1, 6), '1/5')
        self.assertEqual(model.values[(1, 10)], 5)

    def test_table_keyboard_enter_and_tab_commit_only_results(self):
        model = SheetModel(engine, [new_row('item', unit='m3'), new_row('detail', unit='m3')])
        view = SheetView(model)
        view.show()
        try:
            for column, expression, key, result in [(4, '2^3+4', Qt.Key_Return, '12'),
                                                    (5, '6/2', Qt.Key_Tab, '3')]:
                index = model.index(1, column)
                view.setCurrentIndex(index)
                view.edit(index)
                APP.processEvents()
                editor = view.findChild(QLineEdit)
                self.assertIsNotNone(editor)
                QTest.keyClicks(editor, expression)
                QTest.keyClick(editor, key)
                APP.processEvents()
                self.assertEqual(model.rows[1]['cells'][column], result)
        finally:
            view.close()
            view.deleteLater()

    def test_text_and_diameter_are_not_arithmetic(self):
        model = SheetModel(engine, [new_row('item', unit='kg'), new_row('detail', unit='kg')])
        model.setData(model.index(1, 1), 'Muro 2+3')
        self.assertIn('Muro 2+3', model.rows[1]['cells'][1])
        self.assertTrue(model.setData(model.index(1, 9), '1/2"'))
        self.assertEqual(model.rows[1]['cells'][7], '1/2"')
        self.assertTrue(model.setData(model.index(1, 5), '2-2'))
        self.assertEqual(model.rows[1]['cells'][5], '0')

    def test_conversion_swelling_and_catalog(self):
        conversion = ConversionDialog('m2', 'm3', name='Espesor', factor='1/5')
        conversion.accept()
        self.assertEqual(conversion.result(), QDialog.Accepted)
        self.assertEqual(conversion.factor.text(), '0.2')
        swelling = SwellingDialog(1, 10, engine)
        swelling.factor.setText('1+20/100')
        self.assertEqual(swelling.configuration()['factor'], '1.2')
        swelling.accept()
        self.assertEqual(swelling.factor.text(), '1.2')
        catalog = CatalogDialog(sc.initial_catalog())
        index = catalog.table.model().index(0, 1)
        delegate = catalog.table.itemDelegate()
        editor = QLineEdit('1/4')
        delegate.setModelData(editor, catalog.table.model(), index)
        self.assertEqual(catalog.configuration()['6mm']['weight'], '0.25')
        editor.setText('1/0')
        delegate.setModelData(editor, catalog.table.model(), index)
        self.assertEqual(catalog.configuration()['6mm']['weight'], '0.25')
        hooks = HooksDialog([], [])
        hooks.custom.setChecked(True)
        hooks.length.setText('3/10')
        self.assertEqual(hooks.configuration(), (1, '0.3'))

    def test_direct_dialog_evaluates_before_engine_validation(self):
        # Invoke the existing action with a minimal window surface.
        from types import SimpleNamespace
        model = SheetModel(engine, [new_row('item', unit='m2'), new_row('detail', unit='m2')])
        window = SimpleNamespace(_commit_editors=lambda: None, model=model, _enlace=engine,
                                 table=SimpleNamespace(currentIndex=lambda: model.index(1, 1)),
                                 _select=lambda i: None)
        with patch('metrado.window.QInputDialog.getText', return_value=('2^3+4', True)):
            PlantillaWindow.direct_quantity(window)
        self.assertEqual(model.rows[1]['direct'], '12')
