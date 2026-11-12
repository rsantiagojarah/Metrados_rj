"""The window paints while loading; Qt receives only completed worker results."""
from dataclasses import asdict
from copy import deepcopy
import os
from threading import Event, get_ident
import time
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QTimer, QCoreApplication, QEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
import metrado._enlace as engine
from metrado.sheet import new_row, validate_project
from metrado.wall_types import WallType, default_wall_type
from metrado.window import PlantillaWindow

APP = QApplication.instance() or QApplication([])


def wait_for(condition):
    deadline = time.monotonic() + 3
    while not condition() and time.monotonic() < deadline:
        APP.processEvents()
        QTest.qWait(2)
    if not condition():
        raise AssertionError('La operación de arranque no terminó.')


class Bridge:
    def __init__(self):
        self.started = Event()
        self.stopped = Event()

    def start(self):
        self.started.set()
        return True

    def stop(self):
        self.stopped.set()


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.window = None
        self.boot = None
        self.release = Event()
        self.bridge = Bridge()

    def tearDown(self):
        self.release.set()
        if self.boot is not None:
            self.boot.shutdown()
        if self.window is not None:
            with patch.object(self.window, '_can_discard', return_value=True):
                self.window.close()
            self.window.deleteLater()
        APP.clipboard().clear()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        APP.processEvents()

    def create(self, reader):
        from metrado.startup import StartupCoordinator
        self.window = PlantillaWindow(engine, initial_rows=[])
        self.boot = StartupCoordinator(self.window, None, self.bridge, reader=reader)
        self.window.show()
        APP.processEvents()
        self.boot.start()

    def test_slow_read_does_not_block_paint_events_or_enable_edits(self):
        from metrado.project_session import SessionLoad
        entered = Event()
        threads = []
        ui_thread = get_ident()
        def reader(store):
            threads.append(get_ident());entered.set();self.release.wait(2)
            return SessionLoad()
        self.create(reader)
        wait_for(entered.is_set)
        pulse = []
        QTimer.singleShot(0, lambda: pulse.append(True))
        wait_for(lambda: bool(pulse))
        self.assertTrue(self.window.isVisible())
        self.assertFalse(self.window.isEnabled())
        self.assertFalse(self.bridge.started.is_set())
        self.assertNotEqual(threads[0], ui_thread)
        self.release.set()
        wait_for(lambda: self.window.isEnabled())
        wait_for(self.bridge.started.is_set)

    def test_document_is_applied_in_qt_thread_and_keeps_revision(self):
        from pathlib import Path
        from metrado.project_session import SessionLoad
        row = new_row('item', '01', 'Obra', 'm', 0)
        result = SessionLoad(path=Path('prueba.db').absolute(), document=('Mi obra', [row], 4))
        self.create(lambda store: result)
        threads = []
        original = self.window._load
        def load(*args):
            threads.append(get_ident());return original(*args)
        with patch.object(self.window, '_load', side_effect=load):
            wait_for(lambda: self.window.isEnabled())
        self.assertEqual(threads, [get_ident()])
        self.assertEqual(self.window.title_edit.text(), 'Mi obra')
        self.assertEqual(self.window._revision, 4)
        self.assertEqual(self.window._path, result.path)
        self.assertFalse(self.window._dirty)

    def test_close_during_read_does_not_apply_late_data_or_start_bridge(self):
        from metrado.project_session import SessionLoad
        entered = Event()
        def reader(store):
            entered.set();self.release.wait(2)
            return SessionLoad(document=('Obra tardía', [], 1))
        self.create(reader)
        wait_for(entered.is_set)
        self.window.close()
        self.release.set()
        wait_for(lambda: not self.boot.loading)
        self.assertFalse(self.window.isVisible())
        self.assertFalse(self.bridge.started.is_set())
        self.assertNotEqual(self.window.title_edit.text(), 'Obra tardía')

    def test_close_during_bridge_start_stops_it_after_start_returns(self):
        from metrado.project_session import SessionLoad
        class SlowBridge(Bridge):
            def start(bridge):
                bridge.started.set();self.release.wait(2)
                return True
        self.bridge = SlowBridge()
        self.create(lambda store: SessionLoad())
        wait_for(self.bridge.started.is_set)
        self.window.close()
        self.release.set()
        self.boot.shutdown()
        self.assertTrue(self.bridge.stopped.is_set())

    def test_read_error_is_shown_and_window_becomes_usable(self):
        from metrado.project_session import SessionLoad
        self.create(lambda store: SessionLoad(error=PermissionError('Sin acceso')))
        wait_for(lambda: self.window.isEnabled())
        self.assertEqual(self.window.model.rows, [])
        self.assertIn('Sin acceso', self.window.statusBar().currentMessage())

    def test_bridge_failure_keeps_document_editable(self):
        from metrado.project_session import SessionLoad
        def fail():
            self.bridge.started.set()
            raise OSError('AutoCAD no disponible')
        self.bridge.start = fail
        self.create(lambda store: SessionLoad())
        wait_for(lambda: hasattr(self.bridge, 'last_error'))
        self.assertEqual(self.bridge.last_error, 'AutoCAD no disponible')
        self.assertTrue(self.window.isEnabled())

    @unittest.skipUnless(os.name == 'nt', 'Conexión local de Windows')
    def test_real_bridge_started_in_worker_is_cleaned_on_shutdown(self):
        from pathlib import Path
        import tempfile
        import uuid
        from metrado.autocad_bridge import AutoCadBridgeServer
        from metrado.project_session import SessionLoad
        with tempfile.TemporaryDirectory() as folder:
            self.bridge = AutoCadBridgeServer(Path(folder), mutex_name='Local\\MetradosStartupTest.' + uuid.uuid4().hex)
            self.create(lambda store: SessionLoad())
            wait_for(lambda: self.bridge.running and self.bridge.session_path.exists())
            self.window.close()
            self.boot.shutdown()
            self.assertFalse(self.bridge.running)
            self.assertFalse(self.bridge.session_path.exists())


