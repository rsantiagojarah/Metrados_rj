import sys

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer

from metrado.autocad_bridge import AutoCadBridgeServer
from metrado.autocad_integration import AutoCadRequestDispatcher
from metrado.messages import UNAVAILABLE
from metrado.project_session import LastProjectStore
from metrado.startup import StartupCoordinator


def main():
    app = QApplication(sys.argv)
    try:
        import metrado._enlace as enlace
    except ImportError:
        QMessageBox.critical(None, "Metrados", UNAVAILABLE)
        return 1
    from metrado.window import PlantillaWindow

    store = LastProjectStore()
    window = PlantillaWindow(enlace, session_store=store, initial_rows=[])
    dispatcher = AutoCadRequestDispatcher(window)
    bridge = AutoCadBridgeServer(request_handler=dispatcher.dispatch)
    window.autocad_bridge = bridge
    window.autocad_dispatcher = dispatcher
    startup = StartupCoordinator(window, store, bridge)
    app.aboutToQuit.connect(startup.cancel)
    window.show()
    QTimer.singleShot(0, startup.start)
    try:
        return app.exec()
    finally:
        startup.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
