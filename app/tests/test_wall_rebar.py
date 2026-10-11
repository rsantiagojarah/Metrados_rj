"""End-to-end wall reinforcement extents and editable hooks."""
from copy import deepcopy
from dataclasses import asdict
import math
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from metrado.wall_types import default_wall_type, WallType, WallTypeStore, generate_wall_rows
from metrado.wall_rebar import reinforcement, position_key, spaced_points
from metrado.wall_dialog import WallTypeDialog
from metrado.wall_instances import apply_wall, selected_wall
from metrado.sheet import new_row
from metrado.identity import ensure_ids
from metrado.database import write_database, read_database

APP=QApplication.instance() or QApplication([])


def entry(wall, component, side='izquierda'):
    return next(d for d in wall.distributions if (d['component'],d['side']) == (component,side))


class WallRebarTests(unittest.TestCase):
    def test_footing_wings_allow_zero_but_not_negative(self):
        wall=default_wall_type()
        wall.footing_left=0
        wall.footing_right=0
        wall.validate()
        rows=generate_wall_rows(wall,10)
        footing=next(row for row in rows if row[0]=='m3' and 'concreto de zapata' in row[1])
        self.assertEqual(footing[2],[10.0,1.25,1.2])
        self.assertTrue(any(row[0]=='kg' for row in rows))
        wall.footing_left=-.01
        with self.assertRaises(ValueError):
            wall.validate()

    def test_zero_wings_are_accepted_from_the_geometry_form(self):
        with tempfile.TemporaryDirectory() as folder:
            dialog=WallTypeDialog(WallTypeStore(Path(folder)/'types.db'))
            dialog.fields['footing_left'].setText('1-1')
            dialog.fields['footing_right'].setText('0')
            wall=dialog.read_form()
            self.assertEqual(wall.footing_left,0)
            self.assertEqual(wall.footing_right,0)
            dialog.close()

    def test_screen_bars_and_horizontal_distribution_reach_footing_bottom(self):
        wall=default_wall_type()
        wall.horizontal_in_footing=True
        left=reinforcement(wall,entry(wall,'pantalla_vertical'),10)
        right=reinforcement(wall,entry(wall,'pantalla_vertical','derecha'),10)
        self.assertEqual(left.body[0],(3.95,8.3))
        self.assertAlmostEqual(left.body[-1][0],3.2-.75*1.2/8.3)
        self.assertEqual(left.body[-1][1],-1.2)
        self.assertEqual(right.body,((4.45,8.3),(4.45,-1.2)))
        self.assertAlmostEqual(right.body_length,9.5)
        self.assertAlmostEqual(left.body_length,math.hypot(9.5,.75*9.5/8.3))
        horizontal=reinforcement(wall,entry(wall,'pantalla_horizontal','derecha'),10)
        self.assertEqual(horizontal.distribution,right.body)
        self.assertEqual(horizontal.body_length,10)
        points=spaced_points(horizontal.distribution,.25)
        self.assertEqual(len(points),39)
        self.assertEqual(points[0],(4.45,8.3))
        self.assertAlmostEqual(points[-1][1],-1.2)
        # Zero taper still includes the entire footing depth.
        wall.bottom_thickness=wall.top_thickness
        self.assertAlmostEqual(reinforcement(wall,entry(wall,'pantalla_vertical'),10).body_length,9.5)

    def test_horizontal_footing_option_defaults_off_and_only_changes_horizontal_count(self):
        wall=default_wall_type()
        self.assertFalse(wall.horizontal_in_footing)
        payload=asdict(wall)
        del payload['horizontal_in_footing']
        self.assertFalse(WallType.from_dict(payload).horizontal_in_footing)
        def horizontal_counts(rows):
            return [int(r[1]['cells'][3]) for r in rows
                    if r[0]=='kg' and 'Pantalla · horizontal' in r[1]['cells'][1]]
        def other_rows(rows):
            return [r for r in rows if not (r[0]=='kg' and 'Pantalla · horizontal' in r[1]['cells'][1])]
        without=generate_wall_rows(wall,10)
        self.assertEqual(horizontal_counts(without),[35,35])
        for side in ('izquierda','derecha'):
            self.assertEqual(reinforcement(wall,entry(wall,'pantalla_horizontal',side)).distribution[-1][1],0)
        wall.horizontal_in_footing=True
        included=generate_wall_rows(wall,10)
        self.assertEqual(horizontal_counts(included),[40,39])
        self.assertEqual(other_rows(without),other_rows(included))
        for side in ('izquierda','derecha'):
            self.assertEqual(reinforcement(wall,entry(wall,'pantalla_horizontal',side)).distribution[-1][1],-1.2)
        self.assertEqual(horizontal_counts(generate_wall_rows(wall,10,6)),[31,30])
        wall.horizontal_in_footing=False
        self.assertEqual(horizontal_counts(generate_wall_rows(wall,10,6)),[26,25])
        wall.horizontal_in_footing='false'
        with self.assertRaises(ValueError):
            wall.validate()

    def test_horizontal_checkbox_preview_persistence_and_new_type_default(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            store=WallTypeStore(root/'types.db')
            dialog=WallTypeDialog(store)
            self.assertFalse(dialog.horizontal_in_footing.isChecked())
            dialog.horizontal_in_footing.setChecked(True)
            self.assertTrue(dialog.section.wall.horizontal_in_footing)
            dialog.accept()
            reopened=WallTypeDialog(store)
            self.assertTrue(reopened.horizontal_in_footing.isChecked())
            rows=[new_row('item',unit='kg',description='Acero')]
            ensure_ids(rows)
            generated=apply_wall(rows,store.read()[0],10,None,{'kg':rows[0]['id']},'A')
            write_database(root/'obra.db','Obra',generated)
            self.assertTrue(selected_wall(read_database(root/'obra.db')[1],1)['wall']['horizontal_in_footing'])
            reopened.new_type()
            self.assertFalse(reopened.horizontal_in_footing.isChecked())
            reopened.reject()

    def test_footing_and_key_extents_include_full_embedment_and_bends(self):
        wall=default_wall_type()
        wall.dentellon=True
        top=reinforcement(wall,entry(wall,'zapata_transversal','superior'),10)
        bottom=reinforcement(wall,entry(wall,'zapata_transversal','inferior'),10)
        self.assertEqual(top.body,((0,0),(7.45,0)))
        self.assertEqual(bottom.body,((0,-1.2),(7.45,-1.2)))
        self.assertEqual(top.start_direction,(0,-1))
        self.assertEqual(bottom.start_direction,(0,1))
        key=reinforcement(wall,entry(wall,'dentellon_transversal'),10)
        self.assertEqual(key.body[0][1],0)
        self.assertEqual(key.body[-1],(4.45,0))
        self.assertAlmostEqual(key.body[1][1],-1.9)
        self.assertAlmostEqual(key.body[0][0],4.45-.6-.4*1.9/.7)
        self.assertAlmostEqual(key.body_length,4.688327103109606)
        longitudinal=reinforcement(wall,entry(wall,'dentellon'),10)
        self.assertEqual(longitudinal.distribution,((3.85,-1.9),(4.45,-1.9)))
        points=spaced_points(longitudinal.distribution,.25)
        self.assertEqual(len(points),4)
        self.assertTrue(all(point[1] == -1.9 for point in points))

    def test_hooks_are_independent_added_once_and_not_counted_as_distribution(self):
        wall=default_wall_type()
        wall.hooks['pantalla_vertical:derecha']=dict(start=.2,end=.7)
        item=entry(wall,'pantalla_vertical','derecha')
        geometry=reinforcement(wall,item,10)
        self.assertAlmostEqual(geometry.total_length,10.4)
        self.assertAlmostEqual(geometry.points[0][0],4.25)
        self.assertAlmostEqual(geometry.points[-1][0],5.15)
        row=next(r[1] for r in generate_wall_rows(wall,10)
                 if r[0]=='kg' and 'vertical · Derecha' in r[1]['cells'][1])
        self.assertEqual(int(row['cells'][3]),51)
        self.assertAlmostEqual(float(row['cells'][4]),9.5)
        self.assertAlmostEqual(float(row['cells'][5]),.9)
        wall.hooks['pantalla_vertical:derecha']=dict(start=0,end=0)
        self.assertAlmostEqual(reinforcement(wall,item,10).total_length,9.5)

    def test_cut_body_is_fixed_across_instance_heights_and_includes_footing(self):
        wall=default_wall_type()
        cut=dict(component='refuerzo_cortado',side='izquierda',diameter='3/4"',spacing=.2,fixed_length=4.6)
        initial=reinforcement(wall,cut,10)
        self.assertAlmostEqual(initial.body[0][1],4.6)
        self.assertEqual(initial.body[-1][1],-1.2)
        self.assertAlmostEqual(initial.body_length,5.823630913900568)
        low=reinforcement(wall,cut,10,6)
        high=reinforcement(wall,cut,10,10)
        self.assertEqual(low.total_length,high.total_length)
        self.assertEqual(low.body[-1][1],-1.2)
        with self.assertRaises(ValueError):
            reinforcement(wall,cut,10,2)

    def test_hook_validation_and_legacy_defaults(self):
        payload=asdict(default_wall_type())
        del payload['hooks']
        legacy=WallType.from_dict(payload)
        self.assertGreater(reinforcement(legacy,entry(legacy,'pantalla_vertical')).hook_start,0)
        for value in (-1,float('inf'),float('nan'),'0.3',True):
            wall=deepcopy(legacy)
            wall.hooks['pantalla_vertical:izquierda']=dict(start=value,end=0)
            with self.subTest(value=value),self.assertRaises(ValueError):
                wall.validate()

    def test_edit_hooks_in_diagram_roundtrip_and_independent_positions(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            store=WallTypeStore(root/'types.db')
            dialog=WallTypeDialog(store)
            dialog.tabs.setCurrentIndex(1)
            dialog.show()
            APP.processEvents()
            editor=dialog.section.editor
            editor.start.setText('1/5')
            editor.start.editingFinished.emit()
            editor.end.setText('0.70')
            editor.end.editingFinished.emit()
            self.assertEqual(dialog.read_form().hooks['pantalla_vertical:izquierda'],dict(start=.2,end=.7))
            self.assertAlmostEqual(editor.geometry.hook_start,.2)
            dialog.distributions.select_position('zapata_transversal:inferior')
            self.assertEqual(editor.key,'zapata_transversal:inferior')
            self.assertNotEqual(editor.end.text(),'0.7')
            editor.start.clear()
            editor.start.editingFinished.emit()
            self.assertEqual(dialog.read_form().hooks[editor.key]['start'],0)
            # Hit testing on a noncoincident hook selects its position.
            APP.processEvents()
            segment=next((a,b) for key,a,b in dialog.section._segments
                         if key=='pantalla_vertical:derecha' and a != b)
            point=(segment[0]+segment[1])/2
            QTest.mouseClick(dialog.section,Qt.LeftButton,pos=point.toPoint())
            self.assertEqual(editor.key,'pantalla_vertical:derecha')
            dialog.accept()
            saved=store.read()[0]
            self.assertEqual(saved.hooks['pantalla_vertical:izquierda'],dict(start=.2,end=.7))
            store.export_json(root/'types.json')
            other=WallTypeStore(root/'other.db')
            other.import_json(root/'types.json')
            self.assertEqual(other.read()[0].hooks,saved.hooks)
            rows=[new_row('item',unit='kg',description='Acero')]
            ensure_ids(rows)
            generated=apply_wall(rows,saved,10,None,{'kg':rows[0]['id']},'A')
            write_database(root/'obra.db','Obra',generated)
            config=selected_wall(read_database(root/'obra.db')[1],1)
            self.assertEqual(config['wall']['hooks'],saved.hooks)
            dialog.close()


if __name__=='__main__':
    unittest.main()
