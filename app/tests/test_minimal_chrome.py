"""One command row, native overflow and a single contextual status line."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QToolBar, QToolButton
import metrado._enlace as engine
from metrado.chrome import ActionButton, FlatAction
from metrado.steel_store import CatalogStore
from metrado.window import PlantillaWindow

APP = QApplication.instance() or QApplication([])


class MinimalChromeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.window = PlantillaWindow(engine, CatalogStore(Path(self.temp.name) / 'catalog.db'))
        self.window.show()
        self.window.activateWindow()
        APP.processEvents()
        self.toolbar = self.window.findChild(QToolBar, 'actionStrip')

    def tearDown(self):
        with patch.object(self.window, '_can_discard', return_value=True):
            self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        self.temp.cleanup()

    def test_single_command_row_no_old_help_lines(self):
        self.assertEqual({b.objectName() for b in self.window.findChildren(QToolBar)}, {'appHeader', 'actionStrip'})
        self.assertIsNone(self.window.findChild(QLabel, 'sheetHint'))
        self.assertIsNone(self.window.findChild(QLabel, 'sheetNote'))
        self.assertEqual(self.window.centralWidget().layout().count(), 1)
        buttons = [b for b in self.toolbar.findChildren(ActionButton) if b.isVisible()]
        self.assertEqual(len({b.y() for b in buttons}), 1)
        self.assertEqual(self.toolbar.height(), 38)

    def test_every_command_has_flat_button_and_overflow_proxy(self):
        sources = {action.source for action in self.toolbar.actions() if isinstance(action, FlatAction)}
        expected = {*self.window.command_actions, self.window.undo_action, self.window.redo_action,
                    self.window.swelling_action, self.window.hooks_action,
                    *(self.window.row_actions[k] for k in ('up', 'down', 'indent', 'outdent', 'move', 'copy', 'paste'))}
        self.assertEqual(sources, expected)
        self.assertEqual(len(self.toolbar.findChildren(ActionButton)), len(expected))

    def test_history_caption_and_width_stay_short(self):
        button = next(b for b in self.toolbar.findChildren(ActionButton) if b.defaultAction() is self.window.undo_action)
        width = button.width()
        self.window.model.setData(self.window.model.index(1, 1), 'Nombre nuevo muy largo')
        APP.processEvents()
        self.assertEqual(button.caption, 'Deshacer')
        self.assertEqual(button.width(), width)
        self.assertTrue(button.isEnabled())
        QTest.mouseClick(button, Qt.LeftButton)
        self.assertEqual(self.window.model.rows[1]['cells'][1], 'ENERGÍA ELÉCTRICA PARA LA OBRA')

    def test_compact_footer_changes_context_and_prioritizes_messages(self):
        self.window._select(15, 1)
        self.window._selection_status()
        status = self.window.statusBar()
        self.assertIn('Acero:', status.line_text())
        self.assertIn('F6:', status.line_text())
        self.assertIn(self.window.model.summary_text, status.line_text())
        self.window._select(4, 1)
        self.window._selection_status()
        self.assertNotIn('Acero:', status.line_text())
        status.showMessage('No se pudo completar la operación', 30)
        self.assertTrue(status.line_text().startswith('No se pudo'))
        self.assertIn('No se pudo', status.toolTip())
        QTest.qWait(60)
        self.assertIn('Metrado:', status.line_text())
        self.assertEqual(status.height(), 24)

    def test_narrow_window_overflow_keeps_commands_accessible(self):
        self.window.resize(900, 600)
        APP.processEvents()
        extension = self.toolbar.findChild(QToolButton, 'qt_toolbar_ext_button')
        self.assertTrue(extension.isVisible())
        self.assertEqual(self.toolbar.height(), 38)
        menu = self.toolbar.overflow.menu
        QTest.mouseClick(extension, Qt.LeftButton)
        APP.processEvents()
        self.assertTrue(menu.isVisible())
        self.assertEqual(self.toolbar.height(), 38)
        actions = menu.actions()
        self.assertIn(self.window.hooks_action, actions)
        menu.close()
        proxy = next(a for a in self.toolbar.actions() if isinstance(a, FlatAction) and a.source is self.window.undo_action)
        original = self.window.model.rows[1]['cells'][1]
        self.window.model.setData(self.window.model.index(1, 1), 'Prueba desbordamiento')
        proxy.trigger()
        self.assertEqual(self.window.model.rows[1]['cells'][1], original)
        self.assertIsNone(proxy.createWidget(QMenu(self.window)))

    def test_table_tops_remain_aligned(self):
        left = self.window.navigator.mapToGlobal(self.window.navigator.rect().topLeft()).y()
        right = self.window.table.mapToGlobal(self.window.table.rect().topLeft()).y()
        self.assertEqual(left, right)
