"""Background startup IO; only the Qt thread applies rows and enables widgets."""
from threading import Event, Thread

from PySide6.QtCore import QObject, Qt, Signal, Slot

from metrado.project_session import SessionLoad, read_last_project


class StartupCoordinator(QObject):
    documentReady = Signal()
    _loaded = Signal(object)

    def __init__(self, window, store, bridge, reader=read_last_project):
        super().__init__(window)
        self.window, self.store, self.bridge, self.reader = window, store, bridge, reader
        self._cancelled = Event()
        self._reader_thread = self._bridge_thread = None
        self._started = False
        self.loading = False
        self._loaded.connect(self._apply, Qt.QueuedConnection)
        window.startup = self
        # Disable editing before show(), including the first native input events.
        window.setEnabled(False)
        window.statusBar().showMessage('Abriendo obra…')

    def start(self):
        if self._started or self._cancelled.is_set():
            return
        self._started = True
        self.loading = True
        self.window.setEnabled(False)
        self.window.statusBar().showMessage('Abriendo obra…')
        self._reader_thread = Thread(target=self._read, name='MetradosStartupRead', daemon=True)
        self._reader_thread.start()

    def _read(self):
        try:
            result = self.reader(self.store)
        except Exception as error:
            result = SessionLoad(error=error)
        self.loading = False
        if not self._cancelled.is_set():
            try:
                self._loaded.emit(result)
            except RuntimeError:
                # The user may have destroyed the window while IO was pending.
                self._cancelled.set()

    @Slot(object)
    def _apply(self, result):
        if self._cancelled.is_set():
            return
        try:
            restored = self.window.apply_last_project(result)
            if result.error is None:
                self.window.statusBar().showMessage('Obra lista.' if restored else 'Listo.')
        finally:
            self.window.setEnabled(True)
        self.documentReady.emit()
        if not self._cancelled.is_set():
            self._bridge_thread = Thread(target=self._start_bridge, name='MetradosStartupCAD', daemon=True)
            self._bridge_thread.start()

    def _start_bridge(self):
        if self._cancelled.is_set():
            return
        try:
            self.bridge.start()
        except Exception as error:
            self.bridge.last_error = str(error)
        finally:
            if self._cancelled.is_set():
                self.bridge.stop()

    def cancel(self):
        self._cancelled.set()

    def shutdown(self):
        """Called after the UI event loop exits, never while painting the window."""
        self.cancel()
        if self._bridge_thread is not None:
            self._bridge_thread.join(timeout=5)
            if self._bridge_thread.is_alive():
                return  # Its finally block owns cleanup when start returns.
        self.bridge.stop()
