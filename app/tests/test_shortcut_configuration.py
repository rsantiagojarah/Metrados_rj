"""Persistence, validation and live application of user-defined shortcuts."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialogButtonBox

import metrado._enlace as engine
from metrado.database import ConflictError
from metrado.shortcut_store import ShortcutStore, normalize_shortcuts
from metrado.shortcuts import ShortcutDialog, validate_configuration
from metrado.steel_store import CatalogStore
from metrado.window import PlantillaWindow


APP = QApplication.instance() or QApplication([])


class ShortcutStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ShortcutStore(Path(self.temp.name) / 'atajos.sqlite3')

    def tearDown(self):
        self.temp.cleanup()

    def test_defaults_save_read_noop_and_conflict(self):
        self.assertEqual(self.store.read(), ({}, None))
        configuration = {'file.save': ['Ctrl+S'], 'navigate.panels': ['F6', 'Shift+F6']}
        revision = self.store.save(configuration, None)
        self.assertEqual(revision, 1)
        self.assertEqual(self.store.read(), (configuration, 1))
        self.assertEqual(self.store.save(configuration, 1), 1)
        changed = dict(configuration, **{'file.save': ['Ctrl+Alt+S']})
        self.assertEqual(self.store.save(changed, 1), 2)
        with self.assertRaises(ConflictError):
            self.store.save(configuration, 1)

    def test_invalid_identifiers_sequences_and_alternatives_are_rejected(self):
        for configuration in (
                {'Invalid id': ['Ctrl+S']},
                {'file.save': ['Ctrl+S', 'Ctrl+S']},
                {'file.save': ['Ctrl+S', 'Ctrl+Alt+S', 'F8']}):
            with self.assertRaises(ValueError, msg=configuration):
                normalize_shortcuts(configuration)
        self.assertEqual(normalize_shortcuts({'file.save': ['']}), {'file.save': []})

    def test_conflicts_and_editor_navigation_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'repetido'):
            validate_configuration({'file.save': ['Ctrl+Q'], 'file.open': ['Ctrl+Q']})
        for shortcut in ('F2', 'Esc', 'Tab', 'Ctrl+A', '/'):
            with self.assertRaisesRegex(ValueError, 'reservado'):
                validate_configuration({'file.save': [shortcut]})


class ShortcutWindowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.catalog = CatalogStore(root / 'aceros.sqlite3')
        self.store = ShortcutStore(root / 'atajos.sqlite3')
        self.window = PlantillaWindow(engine, self.catalog, self.store)
        self.window.show()
        self.window.activateWindow()
        self.window.table.setFocus()
        APP.processEvents()

    def tearDown(self):
        with patch.object(self.window, '_can_discard', return_value=True):
            self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        self.temp.cleanup()

    def test_every_command_is_configurable_including_actions_without_defaults(self):
        bindings = self.window.keyboard.bindings
        self.assertEqual(len(bindings), len(self.window.keyboard.commands))
        self.assertEqual(len({binding.action_id for binding in bindings}), len(bindings))
        self.assertTrue(all(binding.category for binding in bindings))
        self.assertEqual(
            next(binding for binding in bindings
                 if binding.action is self.window.import_excel_action).defaults, ())
        self.assertIn('help.configure_shortcuts', {binding.action_id for binding in bindings})

    def test_dialog_detects_conflicts_can_clear_and_restore_defaults(self):
        keyboard = self.window.keyboard
        dialog = ShortcutDialog(keyboard.bindings, keyboard.configuration, self.window)
        try:
            dialog.editors['file.new'][0].setKeySequence(QKeySequence('Ctrl+Alt+9'))
            dialog.editors['file.open'][0].setKeySequence(QKeySequence('Ctrl+Alt+9'))
            APP.processEvents()
            self.assertFalse(dialog.buttons.button(QDialogButtonBox.Save).isEnabled())
            self.assertIn('repetido', dialog.error.text())
            row = next(i for i, binding in enumerate(dialog.bindings)
                       if binding.action_id == 'file.new')
            dialog.table.setCurrentCell(row, 1)
            dialog.clear_current()
            self.assertEqual(dialog.editors['file.new'][0].keySequence(), QKeySequence())
            dialog.restore_defaults()
            self.assertEqual(dialog.editors['file.new'][0].keySequence(), QKeySequence('Ctrl+N'))
            self.assertTrue(dialog.buttons.button(QDialogButtonBox.Save).isEnabled())
        finally:
            dialog.close()
            dialog.deleteLater()

    def test_custom_shortcut_replaces_default_updates_help_and_persists(self):
        keyboard = self.window.keyboard
        configuration = {key: list(value) for key, value in keyboard.configuration.items()}
        configuration['navigate.find'] = ['Ctrl+Alt+F']
        revision = self.store.save(configuration, None)
        self.assertEqual(revision, 1)
        keyboard.load_configuration()
        action = keyboard.actions['find']
        self.assertEqual(action.shortcut(), QKeySequence('Ctrl+Alt+F'))
        self.assertIn('Ctrl+Alt+F', keyboard.status_hint())
        self.assertIn('Ctrl+Alt+F', action.toolTip())

        action.triggered.disconnect()
        triggered = []
        action.triggered.connect(lambda: triggered.append(True))
        QTest.keyClick(self.window.table, Qt.Key_F, Qt.ControlModifier)
        QTest.keyClick(
            self.window.table, Qt.Key_F, Qt.ControlModifier | Qt.AltModifier)
        APP.processEvents()
        self.assertEqual(triggered, [True])

        second = PlantillaWindow(engine, self.catalog, self.store)
        try:
            self.assertEqual(second.keyboard.actions['find'].shortcut(),
                             QKeySequence('Ctrl+Alt+F'))
        finally:
            with patch.object(second, '_can_discard', return_value=True):
                second.close()
            second.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)

    def test_copy_shortcut_can_change_without_hijacking_text_editor_copy(self):
        keyboard = self.window.keyboard
        configuration = {key: list(value) for key, value in keyboard.configuration.items()}
        configuration['edit.copy'] = ['Ctrl+Alt+C']
        keyboard.apply_configuration(configuration)
        action = self.window.row_actions['copy']
        action.triggered.disconnect()
        triggered = []
        action.triggered.connect(lambda: triggered.append(True))
        QTest.keyClick(self.window.table, Qt.Key_C, Qt.ControlModifier)
        QTest.keyClick(
            self.window.table, Qt.Key_C, Qt.ControlModifier | Qt.AltModifier)
        APP.processEvents()
        self.assertEqual(triggered, [True])


if __name__ == '__main__':
    unittest.main()
