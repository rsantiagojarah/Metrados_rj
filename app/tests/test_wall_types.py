import json
import os
from pathlib import Path
import tempfile
import unittest
import math

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
import metrado._enlace as engine
from metrado.grid import SheetModel
from metrado.sheet import new_row
from metrado.identity import ensure_ids
from metrado.wall_types import WallType, WallTypeStore, default_wall_type, generate_wall_rows
from metrado.wall_dialog import WallGeneratorDialog

APP = QApplication.instance() or QApplication([])


class WallTypeTests(unittest.TestCase):
    def test_store_round_trip_and_json_transfer(self):
        with tempfile.TemporaryDirectory() as folder:
            store = WallTypeStore(Path(folder) / 'muros.sqlite3')
            wall = default_wall_type()
            wall.name = 'Muro con dentellón'
            wall.dentellon = True
            wall.cut_left = True
            wall.distributions = [item for item in wall.distributions if item['component'] != 'refuerzo_cortado']
            store.save(wall)
            self.assertEqual(store.read()[0].name, 'Muro con dentellón')
            path = Path(folder) / 'tipos.json'
            store.export_json(path)
            other = WallTypeStore(Path(folder) / 'other.sqlite3')
            other.import_json(path)
            self.assertEqual(other.read()[0].name, 'Muro con dentellón')

    def test_generate_keeps_fixed_cut_and_changes_vertical_horizontal_with_height(self):
        wall = default_wall_type()
        wall.name = 'Prueba'
        wall.cut_left = True
        wall.distributions.append(dict(component='refuerzo_cortado', side='izquierda',
                                       diameter='5/8"', spacing=.25, fixed_length=4.6))
        low = generate_wall_rows(wall, 10, 5)
        high = generate_wall_rows(wall, 10, 8)
        low_vertical = next(row for row in low if row[0] == 'kg' and 'Pantalla · vertical' in row[1]['cells'][1])
        high_vertical = next(row for row in high if row[0] == 'kg' and 'Pantalla · vertical' in row[1]['cells'][1])
        self.assertAlmostEqual(float(low_vertical[1]['cells'][4]), math.hypot(6.2, .75 * 6.2 / 5))
        self.assertAlmostEqual(float(high_vertical[1]['cells'][4]), math.hypot(9.2, .75 * 9.2 / 8))
        low_cut = next(row for row in low if row[0] == 'kg' and 'refuerzo cortado' in row[1]['cells'][1])
        high_cut = next(row for row in high if row[0] == 'kg' and 'refuerzo cortado' in row[1]['cells'][1])
        self.assertEqual(low_cut[1]['cells'][4], high_cut[1]['cells'][4])
        self.assertAlmostEqual(float(low_cut[1]['cells'][4]), math.hypot(5.8, .75 * 5.8 / 8.3))
        low_horizontal = next(row for row in low if row[0] == 'kg' and 'Pantalla · horizontal' in row[1]['cells'][1])
        high_horizontal = next(row for row in high if row[0] == 'kg' and 'Pantalla · horizontal' in row[1]['cells'][1])
        self.assertNotEqual(low_horizontal[1]['cells'][3], high_horizontal[1]['cells'][3])

    def test_cut_checkbox_generates_fixed_reinforcement(self):
        wall = default_wall_type()
        wall.cut_left = True
        rows = generate_wall_rows(wall, 10, 8)
        cut = [row for row in rows if row[0] == 'kg' and 'refuerzo cortado' in row[1]['cells'][1]]
        self.assertEqual(len(cut), 1)
        self.assertAlmostEqual(float(cut[0][1]['cells'][4]), math.hypot(5.8, .75 * 5.8 / 8.3))

    def test_generator_dialog_only_offers_existing_partidas(self):
        rows = [new_row('item', unit='m3', code='01', description='Concreto'),
                new_row('item', unit='m2', code='02', description='Encofrado'),
                new_row('item', unit='kg', code='03', description='Acero')]
        ensure_ids(rows)
        with tempfile.TemporaryDirectory() as folder:
            store = WallTypeStore(Path(folder) / 'muros.sqlite3')
            dialog = WallGeneratorDialog(store, rows)
            self.assertEqual(dialog.destinations['m3'].count(), 2)
            self.assertEqual(dialog.destinations['m2'].count(), 2)
            self.assertEqual(dialog.destinations['kg'].count(), 2)
            wall, length, height = dialog.configuration()
            self.assertEqual((wall.name, length, height), ('Muro modelo', 1, None))
            dialog.deleteLater()


if __name__ == '__main__':
    unittest.main()