def wall_document(count=20):
    rows = [new_row('item', '01', 'Concreto', 'm3', 0)]
    wall = asdict(default_wall_type())
    for i in range(count):
        row = new_row('detail', unit='m3', level=1)
        row['cells'][4:7] = ['1', '2', '3']
        row['wall_generated'] = dict(version=1, instance_id='tramo', name='Muro', key=str(i),
                                     wall=deepcopy(wall), length=10, height=8,
                                     destinations={'m3': 'partida'})
        rows.append(row)
    return dict(version=8, title='Muros', rows=rows)


class WallValidationCacheTests(unittest.TestCase):
    def test_equal_wall_snapshots_are_validated_once_without_mutating_them(self):
        data = wall_document()
        before = deepcopy(data['rows'][1]['wall_generated']['wall'])
        with patch.object(WallType, 'from_dict', wraps=WallType.from_dict) as validate:
            validate_project(data)
        self.assertEqual(validate.call_count, 1)
        self.assertEqual(data['rows'][1]['wall_generated']['wall'], before)

    def test_different_or_later_corrupt_wall_is_not_hidden_by_the_cache(self):
        data = wall_document()
        data['rows'][-1]['wall_generated']['wall']['screen_height'] = 0
        with self.assertRaises(ValueError):
            validate_project(data)

    def test_row_metadata_is_checked_even_when_wall_type_is_cached(self):
        data = wall_document()
        data['rows'][-1]['wall_generated']['length'] = -1
        with self.assertRaises(ValueError):
            validate_project(data)

    def test_validation_cache_does_not_survive_a_project_validation(self):
        data = wall_document(2)
        with patch.object(WallType, 'from_dict', wraps=WallType.from_dict) as validate:
            validate_project(deepcopy(data));validate_project(deepcopy(data))
        self.assertEqual(validate.call_count, 2)


if __name__ == '__main__':
    unittest.main()
