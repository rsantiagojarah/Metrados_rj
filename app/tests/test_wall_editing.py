"""Wall editing, independent snapshots, storage and friendly input."""
from copy import deepcopy
from dataclasses import asdict
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication, QDialog, QPlainTextEdit, QDialogButtonBox
import metrado._enlace as engine
from metrado.grid import SheetModel
from metrado.identity import ensure_ids
from metrado.sheet import new_row, write_project, read_project, calculate, RESULT_COLUMN
from metrado.database import write_database, read_database, SCHEMA_VERSION
from metrado.hierarchy import Outline
from metrado.wall_types import default_wall_type, WallTypeStore, WallType, generate_wall_rows
from metrado.wall_instances import apply_wall, selected_wall
from metrado.wall_dialog import WallTypeDialog, WallGeneratorDialog
from metrado.clipboard import insert_rows
from metrado.window import PlantillaWindow
from metrado.steel_store import CatalogStore

APP = QApplication.instance() or QApplication([])


def project():
    rows = [new_row('chapter', '01', 'Estructuras', level=0),
            new_row('chapter', '01.01', 'Muros', level=1)]
    for unit in ('m3', 'm2', 'kg'):
        rows.append(new_row('item', description=unit, unit=unit, level=2))
    ensure_ids(rows)
    return rows


def destinations(rows):
    return {row['cells'][2]: row['id'] for row in rows if row['kind'] == 'item'}


def members(rows, name):
    return [row for row in rows if row.get('wall_generated', {}).get('name') == name]


class WallEditingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.wall = default_wall_type()
        self.wall.cut_left = True
        self.rows = project()
        self.dest = destinations(self.rows)
        self.generated = apply_wall(self.rows, self.wall, 10, 6, self.dest, 'Tramo A')

    def tearDown(self):
        self.temp.cleanup()

    def test_update_same_type_only_touches_selected_instance_and_undoes(self):
        rows = apply_wall(self.generated, self.wall, 10, 6, self.dest, 'Tramo B')
        model = SheetModel(engine, rows)
        original = deepcopy(model.rows)
        a = members(rows, 'Tramo A')
        identity = a[0]['wall_generated']['instance_id']
        updated = apply_wall(model.rows, self.wall, 12, 8, self.dest, 'Tramo A', identity)
        model.replace(updated, 'editar muro')
        self.assertEqual(members(model.rows, 'Tramo B'), members(original, 'Tramo B'))
        self.assertEqual(len(members(model.rows, 'Tramo A')), len(a))
        self.assertEqual({r['id'] for r in members(model.rows, 'Tramo A')}, {r['id'] for r in a})
        self.assertEqual(model.errors, {})
        Outline(model.rows, strict=True)
        self.assertTrue(all(r['level'] == 3 for r in members(model.rows, 'Tramo A')))
        model.undo_stack.undo()
        self.assertEqual(model.rows, original)
        model.undo_stack.redo()
        self.assertEqual(len(model.rows), len(original))

    def test_height_does_not_change_footing_and_cut_length(self):
        low = generate_wall_rows(self.wall, 10, 6)
        high = generate_wall_rows(self.wall, 10, 8)
        footing = lambda entries: [x for x in entries if
            (x[0] == 'kg' and 'Zapata' in x[1]['cells'][1]) or
            (x[0] != 'kg' and 'zapata' in x[1])]
        self.assertEqual(footing(low), footing(high))
        for entries in (low, high):
            cut = next(x[1] for x in entries if x[0] == 'kg' and 'refuerzo cortado' in x[1]['cells'][1])
            self.assertAlmostEqual(float(cut['cells'][4]), (5.8 ** 2 + (.75 * 5.8 / 8.3) ** 2) ** .5)
        with self.assertRaisesRegex(ValueError, 'cortado'):
            generate_wall_rows(self.wall, 10, 2)

    def test_concrete_formwork_round_to_two_decimals_without_rounding_steel(self):
        wall = default_wall_type()
        wall.bottom_thickness = 1.0
        generated = apply_wall(self.rows, wall, 2.675, 8, self.dest, 'Redondeo')
        formwork = next(r for r in generated if 'encofrado de pantalla izquierda' in r['cells'][1])
        # hypot(8, .5) = 8.01560977094...; both the cell and calculation use 8.02.
        self.assertEqual(formwork['cells'][4:6], ['2.68', '8.02'])
        concrete = next(r for r in generated if 'concreto de pantalla' in r['cells'][1])
        self.assertEqual(concrete['cells'][4:7], ['2.68', '0.75', '8.00'])
        values, errors = calculate(generated, engine)
        self.assertEqual(errors, {})
        self.assertAlmostEqual(values[(generated.index(formwork), RESULT_COLUMN['m2'])], 2.68 * 8.02)
        self.assertAlmostEqual(values[(generated.index(concrete), RESULT_COLUMN['m3'])], 16.08)
        original_steel = [row[1]['cells'][3:] for row in generate_wall_rows(wall, 2.675, 8) if row[0] == 'kg']
        sheet_steel = [r['cells'][3:] for r in generated if r['kind'] == 'detail' and r['cells'][2] == 'kg']
        self.assertEqual(sheet_steel, original_steel)
        config = formwork['wall_generated']
        self.assertEqual(config['length'], 2.675)
        updated = apply_wall(generated, wall, 10.005, 8, self.dest, 'Redondeo', config['instance_id'])
        updated_formwork = next(r for r in updated if r['id'] == formwork['id'])
        self.assertEqual(updated_formwork['cells'][4:6], ['10.01', '8.02'])

    def test_sqlite_json_snapshot_and_edit_after_catalog_change(self):
        path = self.root / 'obra.db'
        rev = write_database(path, 'Obra', self.generated)
        title, rows, loaded_rev = read_database(path)
        self.assertEqual((title, loaded_rev), ('Obra', rev))
        self.assertEqual(rows, self.generated)
        self.assertEqual(write_database(path, 'Obra', rows, rev), rev)
        store = WallTypeStore(self.root / 'types.db')
        changed = default_wall_type()
        changed.screen_height = 20
        store.save(changed)
        config = selected_wall(rows, next(i for i, r in enumerate(rows) if 'wall_generated' in r))
        dialog = WallGeneratorDialog(store, rows, instance=config)
        self.assertEqual(dialog.values[0].screen_height, 8.3)
        self.assertFalse(dialog.wall.isEnabled())
        dialog.height.setText('7+1')
        wall, length, height = dialog.configuration()
        updated = apply_wall(rows, wall, length, height, dialog.selected_destinations(), 'Tramo A', config['instance_id'])
        self.assertEqual(len(rows), len(updated))
        json_path = self.root / 'obra.json'
        write_project(json_path, 'Obra', updated)
        reopened = read_project(json_path)[1]
        self.assertEqual(reopened, updated)
        self.assertEqual(calculate(reopened, engine)[1], {})

    def test_migrate_previous_database_and_keep_every_quantity(self):
        path = self.root / 'old.db'
        write_database(path, 'Obra', self.rows)
        with closing(sqlite3.connect(path)) as connection, connection:
            connection.execute('DROP TABLE wall_details')
            connection.execute('PRAGMA user_version=6')
        self.assertEqual(read_database(path)[1], self.rows)
        write_database(path, 'Obra', self.generated)
        self.assertEqual(read_database(path)[1], self.generated)
        with closing(sqlite3.connect(path)) as connection:
            self.assertEqual(connection.execute('PRAGMA user_version').fetchone()[0], SCHEMA_VERSION)
            self.assertEqual(connection.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_missing_destination_rejects_without_mutation(self):
        original = deepcopy(self.generated)
        identity = members(original, 'Tramo A')[0]['wall_generated']['instance_id']
        with self.assertRaises(ValueError):
            apply_wall(self.generated, self.wall, 10, 8, {'m3': 'missing'}, 'Tramo A', identity)
        self.assertEqual(self.generated, original)

    def test_changed_destination_only_replaces_tramo(self):
        rows = deepcopy(self.generated)
        other = new_row('item', description='Otro concreto', unit='m3', level=2)
        rows.append(other)
        ensure_ids(rows)
        mapping = dict(self.dest, m3=other['id'])
        identity = members(rows, 'Tramo A')[0]['wall_generated']['instance_id']
        updated = apply_wall(rows, self.wall, 10, 6, mapping, 'Tramo A', identity)
        outline = Outline(updated, strict=True)
        concrete = [i for i, r in enumerate(updated) if r['kind'] == 'detail' and r['cells'][2] == 'm3']
        self.assertTrue(all(updated[outline.owners[i]]['id'] == other['id'] for i in concrete))

    def test_copied_details_are_not_replaced_with_the_source_wall(self):
        one = next(r for r in self.generated if r['kind'] == 'detail' and r['cells'][2] == 'm3')
        block = [dict(deepcopy(one), level=0)]
        index = next(i for i, r in enumerate(self.generated) if r['id'] == self.dest['m3'])
        rows, pos = insert_rows(self.generated, index, block)
        self.assertNotIn('wall_generated', rows[pos])
        copied_id = rows[pos]['id']
        identity = one['wall_generated']['instance_id']
        updated = apply_wall(rows, self.wall, 12, 8, self.dest, 'Tramo A', identity)
        self.assertIn(copied_id, {r['id'] for r in updated})

    def test_legacy_detail_is_preserved_without_guessing_its_group(self):
        row = new_row('detail', unit='m3')
        row['wall_generated'] = dict(type='Muro', component='pantalla', length=10, height=6)
        with self.assertRaisesRegex(ValueError, 'versión anterior'):
            selected_wall([row], 0)

    def test_invalid_input_rejected_before_changes(self):
        for bad in (float('nan'), float('inf'), 0, -1):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                apply_wall(self.rows, self.wall, bad, 6, self.dest, 'X')
        wall = deepcopy(self.wall)
        wall.distributions[0]['component'] = 'unknown'
        with self.assertRaises(ValueError):
            generate_wall_rows(wall, 10)

    def test_friendly_form_preserves_values_and_supports_arithmetic(self):
        store = WallTypeStore(self.root / 'types.db')
        store.save(self.wall)
        dialog = WallTypeDialog(store)
        self.assertEqual(dialog.findChildren(QPlainTextEdit), [])
        # Positions have a fixed order; compare takeoffs rather than list order.
        def quantities(wall):
            return sorted(str(row) for row in generate_wall_rows(wall, 10))
        self.assertEqual(quantities(dialog.read_form()), quantities(self.wall))
        table = dialog.distributions
        self.assertEqual(table.rowCount(), 11)
        table.cellWidget(0, 2).setText('1/5')
        diameter = table.cellWidget(0, 1)
        diameter.setCurrentIndex(diameter.findData('1/2"'))
        form = dialog.read_form()
        self.assertEqual(form.distributions[0]['spacing'], 0.2)
        self.assertEqual(form.distributions[0]['diameter'], '1/2"')
        dialog.accept()
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(store.read()[0].distributions[0]['diameter'], '1/2"')

    def test_cancel_duplicate_creates_no_catalog_entries(self):
        store = WallTypeStore(self.root / 'types.db')
        store.save(self.wall)
        before = store.read()
        dialog = WallTypeDialog(store)
        dialog.duplicate_type()
        dialog.reject()
        self.assertEqual(store.read(), before)

    def test_distribution_positions_are_fixed_and_optional(self):
        from PySide6.QtWidgets import QPushButton
        dialog = WallTypeDialog(WallTypeStore(self.root / 'types.db'))
        table = dialog.distributions
        self.assertEqual(table.rowCount(), 11)
        self.assertIsNone(table.cellWidget(0, 0))
        self.assertIn('vertical izquierda', table.item(0, 0).text())
        self.assertIsNone(table.cellWidget(0, 3))
        self.assertTrue(table.cellWidget(4, 3).isEnabled())
        forbidden = {'Agregar distribución', 'Duplicar fila', 'Quitar fila'}
        self.assertFalse(forbidden.intersection(b.text() for b in dialog.findChildren(QPushButton)))
        self.assertFalse(table.cellWidget(9, 1).isEnabled())
        dialog.dentellon.setChecked(True)
        self.assertTrue(table.cellWidget(9, 1).isEnabled())

    def test_empty_and_partial_positions_omit_steel_without_errors(self):
        store = WallTypeStore(self.root / 'types.db')
        dialog = WallTypeDialog(store)
        table = dialog.distributions
        for r in range(table.rowCount()):
            # Both ways of omitting a position are accepted.
            if r % 2:
                table.cellWidget(r, 1).setCurrentIndex(0)
            else:
                table.cellWidget(r, 2).clear()
        # Cut has diameter and spacing but no length: also omitted.
        table.cellWidget(4, 1).setCurrentIndex(1)
        table.cellWidget(4, 2).setText('0.2')
        table.cellWidget(4, 3).clear()
        wall = dialog.read_form()
        self.assertEqual(wall.distributions, [])
        self.assertFalse(wall.cut_left)
        self.assertFalse(any(r[0] == 'kg' for r in generate_wall_rows(wall, 10)))
        dialog.accept()
        self.assertEqual(dialog.result(), QDialog.Accepted)
        reopened = WallTypeDialog(store)
        self.assertEqual(reopened.read_form().distributions, [])
        self.assertFalse(reopened.error.text())

    def test_preview_updates_geometry_and_steel_without_catalog_writes(self):
        store = WallTypeStore(self.root / 'types.db')
        dialog = WallTypeDialog(store)
        dialog.fields['screen_height'].setText('6+2')
        self.assertEqual(dialog.section.wall.screen_height, 8)
        dialog.fields['bottom_thickness'].setText('0.5')
        self.assertEqual(dialog.section.wall.bottom_thickness, .5)
        dialog.fields['screen_height'].clear()
        self.assertTrue(dialog.section.pending)
        self.assertEqual(dialog.section.wall.screen_height, 8)
        dialog.fields['screen_height'].setText('7')
        self.assertFalse(dialog.section.pending)
        dialog.tabs.setCurrentIndex(1)
        self.assertTrue(dialog.section.steel)
        dialog.distributions.cellWidget(0, 2).clear()
        self.assertNotIn(('pantalla_vertical', 'izquierda'),
                         {(d['component'], d['side']) for d in dialog.section.wall.distributions})
        dialog.dentellon.setChecked(True)
        self.assertTrue(dialog.section.wall.dentellon)
        self.assertFalse(store.path.exists())
        dialog.reject()

    def test_reference_key_shape_and_legacy_rectangular_geometry(self):
        wall = default_wall_type()
        wall.dentellon = True
        def concrete(w):
            return next(row[2] for row in generate_wall_rows(w, 10)
                        if row[0] == 'm3' and row[-1] == 'dentellon')
        self.assertEqual(concrete(wall), [10, .8, .7])
        transverse = next(row[1] for row in generate_wall_rows(wall, 10)
                          if row[0] == 'kg' and 'Dentellón · transversal' in row[1]['cells'][1])
        self.assertAlmostEqual(float(transverse['cells'][4]), (1.9 ** 2 + (.4 * 1.9 / .7) ** 2) ** .5 + .6 + 1.9)
        longitudinal = next(row[1] for row in generate_wall_rows(wall, 10)
                            if row[0] == 'kg' and 'Dentellón · longitudinal' in row[1]['cells'][1])
        self.assertEqual(int(longitudinal['cells'][3]), 20)
        payload = asdict(wall)
        del payload['dentellon_slope']
        legacy = WallType.from_dict(payload)
        self.assertEqual(concrete(legacy), [10, .6, .7])
        legacy.dentellon_slope = -1
        with self.assertRaises(ValueError):
            legacy.validate()

    def test_invalid_import_is_atomic_and_copies_get_unique_names(self):
        store = WallTypeStore(self.root / 'types.db')
        store.save(self.wall)
        path = self.root / 'types.json'
        path.write_text(json.dumps([asdict(self.wall), {'name': 'bad', 'screen_height': -2}]), encoding='utf-8')
        with self.assertRaises(ValueError):
            store.import_json(path)
        self.assertEqual(len(store.read()), 1)
        path.write_text(json.dumps([asdict(self.wall)]), encoding='utf-8')
        store.import_json(path)
        store.import_json(path)
        self.assertEqual(len({w.name for w in store.read()}), 3)

    def test_no_destination_disables_generation(self):
        dialog = WallGeneratorDialog(WallTypeStore(self.root / 'types.db'), self.rows)
        for combo in dialog.destinations.values():
            combo.setCurrentIndex(0)
        self.assertFalse(dialog.buttons.button(QDialogButtonBox.Ok).isEnabled())

    def test_window_generates_and_edits_selected_instance(self):
        window = PlantillaWindow(engine, catalog_store=CatalogStore(self.root / 'steel.db'))
        window.model.replace(self.rows)
        def fill(dialog):
            dialog.length.setText('12' if dialog.instance else '10')
            dialog.height.setText('8' if dialog.instance else '6')
            dialog.tramo_name.setText('Tramo integrado')
            return QDialog.Accepted
        try:
            with patch.object(WallGeneratorDialog, 'exec', fill), patch('metrado.window.QMessageBox.warning') as warning:
                window.generate_wall()
                generated = members(window.model.rows, 'Tramo integrado')
                self.assertTrue(generated)
                index = next(i for i, r in enumerate(window.model.rows) if 'wall_generated' in r)
                window._select(index)
                window.edit_wall()
                edited = members(window.model.rows, 'Tramo integrado')
                self.assertEqual(len(edited), len(generated))
                self.assertTrue(all(row['wall_generated']['length'] == 12 for row in edited))
                self.assertEqual(window.model.errors, {})
                warning.assert_not_called()
                window.model.undo_stack.undo()
                self.assertTrue(all(row['wall_generated']['length'] == 10
                                    for row in members(window.model.rows, 'Tramo integrado')))
        finally:
            window._dirty = False
            window.model.undo_stack.setClean()
            window.close()
            window.deleteLater()
