"""Automatic bar-count/diameter suffix, scoped to steel measurements only."""
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

import metrado._enlace as engine
from metrado.clipboard import cell_text, decode_rows, encode_rows, insert_rows
from metrado.database import open_document, read_database, write_database
from metrado.grid import SheetModel
from metrado.sheet import calculate, new_row, read_project, steel_detail, write_project

APP = QApplication.instance() or QApplication([])


def steel_model(description='VERTICAL INTERIOR', bars=53, diameter='1"'):
    return SheetModel(engine, [new_row('item', description='ACERO', unit='kg', level=0),
                              dict(steel_detail(description, 2, 10.85, 0.61, 1.15, diameter, bars), level=1)])


class SteelSuffixTests(unittest.TestCase):
    def test_suffix_added_and_quantity_excludes_similar_elements(self):
        model = steel_model()
        self.assertEqual(model.rows[1]['cells'][1], 'VERTICAL INTERIOR 53 Ø1"')
        self.assertEqual(model.data(model.index(1, 1), Qt.EditRole), 'VERTICAL INTERIOR 53 Ø1"')
        self.assertTrue(model.data(model.index(1, 1)).endswith('53 Ø1"'))
        model.setData(model.index(1, 3), '4')
        self.assertEqual(model.rows[1]['cells'][1], 'VERTICAL INTERIOR 53 Ø1"')

    def test_annotations_in_middle_and_duplicates_move_to_one_suffix(self):
        for description in ('VERTICAL 53 Ø1" INTERIOR', 'VERTICAL INTERIOR 53 Ø1" 53 Ø1"',
                            'VERTICAL Ø1" INTERIOR'):
            model = steel_model(description)
            self.assertEqual(model.rows[1]['cells'][1], 'VERTICAL INTERIOR 53 Ø1"')

    def test_editing_plain_description_keeps_suffix(self):
        model = steel_model()
        model.setData(model.index(1, 1), 'NUEVA DESCRIPCIÓN')
        self.assertEqual(model.rows[1]['cells'][1], 'NUEVA DESCRIPCIÓN 53 Ø1"')
        model.setData(model.index(1, 1), '')
        self.assertEqual(model.rows[1]['cells'][1], '53 Ø1"')

    def test_bar_count_and_diameter_edits_keep_suffix_current(self):
        model = steel_model()
        model.setData(model.index(1, 7), '66')
        self.assertEqual(model.rows[1]['cells'][1], 'VERTICAL INTERIOR 66 Ø1"')
        model.setData(model.index(1, 9), '3/4"')
        self.assertEqual(model.rows[1]['cells'][1], 'VERTICAL INTERIOR 66 Ø3/4"')

    def test_manually_entered_spec_updates_fields_and_moves_to_end(self):
        model = steel_model()
        model.setData(model.index(1, 1), 'TRANSVERSAL 44 Ø3/4" EXTERIOR')
        self.assertEqual(model.rows[1]['cells'][1], 'TRANSVERSAL EXTERIOR 44 Ø3/4"')
        self.assertEqual(model.data(model.index(1, 7)), '44')
        self.assertEqual(model.rows[1]['cells'][7], '3/4"')

    def test_new_detail_uses_pending_markers_without_inventing_values(self):
        model = SheetModel(engine, [new_row('item', unit='kg'), new_row('detail', description='Nuevo detalle', unit='kg')])
        self.assertEqual(model.rows[1]['cells'][1], 'Nuevo detalle ? Ø?')
        model.setData(model.index(1, 9), '1"')
        self.assertEqual(model.rows[1]['cells'][1], 'Nuevo detalle ? Ø1"')
        model.setData(model.index(1, 7), '53')
        self.assertEqual(model.rows[1]['cells'][1], 'Nuevo detalle 53 Ø1"')
        self.assertEqual(model.rows[1]['cells'][4], '')

    def test_invalid_legacy_diameter_does_not_accumulate_suffixes(self):
        model = steel_model(diameter='pendiente')
        model.setData(model.index(1, 3), '3')
        model.setData(model.index(1, 4), '10')
        self.assertEqual(model.rows[1]['cells'][1], 'VERTICAL INTERIOR 53 Ø?')
        self.assertEqual(model.rows[1]['cells'][7], 'pendiente')

    def test_removing_only_generated_suffix_is_a_noop(self):
        model = steel_model()
        self.assertFalse(model.setData(model.index(1, 1), 'VERTICAL INTERIOR'))
        self.assertEqual(model.undo_stack.count(), 0)
        self.assertEqual(model.rows[1]['cells'][1], 'VERTICAL INTERIOR 53 Ø1"')

    def test_legacy_repetitions_survive_prose_edit_and_new_suffix_means_total(self):
        rows = steel_model().rows
        rows[1]['cells'][9] = '2'
        before = calculate(rows, engine)
        model = SheetModel(engine, rows)
        self.assertEqual(model.rows[1]['cells'][1], 'VERTICAL INTERIOR 106 Ø1"')
        model.setData(model.index(1, 1), 'RENOMBRADO 106 Ø1"')
        self.assertEqual(model.rows[1]['cells'][9:11], ['2', '53'])
        self.assertEqual((model.values, model.errors), before)
        model.setData(model.index(1, 1), 'RENOMBRADO 110 Ø1"')
        self.assertEqual(model.rows[1]['cells'][9:11], ['1', '110'])
        self.assertEqual(model.data(model.index(1, 7)), '110')

    def test_metric_mixed_fraction_and_decimal_quantity(self):
        model = steel_model()
        for specification, suffix in (('12,5 Ø8mm', '12.5 Ø8mm'), ('7 Ø1 3/8"', '7 Ø1 3/8"'),
                                      ('9 Ø3/8', '9 Ø3/8"')):
            model.setData(model.index(1, 1), 'BARRAS ' + specification)
            self.assertEqual(model.rows[1]['cells'][1], 'BARRAS ' + suffix)
        model.setData(model.index(1, 7), '1000000')
        model.setData(model.index(1, 9), '1"')
        self.assertEqual(model.rows[1]['cells'][1], 'BARRAS 1e+06 Ø1"')

    def test_nonsteel_and_titles_are_unchanged(self):
        rows = [new_row('chapter', description='TÍTULO 53 Ø1"', level=0),
                new_row('item', description='PARTIDA ACERO', unit='kg', level=1),
                new_row('detail_group', description='GRUPO 53 Ø1"', unit='kg', level=2),
                dict(steel_detail('BARRAS', 1, 1, 0, 0, '1"', 53), level=3),
                new_row('item', description='CONCRETO', unit='m3', level=1),
                new_row('detail', description='DETALLE 53 Ø1"', unit='m3', level=2)]
        original = [row['cells'][1] for row in rows]
        model = SheetModel(engine, rows)
        for index in (0, 1, 2, 4, 5):
            self.assertEqual(model.rows[index]['cells'][1], original[index])
        self.assertEqual(model.rows[3]['cells'][1], 'BARRAS 53 Ø1"')

    def test_unit_change_removes_suffix_and_undo_restores_it(self):
        model = steel_model()
        before = deepcopy(model.rows)
        model.setData(model.index(0, 2), 'm3')
        self.assertEqual(model.rows[1]['cells'][1], 'VERTICAL INTERIOR')
        model.undo_stack.undo()
        self.assertEqual(model.rows, before)
        model.undo_stack.redo()
        model.setData(model.index(0, 2), 'kg')
        self.assertEqual(model.rows[1]['cells'][1], 'VERTICAL INTERIOR ? Ø?')

    def test_suffix_changes_are_part_of_same_undo_command(self):
        model = steel_model()
        before = deepcopy(model.rows)
        model.setData(model.index(1, 7), '66')
        self.assertEqual(model.undo_stack.count(), 1)
        model.undo_stack.undo()
        self.assertEqual(model.rows, before)
        model.undo_stack.redo()
        self.assertEqual(model.rows[1]['cells'][1], 'VERTICAL INTERIOR 66 Ø1"')

    def test_direct_quantity_uses_visible_repetitions(self):
        model = steel_model()
        model.set_direct(1, '50')
        self.assertEqual(model.rows[1]['cells'][1], 'VERTICAL INTERIOR 1 Ø1"')
        model.setData(model.index(1, 7), '4')
        self.assertEqual(model.rows[1]['cells'][1], 'VERTICAL INTERIOR 4 Ø1"')
        model.setData(model.index(1, 1), 'DIRECTO 6 Ø1"')
        self.assertEqual(model.rows[1]['cells'][9], '6')
        self.assertEqual(model.rows[1]['direct'], '50')

    def test_paste_rectangle_final_fields_win_and_undo_is_atomic(self):
        model = steel_model()
        before = deepcopy(model.rows)
        matrix = [[cell_text(model, 1, c) for c in range(1, 10)]]
        matrix[0][0], matrix[0][6], matrix[0][8] = 'BARRAS 44 Ø1"', '66', '1/2"'
        model.paste_cells(1, 1, matrix)
        self.assertEqual(model.rows[1]['cells'][1], 'BARRAS 66 Ø1/2"')
        self.assertEqual(model.undo_stack.count(), 1)
        model.undo_stack.undo()
        self.assertEqual(model.rows, before)

    def test_clipboard_blocks_and_plain_text_contain_current_suffix(self):
        model = steel_model()
        model.setData(model.index(1, 7), '66')
        mime = encode_rows(model, [1])
        self.assertIn('VERTICAL INTERIOR 66 Ø1"'.replace('"', '""'), mime.text())
        block = decode_rows(mime.data('application/x-metrado-rows+json'))
        rows, position = insert_rows(model.rows, 0, block)
        model.replace(rows)
        self.assertEqual(model.rows[position]['cells'][1], 'VERTICAL INTERIOR 66 Ø1"')

    def test_sqlite_and_json_store_suffix_and_legacy_import_normalizes_without_changing_source(self):
        model = steel_model()
        model.setData(model.index(1, 9), '1/2"')
        with tempfile.TemporaryDirectory() as folder:
            db, json = Path(folder) / 'obra.db', Path(folder) / 'obra.json'
            write_database(db, 'Obra', model.rows)
            write_project(json, 'Obra', model.rows)
            for rows in (read_database(db)[1], read_project(json)[1]):
                self.assertEqual(rows[1]['cells'][1], 'VERTICAL INTERIOR 53 Ø1/2"')
            model.rows[1]['cells'][1] = 'ANTERIOR'
            write_project(json, 'Anterior', model.rows)
            original = json.read_bytes()
            title, rows, revision = open_document(json)
            loaded = SheetModel(engine, rows)
            self.assertEqual(loaded.rows[1]['cells'][1], 'ANTERIOR 53 Ø1/2"')
            self.assertEqual(json.read_bytes(), original)


if __name__ == '__main__':
    unittest.main(verbosity=2)
