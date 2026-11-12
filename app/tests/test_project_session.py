"""Last saved SQLite document, startup fallback and non-destructive errors."""
from pathlib import Path
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
import metrado._enlace as engine
from metrado.database import write_database
from metrado.sheet import new_row
from metrado.steel_store import CatalogStore
from metrado.window import PlantillaWindow

APP = QApplication.instance() or QApplication([])


class ProjectSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        from metrado.project_session import LastProjectStore
        self.store = LastProjectStore(self.root / 'session.json')
        self.catalog = CatalogStore(self.root / 'catalog.sqlite3')
        self.windows = []
        self.path = self.root / 'Obra Perú #1.metrado.db'
        self.rows = [new_row('item', '01', 'Obra guardada', 'm', 0),
                     new_row('detail', unit='m', level=1)]
        self.rows[1]['cells'][4] = '2.5'
        write_database(self.path, 'Mi obra', self.rows)

    def tearDown(self):
        for window in self.windows:
            with patch.object(window, '_can_discard', return_value=True):
                window.close()
            window.deleteLater()
        APP.processEvents()
        self.temp.cleanup()

    def window(self):
        window = PlantillaWindow(engine, catalog_store=self.catalog, session_store=self.store)
        self.windows.append(window)
        return window

    def test_successful_open_reopens_same_database_and_revision(self):
        window = self.window()
        with patch('metrado.window.QFileDialog.getOpenFileName', return_value=(str(self.path), '')):
            window.open_project()
        self.assertEqual(self.store.read(), self.path)
        reopened = self.window()
        self.assertTrue(reopened.restore_last_project())
        self.assertEqual(reopened._path, self.path)
        self.assertEqual(reopened.title_edit.text(), 'Mi obra')
        self.assertEqual(reopened.model.values[0, 13], 2.5)
        self.assertEqual(reopened._revision, window._revision)
        self.assertFalse(reopened._dirty)

    def test_save_as_remembers_new_destination_and_failed_save_preserves_it(self):
        window = self.window()
        window._load('Nueva', self.rows)
        other = self.root / 'Nueva.metrado.db'
        with patch('metrado.window.QFileDialog.getSaveFileName', return_value=(str(other), '')):
            self.assertTrue(window.save_project())
        self.assertEqual(self.store.read(), other)
        with patch('metrado.window.write_database', side_effect=sqlite3.OperationalError('fallo')), patch('metrado.window.QMessageBox.warning'):
            self.assertFalse(window.save_project())
        self.assertEqual(self.store.read(), other)
        self.assertTrue(self.window().restore_last_project())

    def test_missing_local_file_opens_blank_and_clears_stale_path(self):
        self.store.remember(self.path)
        self.path.unlink()
        window = self.window()
        self.assertFalse(window.restore_last_project())
        self.assertEqual(window.model.rows, [])
        self.assertIsNone(window._path)
        self.assertIsNone(self.store.read())

    def test_inaccessible_database_keeps_path_for_next_startup(self):
        self.store.remember(self.path)
        window = self.window()
        with patch('metrado.window.open_document', side_effect=PermissionError('Sin acceso')):
            self.assertFalse(window.restore_last_project())
        self.assertEqual(self.store.read(), self.path)
        self.assertEqual(window.model.rows, [])
        self.assertIn('Sin acceso', window.statusBar().currentMessage())

    def test_disconnected_unc_server_keeps_last_path(self):
        network = Path(r'\\Win-3s633a51bp0\e\Puentes\Obra.metrado.db')
        self.store.remember(network)
        disconnected = FileNotFoundError('Servidor desconectado')
        disconnected.winerror = 53
        window = self.window()
        with patch('metrado.window.open_document', side_effect=disconnected):
            self.assertFalse(window.restore_last_project())
        self.assertEqual(self.store.read(), network)
        self.assertEqual(window.model.rows, [])

    def test_unc_document_restores_through_the_same_loading_path(self):
        network = Path(r'\\Win-3s633a51bp0\e\Puentes\Obra.metrado.db')
        self.store.remember(network)
        window = self.window()
        with patch('metrado.window.open_document', return_value=('Obra en red', self.rows, 7)) as opened:
            self.assertTrue(window.restore_last_project())
        opened.assert_called_once_with(network)
        self.assertEqual(window._path, network)
        self.assertEqual(window._revision, 7)
        self.assertEqual(window.title_edit.text(), 'Obra en red')

    def test_actual_application_entrypoint_requests_session_restore(self):
        from metrado import __main__ as entry
        with patch.object(entry, 'QApplication') as application, \
                patch.object(entry, 'AutoCadBridgeServer'), \
                patch.object(entry, 'AutoCadRequestDispatcher'), \
                patch.object(entry, 'LastProjectStore', return_value=self.store), \
                patch.object(entry, 'StartupCoordinator') as startup, \
                patch.object(entry.QTimer, 'singleShot') as scheduled, \
                patch('metrado.window.PlantillaWindow') as constructor:
            application.return_value.exec.return_value = 0
            self.assertEqual(entry.main(), 0)
            self.assertIs(constructor.call_args.kwargs['session_store'], self.store)
            self.assertEqual(constructor.call_args.kwargs['initial_rows'], [])
            constructor.return_value.restore_last_project.assert_not_called()
            constructor.return_value.show.assert_called_once_with()
            scheduled.assert_called_once_with(0, startup.return_value.start)
            startup.return_value.shutdown.assert_called_once_with()

    def test_unc_path_is_stored_without_altering_backslashes(self):
        network = Path(r'\\Win-3s633a51bp0\e\Puentes\01_1_PUENTE VILLA CONF\Obra.metrado.db')
        self.store.remember(network)
        self.assertEqual(self.store.read(), network)

    def test_cancelled_open_and_invalid_file_keep_last_valid_path(self):
        self.store.remember(self.path)
        window = self.window()
        with patch('metrado.window.QFileDialog.getOpenFileName', return_value=('', '')):
            window.open_project()
        bad = self.root / 'invalida.db'
        bad.write_text('invalid', encoding='utf-8')
        with patch('metrado.window.QFileDialog.getOpenFileName', return_value=(str(bad), '')), patch('metrado.window.QMessageBox.warning'):
            window.open_project()
        self.assertEqual(self.store.read(), self.path)

    def test_settings_write_failure_does_not_undo_successful_database_save(self):
        window = self.window()
        window._load('Guardada', self.rows, self.path, 1)
        with patch.object(self.store, 'remember', side_effect=OSError('configuración bloqueada')):
            self.assertTrue(window.save_project())
        self.assertFalse(window._dirty)
        self.assertIn('recordar', window.statusBar().currentMessage())


if __name__ == '__main__':
    unittest.main()
