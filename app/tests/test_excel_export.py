"""Report round trips, initial engine parity, formula wiring and UI safety."""
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from openpyxl import load_workbook
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QToolBar, QMessageBox
import metrado._enlace as engine
from metrado.excel_export import ExcelReport, export_workbook, PENDING
from metrado.identity import ensure_ids
from metrado.references import make_reference
from metrado.sheet import new_row, example_rows, steel_detail, calculate
from metrado import steel_config as sc
from metrado.steel_store import CatalogStore
from metrado.window import PlantillaWindow

APP = QApplication.instance() or QApplication([])


def geometry(unit='m3', count=2):
    rows = [new_row('item', '01.01', 'EXCAVACIÓN', unit, 0)]
    for i in range(count):
        row = new_row('detail', description=f'Tramo {i+1}', unit=unit, level=1)
        row['cells'][4:7] = ['2', '3', '4']
        rows.append(row)
    ensure_ids(rows)
    return rows


def comprehensive_rows():
    rows = geometry()
    for row in rows[1:]:
        row['volume_factor'] = dict(block='bloque-1', factor='1.2', note='Material excavado')
    # Signed same-unit reference, then a dimension conversion and a forward link.
    rows += [new_row('item', '02', 'RELLENO', 'm3', 0),
             new_row('detail', description='Referencia negativa', unit='m3', level=1)]
    rows[4]['reference'] = make_reference(rows[0], 'm3')
    rows[4]['cells'][3] = '-1'
    rows += [new_row('item', '03', 'ÁREA EQUIVALENTE', 'm2', 0),
             new_row('detail', unit='m2', level=1)]
    rows[6]['reference'] = make_reference(rows[0], 'm2', 'Inverso de espesor', '2')
    rows += [new_row('item', '04', 'ACERO', 'kg', 0)]
    bar = steel_detail('Barra principal', 2, 8.5, 0, 0, '1/2"', 4)
    bar['level'] = 1
    catalog = sc.initial_catalog()
    sc.adopt(bar, catalog)
    bar['steel_hooks'] = dict(count=2, override='0.4')
    sc.sync_dimensions(bar)
    rows.append(bar)
    rows += [new_row('item', '05', 'DÍAS', 'dia', 0), new_row('detail', unit='dia', level=1)]
    rows[-1]['cells'][7] = '-3'
    ensure_ids(rows)
    return rows


class ExcelExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'metrados.xlsx'
        self.books = []

    def tearDown(self):
        for book in self.books:
            book.close()
        self.temp.cleanup()

    def read(self, rows, title='Proyecto de prueba'):
        export_workbook(self.path, title, rows, engine)
        formula = load_workbook(self.path)
        cached = load_workbook(self.path, data_only=True)
        self.books.extend([formula, cached])
        return formula, cached

    def test_two_sheets_a4_repeated_headers_and_no_indentation(self):
        book, _ = self.read(example_rows())
        self.assertEqual(book.sheetnames, ['Desarrollo', 'Resumen'])
        for name, orientation, titles in [('Desarrollo', 'portrait', '$1:$11'), ('Resumen', 'portrait', '$1:$11')]:
            sheet = book[name]
            self.assertEqual(str(sheet.page_setup.paperSize), sheet.PAPERSIZE_A4)
            self.assertEqual(sheet.page_setup.orientation, orientation)
            self.assertEqual(sheet.print_title_rows, titles)
            self.assertEqual(sheet.page_setup.fitToWidth, 1)
            self.assertEqual(sheet.page_setup.fitToHeight, 0)
            self.assertEqual(sheet.sheet_view.zoomScale, 90)
            self.assertFalse(sheet.sheet_view.showGridLines)
            for row in sheet:
                for cell in row:
                    self.assertEqual(cell.alignment.indent, 0)
        self.assertEqual(book.calculation.calcMode, 'auto')
        self.assertTrue(book['Desarrollo'].column_dimensions['O'].hidden)
        self.assertNotIn('O', str(book['Desarrollo'].print_area))
        self.assertFalse(any(cell.comment for sheet in book for row in sheet for cell in row))

    def test_every_initial_total_equals_engine_without_mutating_document(self):
        for rows in (example_rows(), comprehensive_rows()):
            before = deepcopy(rows)
            report = ExcelReport('Obra', rows, engine)
            _, cache = self.read(rows)
            expected, errors = calculate(rows, engine)
            self.assertFalse(errors)
            for i, row in enumerate(rows):
                if row['kind'] == 'item':
                    self.assertAlmostEqual(cache['Desarrollo'][f'N{report.positions[i]}'].value, expected[i, 13])
            self.assertEqual(rows, before)

    def test_reference_header_has_project_fields_and_separate_black_frames(self):
        book, _ = self.read(geometry(), 'Proyecto real de prueba')
        for sheet in book:
            self.assertEqual(sheet['B3'].value, 'Proyecto real de prueba')
            self.assertEqual([sheet.cell(r, 1).value for r in range(3, 8)],
                             ['Proyecto:', 'Propietario:', 'Fecha:', 'Especialidad:', 'Módulo:'])
            self.assertIsNone(sheet['B4'].value)
            self.assertIsNone(sheet['B6'].value)
            self.assertIsNone(sheet['B7'].value)
            self.assertTrue(sheet['B5'].is_date)
            self.assertEqual(sheet['A1'].border.top.style, 'medium')
            self.assertEqual(sheet['A3'].border.left.style, 'medium')
            self.assertEqual(sheet['A7'].border.bottom.style, 'medium')
            self.assertEqual(sheet['A9'].fill.fgColor.rgb[-6:], 'D9D9D9')
            self.assertEqual(sheet.freeze_panes, 'C12')
        self.assertEqual(book['Desarrollo']['A1'].value, 'METRADOS')
        self.assertEqual(book['Resumen']['A1'].value, 'RESUMEN DE METRADOS')
        self.assertEqual(book['Desarrollo']['I4'].value, 'Hecho por:')
        self.assertEqual(book['Resumen']['C5'].value, 'Revisado por:')

    def test_reference_typography_colors_and_grid_do_not_merge_body_columns(self):
        rows = [new_row('chapter', '01', 'TÍTULO', level=0),
                new_row('chapter', '01.01', 'SUBTÍTULO', level=1),
                new_row('item', '01.01.01', 'PARTIDA', 'm3', 2),
                new_row('detail', description='Detalle', unit='m3', level=3)]
        book, _ = self.read(rows)
        for sheet in book:
            for r, color in ((12, '990099'), (13, 'FF0000'), (14, '000000')):
                cell = sheet.cell(r, 2)
                self.assertEqual(cell.font.name, 'Arial Narrow')
                self.assertEqual(cell.font.color.rgb[-6:], color)
                self.assertIn(cell.fill.fgColor.rgb[-6:], ('FFFFFF', '000000'))
                for side in ('top', 'bottom', 'left', 'right'):
                    self.assertEqual(getattr(cell.border, side).style, 'thin')
            self.assertTrue(all(rng.max_row < 12 for rng in sheet.merged_cells.ranges))
        self.assertTrue(book['Desarrollo']['B14'].font.bold)
        self.assertFalse(book['Desarrollo']['B15'].font.bold)
        self.assertEqual(book['Desarrollo']['C9'].alignment.text_rotation, 90)
        self.assertEqual(book['Desarrollo']['E9'].value, 'DIMENSIONES')
        self.assertEqual(book['Desarrollo']['I9'].value, 'METRADO')

    def test_portrait_steel_display_rounds_without_losing_weight_precision(self):
        book, cache = self.read(comprehensive_rows())
        self.assertEqual(book['Desarrollo']['K21'].number_format, '0.00')
        self.assertEqual(cache['Desarrollo']['K21'].value,
                         float(comprehensive_rows()[8]['steel_catalog']['1/2"']['weight']))
        self.assertTrue(book['Desarrollo']['N20'].alignment.shrink_to_fit)
        self.assertEqual(book['Desarrollo']['B20'].font.sz, 8)

    def test_steel_uses_item_row_labels_without_extra_gray_header(self):
        book, cache = self.read(comprehensive_rows())
        sheet = book['Desarrollo']
        self.assertEqual([sheet.cell(20, c).value for c in (6, 7, 10, 11)],
                         ['gancho', 'empal.', 'diam.', 'kg/m'])
        self.assertEqual(cache['Desarrollo']['B21'].value, 'Barra principal 4 Ø1/2"')
        self.assertIsNone(sheet['B21'].fill.fill_type)
        self.assertNotIn('ACERO · longitudes en m',
                         [sheet.cell(r, 2).value for r in range(12, sheet.max_row + 1)])

    def test_all_units_signed_and_direct_values(self):
        for unit in ('m', 'm2', 'm3', 'kg', 'und', 'mes', 'glb', 'vje', 'dia'):
            rows = geometry(unit, 1)
            rows[1]['direct'] = '2,5'
            rows[1]['cells'][3] = '-2'
            rows[1]['cells'][9 if unit == 'kg' else 7] = '3'
            formula, cache = self.read(rows)
            self.assertEqual(cache['Desarrollo']['N12'].value, -15)
            self.assertIn('COUNT', formula['Desarrollo']['L13' if unit == 'kg' else
                {'m': 'I13', 'm2': 'J13', 'm3': 'K13'}.get(unit, 'M13')].value)

    def test_fe_has_one_contribution_and_separate_editable_factor(self):
        rows = comprehensive_rows()
        book, cache = self.read(rows)
        sheet = book['Desarrollo']
        self.assertEqual(sheet['J15'].value, 1.2)
        self.assertEqual(sheet['O13'].value, 0)
        self.assertEqual(sheet['O14'].value, 0)
        self.assertEqual(sheet['O15'].value, '=K15')
        self.assertIn('SUM(K13:K14)*J15', sheet['K15'].value)
        self.assertAlmostEqual(cache['Desarrollo']['N12'].value, 57.6)

    def test_multiple_fe_blocks_and_free_details_contribute_once(self):
        rows = geometry(count=5)
        for i, factor, block in ((1, '1.2', 'a'), (2, '1.2', 'a'), (4, '1.5', 'b'), (5, '1.5', 'b')):
            rows[i]['volume_factor'] = dict(block=block, factor=factor, note='')
        report = ExcelReport('Obra', rows, engine)
        book, cache = self.read(rows)
        self.assertEqual(len(report.footers), 2)
        self.assertAlmostEqual(cache['Desarrollo']['N12'].value, 48*1.2 + 24 + 48*1.5)
        free = report.positions[3]
        self.assertEqual(book['Desarrollo'][f'O{free}'].value, f'=K{free}')

    def test_pending_in_fe_and_unit_changed_reference_propagates(self):
        rows = comprehensive_rows()
        rows[1]['cells'][4] = ''
        _, cache = self.read(rows)
        for address in ('K15', 'N12', 'N16', 'N18'):
            self.assertEqual(cache['Desarrollo'][address].value, PENDING)
        rows = comprehensive_rows()
        rows[0]['cells'][2] = rows[1]['cells'][2] = rows[2]['cells'][2] = 'm'
        rows[1].pop('volume_factor'); rows[2].pop('volume_factor')
        _, cache = self.read(rows)
        report = ExcelReport('Obra', rows, engine)
        self.assertEqual(cache['Desarrollo'][f'N{report.positions[5]}'].value, PENDING)

    def test_reference_links_source_and_factor_only_for_incompatible_units(self):
        rows = comprehensive_rows()
        book, cache = self.read(rows)
        self.assertEqual(book['Desarrollo']['E17'].value, '=N12')
        self.assertIsNone(book['Desarrollo']['F17'].value)
        self.assertEqual(book['Desarrollo']['F19'].value, 2)
        self.assertIn('TEXT(F19', book['Desarrollo']['B19'].value)
        self.assertAlmostEqual(cache['Desarrollo']['N16'].value, -57.6)
        self.assertAlmostEqual(cache['Desarrollo']['N18'].value, 115.2)

    def test_forward_reference_and_summary_are_formulas(self):
        rows = geometry('m', 1)
        linked = geometry('m', 1)
        linked[0]['cells'][0] = '02'
        linked[1]['reference'] = make_reference(rows[0], 'm')
        book, cache = self.read(linked + rows)
        self.assertEqual(book['Desarrollo']['E13'].value, '=N14')
        self.assertEqual(book['Resumen']['D12'].value, "='Desarrollo'!N12")
        self.assertEqual(cache['Resumen']['D12'].value, 2)

    def test_steel_automatic_laps_catalog_and_suffix(self):
        book, cache = self.read(comprehensive_rows())
        sheet = book['Desarrollo']
        self.assertIn('ROUNDUP', sheet['G21'].value)
        self.assertIn('MATCH(J21', sheet['K21'].value)
        self.assertEqual(sheet['Q21'].value, 2)
        self.assertEqual(sheet['R21'].value, .4)
        self.assertEqual(cache['Desarrollo']['F21'].value, .8)
        self.assertGreater(cache['Desarrollo']['G21'].value, 0)
        self.assertIn('4 Ø1/2"', cache['Desarrollo']['B21'].value)
        self.assertTrue(sheet.data_validations.dataValidation)

    def test_zero_hooks_without_override_and_distinct_historical_catalogs(self):
        rows = comprehensive_rows()
        rows[8]['steel_hooks'] = dict(count=0, override=None)
        second = deepcopy(rows[8]); second.pop('id')
        second['steel_catalog']['1/2"']['weight'] = '5'
        rows.insert(9, second)
        report = ExcelReport('Obra', rows, engine)
        book, cache = self.read(rows)
        self.assertIsNone(book['Desarrollo']['R21'].value)
        self.assertEqual(cache['Desarrollo']['F21'].value, 0)
        self.assertEqual(len(report.catalogs), 2)
        self.assertEqual(cache['Desarrollo']['K22'].value, 5)

    def test_legacy_steel_manual_lengths_and_repetitions_preserved(self):
        rows = [new_row('item', '01', 'Acero', 'kg', 0), steel_detail('Barra', -2, 10, .6, 1, '1"', 5)]
        rows[1]['level'] = 1; rows[1]['cells'][9] = '3'
        book, cache = self.read(rows)
        self.assertEqual(book['Desarrollo']['H13'].value, 15)
        self.assertEqual(book['Desarrollo']['F13'].value, .6)
        self.assertEqual(book['Desarrollo']['G13'].value, 1)
        self.assertAlmostEqual(cache['Desarrollo']['N12'].value, calculate(rows, engine)[0][0, 13])

    def test_missing_measurements_propagate_pending_not_zero(self):
        rows = geometry()
        rows[1]['cells'][4] = ''
        book, cache = self.read(rows)
        self.assertEqual(cache['Desarrollo']['N12'].value, PENDING)
        self.assertEqual(cache['Resumen']['D12'].value, PENDING)
        self.assertIn('COUNT(O13:O14)=2', book['Desarrollo']['N12'].value)
        self.assertIn('E13>0', book['Desarrollo']['K13'].value)

    def test_missing_source_and_cycle(self):
        rows = geometry()
        rows[1]['reference'] = make_reference(rows[0], 'm3')
        rows[1]['reference']['source'] = 'missing'
        _, cache = self.read(rows)
        self.assertEqual(cache['Desarrollo']['N12'].value, PENDING)
        rows[1]['reference']['source'] = rows[0]['id']
        with self.assertRaisesRegex(ValueError, 'circular'):
            export_workbook(self.path, 'Obra', rows, engine)

    def test_empty_item_zero_empty_workbook_and_headings(self):
        for rows in ([], [new_row('item', '01', 'VACÍA', 'm', 0)]):
            book, cache = self.read(rows)
            self.assertEqual(book.sheetnames, ['Desarrollo', 'Resumen'])
            if rows:
                self.assertEqual(cache['Resumen']['D12'].value, 0)
        rows = geometry()
        rows.insert(1, new_row('detail_group', description='VEREDAS', unit='m3', level=1))
        rows[2]['level'] = rows[3]['level'] = 2
        _, cache = self.read(rows)
        self.assertEqual(cache['Desarrollo']['N12'].value, 48)
        self.assertEqual(cache['Desarrollo']['B13'].value, 'VEREDAS')

    def test_formula_injection_and_item_leading_zeroes(self):
        rows = geometry()
        rows[0]['cells'][0] = '001.01'
        rows[0]['cells'][1] = '=HYPERLINK("https://invalid.example","X")'
        rows[1]['cells'][1] = '=2+2'
        book, _ = self.read(rows, '=DANGEROUS()')
        self.assertEqual(book['Desarrollo']['B12'].data_type, 's')
        self.assertEqual(book['Desarrollo']['B13'].data_type, 's')
        self.assertEqual(book['Resumen']['A12'].value, '001.01')
        self.assertEqual(book['Resumen']['A12'].data_type, 's')

    def test_unrepresentable_text_is_rejected_without_truncation(self):
        for text in ('a\x01b', 'X' * 32768):
            rows = geometry()
            rows[0]['cells'][1] = text
            with self.assertRaisesRegex(ValueError, 'texto demasiado largo'):
                export_workbook(self.path, 'Obra', rows, engine)
            self.assertFalse(self.path.exists())

    def test_long_text_wraps_and_multipage_is_not_fit_to_one_page(self):
        rows = geometry('m3', 100)
        rows[1]['cells'][1] = 'DESCRIPCIÓN EXTENSA ' * 10
        book, _ = self.read(rows)
        self.assertGreater(book['Desarrollo'].row_dimensions[13].height, 40)
        self.assertGreater(len(book['Desarrollo'].row_breaks.brk), 1)
        self.assertEqual(book['Desarrollo'].page_setup.fitToHeight, 0)

    def test_atomic_failure_preserves_destination_and_cleans_temporary(self):
        self.read(geometry())
        before = self.path.read_bytes()
        for target in ('metrado.excel_export._save_cached', 'metrado.excel_export.os.replace'):
            with patch(target, side_effect=OSError('bloqueado')):
                with self.assertRaises(OSError):
                    export_workbook(self.path, 'Otra', geometry(), engine)
            self.assertEqual(self.path.read_bytes(), before)
            self.assertEqual(list(self.path.parent.glob('.metrado-excel-*')), [])


class ExcelExportWindowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'out.xlsx'
        self.window = PlantillaWindow(engine, CatalogStore(Path(self.temp.name) / 'catalog.db'))

    def tearDown(self):
        with patch.object(self.window, '_can_discard', return_value=True):
            self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        self.temp.cleanup()

    def test_menu_and_palette_only(self):
        action = self.window.export_excel_action
        self.assertIn(action, self.window.keyboard.commands)
        self.assertNotIn(action, self.window.findChild(QToolBar, 'actionStrip').actions())
        self.assertTrue(any(a.menu().title() == 'Archivo' and action in a.menu().actions()
                            for a in self.window.menuBar().actions()))

    def test_cancel_preserves_document(self):
        before = deepcopy(self.window.model.rows)
        with patch('metrado.window.QFileDialog.getSaveFileName', return_value=('', '')):
            self.assertFalse(self.window.export_excel())
        self.assertEqual(before, self.window.model.rows)

    def test_export_preserves_history_path_dirty_selection_and_writes_all_items(self):
        window = self.window
        window.model.setData(window.model.index(0, 1), 'Título editado')
        before = (deepcopy(window.model.rows), window.model.undo_stack.index(), window._path,
                  window._revision, window._dirty, window.table.currentIndex())
        with patch('metrado.window.QFileDialog.getSaveFileName', return_value=(str(self.path), '')):
            self.assertTrue(window.export_excel())
        after = (window.model.rows, window.model.undo_stack.index(), window._path,
                 window._revision, window._dirty, window.table.currentIndex())
        self.assertEqual(before, after)
        with self.path.open('rb') as stream:
            book = load_workbook(stream)
            self.assertEqual(book['Resumen'].max_row, 23)
            book.close()

    def test_failure_restores_cursor_and_reports_error(self):
        with patch('metrado.window.QFileDialog.getSaveFileName', return_value=(str(self.path), '')), \
             patch('metrado.excel_export.export_workbook', side_effect=OSError('archivo ocupado')), \
             patch('metrado.window.QMessageBox.warning') as warning:
            self.assertFalse(self.window.export_excel())
            warning.assert_called_once()
        self.assertIsNone(QApplication.overrideCursor())

    def test_extension_added_and_overwrite_confirmation(self):
        with patch('metrado.window.QFileDialog.getSaveFileName', return_value=(str(self.path.with_suffix('')), '')):
            self.assertTrue(self.window.export_excel())
        self.assertTrue(self.path.exists())
        before = self.path.read_bytes()
        with patch('metrado.window.QFileDialog.getSaveFileName', return_value=(str(self.path.with_suffix('')), '')), \
             patch('metrado.window.QMessageBox.question', return_value=QMessageBox.No):
            self.assertFalse(self.window.export_excel())
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
