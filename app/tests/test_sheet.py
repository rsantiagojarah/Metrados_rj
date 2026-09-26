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
from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit, QMessageBox
import metrado._enlace as engine
from metrado.grid import SheetModel
from metrado.sheet import calculate, example_rows, new_row, read_project, write_project
from metrado.steel import STEEL_LABELS, apply_bar_spec, header_mode
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


    def test_steel_kg_partida_uses_stirrup_columns(self):
        rows = example_rows()
        values, errors = calculate(rows, engine)
        self.assertNotIn(15, errors)
        self.assertAlmostEqual(values[(15, 8)], 1336.66, places=4)
        self.assertAlmostEqual(values[(15, 11)], 3.978, places=2)
        self.assertAlmostEqual(values[(15, 12)], 2 * 12.61 * 53 * values[(15, 11)], places=4)
        self.assertEqual(rows[15]["cells"][9], "1")
        steel_weights = [values[(index, 12)] for index in range(15, len(rows))
                         if rows[index]["kind"] == "detail"]
        self.assertAlmostEqual(values[(14, 13)], sum(steel_weights), places=4)
        self.assertEqual(header_mode(rows, 14), "steel")
        self.assertEqual(header_mode(rows, 15), "steel")
        self.assertEqual(header_mode(rows, 4), "standard")
        self.assertEqual(header_mode(rows, 11), "standard")

    def test_veces_multiplies_steel_weight(self):
        rows = [new_row("item", unit="kg"), new_row("detail", unit="kg")]
        rows[1]["cells"][3] = "2"
        rows[1]["cells"][4] = "10.85"
        rows[1]["cells"][5] = "0.61"
        rows[1]["cells"][6] = "1.15"
        rows[1]["cells"][7] = "1\""
        rows[1]["cells"][9] = "2"
        rows[1]["cells"][10] = "53"
        values, errors = calculate(rows, engine)
        self.assertEqual(errors, {})
        once = 2 * 12.61 * 53 * values[(1, 11)]
        self.assertAlmostEqual(values[(1, 12)], once * 2, places=3)

    def test_empty_gancho_counts_as_zero(self):
        rows = [new_row("item", unit="kg"), new_row("detail", unit="kg")]
        rows[1]["cells"][4] = "2.15"
        rows[1]["cells"][7] = "3/4\""
        rows[1]["cells"][10] = "6"
        values, errors = calculate(rows, engine)
        self.assertEqual(errors, {})
        self.assertAlmostEqual(values[(1, 8)], 12.90, places=4)

    def test_m2_geometry_unchanged_beside_steel(self):
        model = SheetModel(engine, example_rows())
        self.assertEqual(model.values[(11, 13)], 837.13)
        self.assertFalse(model.flags(model.index(4, 9)) & Qt.ItemIsEditable)
        self.assertTrue(model.flags(model.index(15, 9)) & Qt.ItemIsEditable)
        self.assertTrue(model.flags(model.index(15, 7)) & Qt.ItemIsEditable)
        self.assertFalse(model.flags(model.index(15, 8)) & Qt.ItemIsEditable)
        self.assertFalse(model.flags(model.index(15, 10)) & Qt.ItemIsEditable)
        self.assertFalse(model.flags(model.index(15, 11)) & Qt.ItemIsEditable)

    def test_save_and_reopen_keeps_steel_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "aceros.metrado.json"
            rows = example_rows()
            write_project(path, "Aceros", rows)
            title, restored = read_project(path)
            self.assertEqual(title, "Aceros")
            self.assertEqual(restored[15]["cells"][4:8], ["10.85", "0.61", "1.15", "1\""])
            self.assertEqual(restored[15]["cells"][9], "1")
            self.assertEqual(restored[15]["cells"][10], "53")
            self.assertEqual(calculate(restored, engine)[0][(15, 8)],
                             calculate(rows, engine)[0][(15, 8)])

    def test_description_fills_bars_and_diameter(self):
        cells = [""] * 14
        apply_bar_spec(cells, "VERTICAL INTERIOR CONTINUO 53 Ø1\"")
        self.assertEqual(cells[7], "1\"")
        self.assertEqual(cells[10], "53")
        model = SheetModel(engine, [new_row("item", unit="kg"), new_row("detail", unit="kg")])
        model.setData(model.index(1, 1), "VERTICAL INTERIOR CONTINUO 53 Ø1\"")
        model.setData(model.index(1, 3), "2")
        model.setData(model.index(1, 4), "10.85")
        self.assertEqual(model.rows[1]["cells"][7], "1\"")
        self.assertEqual(model.rows[1]["cells"][9], "1")
        self.assertAlmostEqual(model.values[(1, 8)], 1150.10, places=4)
        self.assertIn((1, 12), model.values)

    def test_edit_recalculates_only_its_partida(self):
        class CountingEngine:
            def __init__(self):
                self.calls = 0
            def ask_sheet_quantity(self, *args):
                self.calls += 1
                return engine.ask_sheet_quantity(*args)
            def __getattr__(self, name):
                return getattr(engine, name)
        counter = CountingEngine()
        rows = [new_row("item", unit="m"), new_row("detail", unit="m"),
                new_row("item", unit="m"), new_row("detail", unit="m")]
        rows[1]["cells"][4] = "2"
        rows[3]["cells"][4] = "7"
        model = SheetModel(counter, rows)
        counter.calls = 0
        notifications = []
        model.dataChanged.connect(lambda first, last, roles: notifications.append((first.row(), last.row())))
        model.setData(model.index(3, 4), "9")
        self.assertEqual(counter.calls, 1)
        self.assertEqual(model.values, calculate(rows, engine)[0])
        self.assertEqual(model.errors, {})
        self.assertEqual(notifications, [(2, 3)])

    def test_partial_calculation_matches_full_after_error_and_unit_changes(self):
        model = SheetModel(engine, example_rows())
        edits = [(15, 4, ""), (16, 4, "nan"), (15, 4, "10.85"),
                 (16, 4, "5.35"), (15, 9, '1/2"'), (15, 7, "60"),
                 (3, 2, "m3"), (4, 4, "2"), (4, 5, "3"), (4, 6, "4"),
                 (0, 1, "CAPÍTULO RENOMBRADO")]
        for row, column, value in edits:
            model.setData(model.index(row, column), value)
            self.assertEqual((model.values, model.errors), calculate(model.rows, engine))
        model.set_direct(15, "100")
        self.assertEqual((model.values, model.errors), calculate(model.rows, engine))
        model.replace(model.rows[:14])
        self.assertEqual((model.values, model.errors), calculate(model.rows, engine))
        model.replace([])
        self.assertEqual(model.values, {})
        self.assertEqual(model.errors, {})

    def test_summary_updates_after_errors_and_structure_changes(self):
        rows = [new_row("item", unit="m"), new_row("detail", unit="m"),
                new_row("item", unit="m"), new_row("detail", unit="m")]
        rows[1]["cells"][4] = "2"
        rows[3]["cells"][4] = "7"
        model = SheetModel(engine, rows)
        self.assertEqual(model.summary_text, "2 partidas · 2 detalles · 0 detalles pendientes")
        model.setData(model.index(3, 4), "")
        self.assertEqual(model.summary_text, "2 partidas · 2 detalles · 1 detalles pendientes")
        model.replace(rows[2:])
        self.assertEqual(model.summary_text, "1 partidas · 1 detalles · 1 detalles pendientes")
        model.setData(model.index(1, 4), "8")
        self.assertEqual(model.summary_text, "1 partidas · 1 detalles · 0 detalles pendientes")
        model.replace([])
        self.assertEqual(model.summary_text, "0 partidas · 0 detalles · 0 detalles pendientes")

    def test_reference_columns_show_accumulated_length_and_weight(self):
        model = SheetModel(engine, example_rows())
        display = lambda column: model.data(model.index(15, column))
        self.assertEqual(display(7), "53")
        self.assertEqual(display(8), "1336.66")
        self.assertEqual(display(9), '1"')
        self.assertEqual(display(10), f"{model.values[(15, 11)]:.2f}")
        self.assertEqual(display(11), f"{model.values[(15, 12)]:.2f}")
        self.assertEqual(display(12), "")
        self.assertEqual(display(4), "10.85")
        self.assertEqual(model.data(model.index(16, 6)), "0.00")

    def test_reference_times_edits_preserve_diameter_and_weight(self):
        rows = example_rows()
        rows[15]["cells"][9] = "2"
        model = SheetModel(engine, rows)
        self.assertEqual(model.data(model.index(15, 7)), "106")
        self.assertAlmostEqual(model.values[(15, 8)], 2673.32)
        before = model.values[(15, 12)]
        model.setData(model.index(15, 7), "53")
        self.assertEqual(rows[15]["cells"][7], '1"')
        self.assertEqual(rows[15]["cells"][9], "1")
        self.assertAlmostEqual(model.values[(15, 12)], before / 2)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reference.json"
            write_project(path, "Referencia", rows)
            _, restored = read_project(path)
            self.assertEqual(calculate(restored, engine), calculate(rows, engine))

    def test_diameter_from_description_without_bar_count(self):
        model = SheetModel(engine, example_rows())
        model.setData(model.index(15, 1), "BARRA VERTICAL Ø8mm")
        self.assertEqual(model.rows[15]["cells"][7], "8mm")
        self.assertEqual(model.rows[15]["cells"][10], "53")
        self.assertNotIn(15, model.errors)
        model.setData(model.index(15, 1), "BARRA SIN DIÁMETRO")
        self.assertNotIn(15, model.errors)
        self.assertEqual(model.rows[15]["cells"][7], "8mm")
        self.assertEqual(model.data(model.index(15, 7)), "53")

    def test_reference_direct_quantity_times(self):
        model = SheetModel(engine, example_rows())
        model.set_direct(15, "100")
        self.assertEqual(model.data(model.index(15, 7)), "1")
        model.setData(model.index(15, 7), "3")
        self.assertEqual(model.rows[15]["direct"], "100")
        self.assertEqual(model.data(model.index(15, 11)), "600.00")
        self.assertEqual(model.data(model.index(15, 10)), "")
        self.assertEqual(model.data(model.index(15, 8)), "")

    def test_unit_change_to_kg_clears_geometry(self):
        model = SheetModel(engine, example_rows())
        self.assertTrue(model.setData(model.index(3, 2), "kg"))
        self.assertEqual(model.rows[4]["cells"][2], "kg")
        self.assertEqual(model.rows[4]["cells"][4:8], ["", "", "", ""])
        self.assertEqual(model.rows[4]["cells"][9], "1")
        self.assertEqual(model.rows[4]["cells"][10], "")
        self.assertNotIn((3, 13), model.values)


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

    def test_example_opens_on_steel_partida(self):
        self.assertEqual(self.window.table.horizontalHeader().mode, "steel")
        self.assertEqual(self.window.table.rowHeight(14), self.window.table.rowHeight(15))
        self.assertEqual(self.window.model.headerData(5, Qt.Horizontal), "gancho")
        self.assertEqual(self.window.model.headerData(10, Qt.Horizontal), "kg/m")
        self.assertEqual(self.window.model.headerData(11, Qt.Horizontal), "Kg.")

    def test_header_follows_selection_without_local_headers(self):
        from metrado.grid import WIDTHS
        from metrado.steel import STEEL_WIDTHS
        total = self.window.model.values[(14, 13)]
        for row, mode, widths in ((4, "standard", WIDTHS), (14, "steel", STEEL_WIDTHS),
                                  (15, "steel", STEEL_WIDTHS), (13, "standard", WIDTHS)):
            self.window._select(row)
            APP.processEvents()
            self.assertEqual(self.window.table.horizontalHeader().mode, mode)
            self.assertEqual([self.window.table.columnWidth(c) for c in range(14)], list(widths))
            self.assertEqual(self.window.table.rowHeight(14), 28)
            self.assertEqual(self.window.table.rowHeight(15), 28)
        self.assertEqual(self.window.model.headerData(5, Qt.Horizontal), "Ancho")
        self.assertEqual(self.window.model.values[(14, 13)], total)
        self.assertFalse(self.window._dirty)

    def test_header_follows_unit_edit(self):
        self.window._select(14)
        self.window.model.setData(self.window.model.index(14, 2), "m3")
        self.assertEqual(self.window.table.horizontalHeader().mode, "standard")
        self.window.model.setData(self.window.model.index(14, 2), "kg")
        self.assertEqual(self.window.table.horizontalHeader().mode, "steel")
        self.assertEqual(self.window.table.rowHeight(14), 28)

    def test_diameter_dropdown_recalculates_and_persists(self):
        self.window._select(15, 9)
        before = self.window.model.values[(15, 12)]
        QTest.keyClick(self.window.table, Qt.Key_F2)
        APP.processEvents()
        editor = self.window.table.findChild(QComboBox)
        self.assertIsNotNone(editor)
        self.assertEqual(editor.currentText(), '1"')
        editor.setCurrentText('1/2"')
        QTest.keyClick(editor, Qt.Key_Return)
        APP.processEvents()
        model = self.window.model
        self.assertEqual(model.data(model.index(15, 9)), '1/2"')
        self.assertEqual(model.rows[15]["cells"][9], "1")
        self.assertEqual(model.rows[15]["cells"][10], "53")
        self.assertIn('Ø1/2"', model.rows[15]["cells"][1])
        self.assertAlmostEqual(model.values[(15, 12)], before / 4)
        self.assertAlmostEqual(model.values[(15, 8)], 1336.66)
        self.assertFalse(model.setData(model.index(15, 9), "inválido"))
        self.assertEqual(model.data(model.index(15, 9)), '1/2"')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "diametro.json"
            write_project(path, "Diámetro", model.rows)
            _, restored = read_project(path)
            self.assertEqual(restored[15]["cells"][7], '1/2"')
            self.assertEqual(calculate(restored, engine), calculate(model.rows, engine))

    def test_moving_cell_repaints_selection_without_other_rows(self):
        from metrado.grid import SheetDelegate
        painted = set()

        class RecordingDelegate(SheetDelegate):
            def paint(self, painter, option, index):
                painted.add((index.row(), index.column()))
                super().paint(painter, option, index)

        delegate = RecordingDelegate(self.window.table)
        self.window.table.setItemDelegate(delegate)
        self.window._select(15, 4)
        APP.processEvents()
        painted.clear()
        self.window.table.setCurrentIndex(self.window.model.index(15, 5))
        APP.processEvents()
        self.assertIn((15, 5), painted)
        self.assertEqual({row for row, _ in painted}, {15})
        self.assertFalse(self.window._dirty)

    def test_selection_does_not_scan_sheet_rows(self):
        class TrackedRows(list):
            scans = 0
            def __iter__(self):
                self.scans += 1
                return super().__iter__()
        rows = TrackedRows(example_rows())
        self.window.model.replace(rows)
        APP.processEvents()
        rows.scans = 0
        for row in (15, 16, 4, 14, 20):
            self.window._select(row)
            APP.processEvents()
        self.assertEqual(rows.scans, 0)
        self.assertEqual(self.window.statusBar().currentMessage(), self.window.model.summary_text)

    def test_reference_times_keyboard_editor(self):
        self.window._select(15, 7)
        QTest.keyClick(self.window.table, Qt.Key_F2)
        APP.processEvents()
        editor = self.window.table.findChild(QLineEdit)
        self.assertIsNotNone(editor)
        editor.selectAll()
        QTest.keyClicks(editor, "60")
        QTest.keyClick(editor, Qt.Key_Return)
        APP.processEvents()
        self.assertEqual(self.window.model.rows[15]["cells"][7], '1"')
        self.assertEqual(self.window.model.data(self.window.model.index(15, 7)), "60")
        self.assertAlmostEqual(self.window.model.values[(15, 8)], 1513.2)

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
