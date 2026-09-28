"""Minimal OOXML fixtures exercise actual file reading, without Excel installed."""
from copy import deepcopy
from hashlib import sha256
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from xml.sax.saxutils import escape
from zipfile import ZipFile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QToolBar
import metrado._enlace as engine
from metrado.database import read_database, write_database
from metrado.excel_import import ExcelBudget, unit_code
from metrado.excel_dialog import ExcelImportDialog, PreviewModel
from metrado.hierarchy import Outline
from metrado.grid import SheetModel
from metrado.sheet import calculate, new_row, read_project, write_project
from metrado.steel_store import CatalogStore
from metrado.window import PlantillaWindow

APP = QApplication.instance() or QApplication([])
NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
BASE = [('Item', 'Descripción', 'Unidad'), ('01', 'TÍTULO', ''),
        ('01.01', 'SUBTÍTULO', ''), ('01.01.01', 'EXCAVACIÓN', 'M³'),
        ('01.01.02', 'SEGURIDAD', 'DÍA'), ('02', 'ACEROS', ''), ('02.01', 'ACERO', 'KG')]


def workbook(path, sheets):
    """Write bounded in-test XLSX containers, not user-facing workbooks."""
    with ZipFile(path, 'w') as z:
        z.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '</Types>')
        z.writestr('xl/workbook.xml', f'<workbook xmlns="{NS}" xmlns:r="{REL}"><sheets>' + ''.join(
            f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>' for i, name in enumerate(sheets, 1)) + '</sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + ''.join(
            f'<Relationship Id="rId{i}" Type="{REL}/worksheet" Target="worksheets/sheet{i}.xml"/>'
            for i in range(1, len(sheets) + 1)) + '</Relationships>')
        z.writestr('xl/styles.xml', f'<styleSheet xmlns="{NS}">'
            '<numFmts count="1"><numFmt numFmtId="164" formatCode="00"/></numFmts>'
            '<fonts count="1"><font><name val="Arial"/></font></fonts>'
            '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
            '<borders count="1"><border/></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="2"><xf numFmtId="0"/><xf numFmtId="164"/></cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
        for i, rows in enumerate(sheets.values(), 1):
            data = []
            for r, values in enumerate(rows, 1):
                cells = []
                for c, value in enumerate(values):
                    if value is None:
                        continue
                    ref = f'{chr(65 + c)}{r}'
                    if isinstance(value, dict):
                        # Raw numeric/formula/error cells exercise openpyxl's types.
                        attrs = value.get('attrs', '')
                        cells.append(f'<c r="{ref}" {attrs}>{value["xml"]}</c>')
                    else:
                        cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>')
                data.append(f'<row r="{r}">{"".join(cells)}</row>')
            z.writestr(f'xl/worksheets/sheet{i}.xml', f'<worksheet xmlns="{NS}"><sheetData>{"".join(data)}</sheetData></worksheet>')


class ExcelFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'Presupuesto.xlsx'

    def tearDown(self):
        self.temp.cleanup()


class ExcelTests(ExcelFixture, unittest.TestCase):
    def test_preview_cells_have_no_hover_comments(self):
        model = PreviewModel([new_row('item', '01.01', 'PARTIDA', 'm3', 1)])
        for column in range(model.columnCount()):
            self.assertIsNone(model.data(model.index(0, column), Qt.ToolTipRole))

    def read(self, rows=BASE):
        workbook(self.path, {'Presupuesto': rows, 'Vacía': []})
        with ExcelBudget(self.path) as budget:
            self.assertEqual(list(budget.headers), ['Presupuesto'])
            return budget.read('Presupuesto')

    def test_codes_hierarchy_names_units_and_empty_measurements(self):
        result = self.read()
        self.assertEqual((result.titles, result.items), (3, 3))
        self.assertEqual([r['cells'][0] for r in result.rows], [r[0] for r in BASE[1:]])
        self.assertEqual([r['level'] for r in result.rows], [0, 1, 2, 2, 0, 1])
        self.assertEqual([r['cells'][2] for r in result.rows], ['', '', 'm3', 'dia', '', 'kg'])
        self.assertTrue(all(not any(r['cells'][3:]) and not r['direct'] for r in result.rows))
        self.assertEqual(len({r['id'] for r in result.rows}), 6)
        Outline(result.rows, strict=True)

    def test_reordered_columns_preamble_and_repeated_header(self):
        rows = [('Presupuesto',), (), ('Unidad', 'Precio', 'Partida', 'Ítem'),
                ('', '500', 'TÍTULO', '01'), ('M2', '1000', 'PARTIDA', '01.01'),
                ('Unidad', 'Precio', 'Partida', 'Ítem'), ('UND', '2000', 'OTRA', '01.02')]
        self.assertEqual(self.read(rows).items, 2)

    def test_unit_aliases(self):
        for raw, expected in [('M²', 'm2'), ('m^3', 'm3'), ('DÍAS', 'dia'), ('UND.', 'und'),
                              ('ml', 'm'), ('GLB', 'glb'), ('MES', 'mes'), ('VJE', 'vje'), ('KG', 'kg')]:
            self.assertEqual(unit_code(raw), expected)

    def test_no_header_empty_or_no_items_rejected(self):
        for rows in [[], [('hola',)], [BASE[0], BASE[1]]]:
            with self.assertRaises(ValueError):
                self.read(rows)

    def test_invalid_rows_report_excel_row_and_no_partial_result(self):
        bad_rows = [('01', 'DUPLICADO', ''), ('02.01', 'SIN PADRE', 'm'),
                    ('01.02', '', 'm'), ('01.02', 'UNIDAD', 'ton'),
                    ('01.02', 'UNIDAD CERO', {'xml': '<v>0</v>'}),
                    ('bad', 'CÓDIGO', 'm'), ('', 'SIN ÍTEM', 'm')]
        for bad in bad_rows:
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, 'fila 3'):
                self.read([BASE[0], BASE[1], bad])

    def test_item_cannot_be_parent_or_return_to_closed_branch(self):
        for rows in [[BASE[0], ('01', 'PARTIDA', 'm'), ('01.01', 'HIJA', 'm')],
                     [BASE[0], BASE[1], ('02', 'OTRA', ''), ('01.01', 'FUERA DE ORDEN', 'm')]]:
            with self.assertRaises(ValueError):
                self.read(rows)

    def test_duplicate_canonical_code(self):
        with self.assertRaisesRegex(ValueError, 'duplicado'):
            self.read([BASE[0], ('01', 'UNO', 'm'), ('1', 'OTRO', 'm')])

    def test_numeric_integers_allowed_but_decimal_codes_require_text(self):
        numeric = {'xml': '<v>1</v>'}
        self.assertEqual(self.read([BASE[0], (numeric, 'PARTIDA', 'm')]).rows[0]['cells'][0], '1')
        numeric['attrs'] = 's="1"'
        self.assertEqual(self.read([BASE[0], (numeric, 'PARTIDA', 'm')]).rows[0]['cells'][0], '01')
        numeric['xml'] = '<v>1.01</v>'
        with self.assertRaisesRegex(ValueError, 'como texto'):
            self.read([BASE[0], (numeric, 'PARTIDA', 'm')])

    def test_formula_or_excel_error_in_imported_columns_rejected(self):
        for bad in [{'xml': '<f>1+1</f><v>2</v>'}, {'attrs': 't="e"', 'xml': '<v>#REF!</v>'}]:
            for column in range(3):
                row = ['01', 'PARTIDA', 'm']
                row[column] = bad
                with self.assertRaisesRegex(ValueError, 'fórmulas ni errores'):
                    self.read([BASE[0], row])

    def test_row_limits_do_not_silently_truncate(self):
        with patch('metrado.excel_import.MAX_ROWS', 2), self.assertRaisesRegex(ValueError, '10 000'):
            self.read()
        with patch('metrado.excel_import.MAX_SOURCE_ROWS', 4), self.assertRaisesRegex(ValueError, 'filas de origen'):
            self.read([BASE[0], ('01', 'PARTIDA', 'm'), (), (), (), ('02', 'LEJANA', 'm')])

    def test_corrupt_file_and_legacy_extension_rejected(self):
        for name in ('roto.xlsx', 'antiguo.xls'):
            path = self.path.with_name(name)
            # A ZIP without workbook metadata is a corrupt Excel fixture.
            with ZipFile(path, 'w'):
                pass
            with self.assertRaises(ValueError):
                ExcelBudget(path)

    def test_source_unchanged_and_sqlite_json_roundtrip(self):
        workbook(self.path, {'Presupuesto': BASE})
        before = sha256(self.path.read_bytes()).digest()
        with ExcelBudget(self.path) as budget:
            rows = budget.read('Presupuesto').rows
        self.assertEqual(sha256(self.path.read_bytes()).digest(), before)
        db = self.path.with_suffix('.db')
        write_database(db, 'Importado', rows)
        restored = read_database(db)[1]
        self.assertEqual(restored, rows)
        export = self.path.with_suffix('.json')
        write_project(export, 'Importado', rows)
        self.assertEqual(read_project(export)[1], rows)

    def test_day_calculation_negative_reference_and_undo(self):
        rows = [new_row('item', '01', 'Días', 'dia', 0), new_row('detail', unit='dia', level=1),
                new_row('item', '02', 'Días enlazados', 'dia', 0), new_row('detail', unit='dia', level=1)]
        model = SheetModel(engine, rows)
        try:
            model.set_reference(3, model.rows[0]['id'])
            model.setData(model.index(1, 7), '30')
            self.assertEqual((model.values[(0, 13)], model.values[(2, 13)]), (30, 30))
            model.setData(model.index(3, 3), '-1')
            self.assertEqual(model.values[(2, 13)], -30)
            model.undo_stack.undo()
            self.assertEqual(model.values[(2, 13)], 30)
            write_database(self.path.with_suffix('.db'), 'Días', model.rows)
            self.assertEqual(calculate(read_database(self.path.with_suffix('.db'))[1], engine), (model.values, model.errors))
        finally:
            model.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


class ExcelWindowTests(ExcelFixture, unittest.TestCase):
    # Reuse only fixture setup, not the reader test suite.
    def setUp(self):
        super().setUp()
        workbook(self.path, {'Presupuesto': BASE, 'Otra': [BASE[0], ('01', 'OTRA', 'M')],
                             'Inválida': [BASE[0], ('01', 'UNIDAD', 'TON')]})
        self.window = PlantillaWindow(engine, CatalogStore(Path(self.temp.name) / 'catalog.db'))

    def tearDown(self):
        with patch.object(self.window, '_can_discard', return_value=True):
            self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        super().tearDown()

    def test_menu_only_and_command_palette(self):
        action = self.window.import_excel_action
        menus = [a.menu() for a in self.window.menuBar().actions()]
        self.assertTrue(any(m.title() == 'Archivo' and action in m.actions() for m in menus))
        self.assertIn(action, self.window.keyboard.commands)
        self.assertNotIn(action, self.window.findChild(QToolBar, 'actionStrip').actions())

    def test_preview_switch_errors_and_confirmation(self):
        with ExcelBudget(self.path) as budget:
            dialog = ExcelImportDialog(budget)
            try:
                self.assertEqual(dialog.preview.model().rowCount(), 6)
                dialog.sheet.setCurrentText('Otra')
                self.assertEqual(dialog.result.items, 1)
                dialog.sheet.setCurrentText('Inválida')
                self.assertIsNone(dialog.result)
                self.assertFalse(dialog.buttons.button(QDialogButtonBox.Ok).isEnabled())
                self.assertIn('fila 2', dialog.summary.text())
                dialog.sheet.setCurrentText('Presupuesto')
                self.assertTrue(dialog.buttons.button(QDialogButtonBox.Ok).isEnabled())
            finally:
                dialog.deleteLater()
                QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)

    def test_cancel_file_or_preview_preserves_current_project(self):
        before = deepcopy(self.window.model.rows)
        for filename, result in [('', QDialog.Accepted), (str(self.path), QDialog.Rejected)]:
            with patch('metrado.window.QFileDialog.getOpenFileName', return_value=(filename, '')), \
                 patch('metrado.excel_dialog.ExcelImportDialog.exec', return_value=result), \
                 patch.object(self.window, '_can_discard') as discard:
                self.window.import_excel()
                discard.assert_not_called()
                self.assertEqual(before, self.window.model.rows)

    def test_save_guard_cancel_preserves_current_project(self):
        before = deepcopy(self.window.model.rows)
        with patch('metrado.window.QFileDialog.getOpenFileName', return_value=(str(self.path), '')), \
             patch('metrado.excel_dialog.ExcelImportDialog.exec', return_value=QDialog.Accepted), \
             patch.object(self.window, '_can_discard', return_value=False):
            self.window.import_excel()
        self.assertEqual(before, self.window.model.rows)

    def test_unreadable_file_keeps_history_and_never_asks_to_discard(self):
        self.window.model.setData(self.window.model.index(0, 1), 'CAMBIO PENDIENTE')
        before = deepcopy(self.window.model.rows)
        history = self.window.model.undo_stack.index()
        with patch('metrado.window.QFileDialog.getOpenFileName', return_value=(str(self.path.with_name('ausente.xlsx')), '')), \
             patch('metrado.window.QMessageBox.warning') as warning, \
             patch.object(self.window, '_can_discard') as discard:
            self.window.import_excel()
        warning.assert_called_once()
        discard.assert_not_called()
        self.assertEqual(self.window.model.rows, before)
        self.assertEqual(self.window.model.undo_stack.index(), history)

    def test_import_new_unsaved_project_and_save_does_not_overwrite_excel(self):
        original = self.path.read_bytes()
        self.window._path, self.window._revision = Path(self.temp.name) / 'anterior.db', 7
        with patch('metrado.window.QFileDialog.getOpenFileName', return_value=(str(self.path), '')), \
             patch('metrado.excel_dialog.ExcelImportDialog.exec', return_value=QDialog.Accepted), \
             patch.object(self.window, '_can_discard', return_value=True):
            self.window.import_excel()
        self.assertEqual(len(self.window.model.rows), 6)
        self.assertEqual(self.window.title_edit.text(), 'Presupuesto')
        self.assertIsNone(self.window._path)
        self.assertIsNone(self.window._revision)
        self.assertTrue(self.window._dirty)
        self.assertFalse(self.window.model.undo_stack.isClean())
        self.assertEqual(self.window.model.rows[2]['cells'][0], '01.01.01')
        dest = self.path.with_suffix('.db')
        with patch('metrado.window.QFileDialog.getSaveFileName', return_value=(str(dest), '')):
            self.assertTrue(self.window.save_project())
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse(self.window._dirty)


if __name__ == '__main__':
    unittest.main()
