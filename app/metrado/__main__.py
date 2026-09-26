import sys

from PySide6.QtWidgets import QApplication, QMessageBox

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
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
