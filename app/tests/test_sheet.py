"""Integration checks against the real Rust engine and desktop widgets."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QMessageBox
import metrado._enlace as engine
from metrado.grid import SheetModel
from metrado.sheet import calculate, example_rows, new_row, read_project, write_project
from metrado.window import PlantillaWindow

APP = QApplication.instance() or QApplication([])


class SheetTests(unittest.TestCase):
    def test_reference_quantities(self):
        values, errors = calculate(example_rows(), engine)
        self.assertEqual(errors, {})
        self.assertEqual(values[(1, 13)], 6)
        self.assertEqual(values[(3, 13)], 80)
        self.assertEqual(values[(11, 13)], 837.13)

    def test_total_waits_for_all_details(self):
        rows = [new_row("item", unit="m3"), new_row("detail", unit="m3"),
                new_row("detail", unit="m3")]
        rows[1]["cells"][4:7] = ["2", "3", "4"]
        values, errors = calculate(rows, engine)
        self.assertEqual(values[(1, 10)], 24)
        self.assertNotIn((0, 13), values)
        self.assertIn(0, errors)
        rows[2]["cells"][4:7] = ["1", "2", "3"]
        values, errors = calculate(rows, engine)
        self.assertEqual(values[(0, 13)], 30)
        self.assertEqual(errors, {})

    def test_factors_comma_and_invalid_numbers(self):
        rows = [new_row("item"), new_row("detail")]
        rows[1]["cells"][4] = "2,5"
        rows[1]["cells"][3] = "2"
        rows[1]["cells"][7] = "3"
        values, _ = calculate(rows, engine)
        self.assertEqual(values[(0, 13)], 15)
        for value in ("", "0", "-2", "nan", "inf", "abc"):
            rows[1]["cells"][4] = value
            values, errors = calculate(rows, engine)
            self.assertNotIn((0, 13), values)
            self.assertIn(1, errors)

    def test_unit_change_invalidates_old_geometry_and_direct(self):
        model = SheetModel(engine, example_rows())
        self.assertTrue(model.setData(model.index(3, 2), "m3"))
        self.assertEqual(model.rows[4]["cells"][2], "m3")
        self.assertNotIn((3, 13), model.values)
        self.assertEqual(model.rows[4]["cells"][4:7], ["", "", ""])
        self.assertFalse(model.flags(model.index(3, 13)) & Qt.ItemIsEditable)
        self.assertFalse(model.flags(model.index(4, 10)) & Qt.ItemIsEditable)

    def test_direct_and_geometric_modes(self):
        model = SheetModel(engine, [new_row("item", unit="m2"), new_row("detail", unit="m2")])
        model.set_direct(1, "837,13")
        self.assertEqual(model.values[(0, 13)], 837.13)
        model.setData(model.index(1, 4), "10")
        self.assertEqual(model.rows[1]["direct"], "")
        self.assertNotIn((0, 13), model.values)
        model.setData(model.index(1, 5), "20")
        self.assertEqual(model.values[(0, 13)], 200)

    def test_save_and_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "obra.metrado.json"
            rows = example_rows()
            write_project(path, "Obra — Perú", rows)
            title, restored = read_project(path)
            self.assertEqual(title, "Obra — Perú")
            self.assertEqual(restored, rows)
            self.assertEqual(calculate(restored, engine), calculate(rows, engine))

    def test_failed_write_preserves_existing_project(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "obra.metrado.json"
            write_project(path, "Original", example_rows())
            original = path.read_bytes()
            with patch("metrado.sheet.os.replace", side_effect=OSError("disk error")):
                with self.assertRaises(OSError):
                    write_project(path, "Nuevo", [])
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(Path(folder).glob("*.tmp")), [])

    def test_invalid_project_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "broken.json"
            cases = [
                {"version": 2, "title": "", "rows": []},
                {"version": 1, "title": "", "rows": [new_row("detail")]},
                {"version": 1, "title": "", "rows": [{"kind": "item", "cells": []}]},
                {"version": 1, "title": "", "rows": [new_row("item", unit="invalid")]},
            ]
            for data in cases:
                # Test fixtures are serialized data, not application source.
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_project(path)


class WindowTests(unittest.TestCase):
    def setUp(self):
        self.window = PlantillaWindow(engine)
        self.window.show()
        APP.processEvents()

    def tearDown(self):
        self.window._dirty = False
        self.window.close()
        self.window.deleteLater()
        APP.processEvents()

    def test_layout_and_keyboard_edit(self):
        self.assertEqual(self.window.model.columnCount(), 14)
        self.assertEqual(self.window.table.horizontalHeader().height(), 62)
        index = self.window.model.index(4, 4)
        self.window.table.setCurrentIndex(index)
        self.window.table.setFocus()
        QTest.keyClick(self.window.table, Qt.Key_F2)
        APP.processEvents()
        editor = self.window.table.findChild(QLineEdit)
        self.assertIsNotNone(editor)
        editor.selectAll()
        QTest.keyClicks(editor, "125")
        QTest.keyClick(editor, Qt.Key_Return)
        APP.processEvents()
        self.assertEqual(self.window.model.values[(3, 13)], 125)
        self.assertTrue(self.window._dirty)

    def test_input_text_remains_readable_on_dark_background(self):
        palette = self.window.title_edit.palette()
        self.assertGreater(palette.color(QPalette.Text).lightness(), 200)
        self.assertLess(palette.color(QPalette.Base).lightness(), 50)

    def test_flat_action_button_adds_detail(self):
        from metrado.chrome import ActionButton
        self.window._select(3)
        count = self.window.model.rowCount()
        button = next(b for b in self.window.findChildren(ActionButton)
                      if b.accessibleName() == "+ Detalle")
        QTest.mouseClick(button, Qt.LeftButton)
        APP.processEvents()
        self.assertEqual(self.window.model.rowCount(), count + 1)
        self.assertEqual(self.window.model.rows[4]["kind"], "detail")

    def test_action_shortcut_still_adds_detail(self):
        self.window._select(3)
        count = self.window.model.rowCount()
        QTest.keyClick(self.window.table, Qt.Key_Return, Qt.ControlModifier)
        APP.processEvents()
        self.assertEqual(self.window.model.rowCount(), count + 1)
        self.assertEqual(self.window.model.rows[4]["kind"], "detail")

    def test_insert_detail_and_delete_subtree(self):
        self.window._select(3)
        self.window.add_row("detail")
        self.assertEqual(self.window.model.rows[4]["kind"], "detail")
        self.window.table.setFocus()
        self.window._select(3)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            self.window.remove_row()
        self.assertFalse(any(r["cells"][0] == "00.01.10" for r in self.window.model.rows))
        self.assertEqual(self.window.model.rows[3]["kind"], "chapter")

    def test_discard_cancel_preserves_rows(self):
        self.window._dirty = True
        original = self.window.model.rows
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Cancel):
            self.window.new_project()
        self.assertIs(self.window.model.rows, original)
        self.assertTrue(self.window._dirty)

    def test_save_cancel_prevents_discard(self):
        self.window._dirty = True
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Save):
            with patch.object(self.window, "save_project", return_value=False):
                self.assertFalse(self.window._can_discard())


if __name__ == "__main__":
    unittest.main(verbosity=2)
