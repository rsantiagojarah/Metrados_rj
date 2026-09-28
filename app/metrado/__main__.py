import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from metrado.autocad_bridge import AutoCadBridgeServer, BridgeError
from metrado.autocad_integration import AutoCadRequestDispatcher
from metrado.messages import UNAVAILABLE


def main():
    app = QApplication(sys.argv)
    try:
        import metrado._enlace as enlace
    except ImportError:
        QMessageBox.critical(None, "Metrados", UNAVAILABLE)
        return 1
    from metrado.window import PlantillaWindow

    window = PlantillaWindow(enlace)
    dispatcher = AutoCadRequestDispatcher(window)
    bridge = AutoCadBridgeServer(request_handler=dispatcher.dispatch)
    try:
        bridge.start()
    except (BridgeError, OSError) as error:
        bridge.last_error = str(error)
    window.autocad_bridge = bridge
    window.autocad_dispatcher = dispatcher
    app.aboutToQuit.connect(bridge.stop)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
