"""Appearance adapted from Gitbin's QML palette; no dependency on Gitbin."""
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

FONT_FAMILY = "Segoe UI"
WINDOW = "#11151b"
PANEL = "#191e26"
SURFACE = "#171b22"
HEADER = "#1d232c"
INPUT = "#0f141a"
BORDER = "#303a46"
TEXT = "#e1e8f2"
MUTED = "#8e97a4"
ACCENT = "#25b9c4"
DETAIL = "#a6c6df"
CHAPTER = "#f08088"
WARNING = "#f0bc78"
WARNING_BACKGROUND = "#342624"
SELECTION = "#2c4051"

STYLE = """
QWidget { font-family: "Segoe UI"; font-size: 11px; color: #e1e8f2; }
QMainWindow, QDialog, QMessageBox, QInputDialog { background: #11151b; }
QLabel { background: transparent; }
QLabel#sheetHeading { color: #edf2f7; font-size: 16px; font-weight: 600; }
QLabel#sheetHint { color: #a8b4c3; padding: 3px 6px; font-size: 11px; }
QLabel#sheetNote { color: #8e97a4; font-size: 11px; }
QLabel#partidaHeading { color: #e1e8f2; font-weight: 600; padding: 4px 6px; }
QSplitter::handle { background: #303a46; }
QSplitter::handle:hover { background: #25b9c4; }
QTreeView#partidaNavigator::item { height: 28px; }
QTreeView QLineEdit, QTreeView QComboBox { padding: 1px 3px; border-radius: 0; }
QToolBar { background: #191e26; spacing: 6px; padding: 7px;
    border: 0; border-bottom: 1px solid #29313b; }
QToolBar::separator { background: #303a46; width: 1px; margin: 4px 5px; }
QToolBar#appHeader { background: #10141a; border-bottom: 1px solid #252b34; padding: 0; spacing: 0; }
QLabel#appBrand { color: #f0f2f5; font-size: 14px; font-weight: 600; }
QLabel#headerMeta { color: #788493; font-size: 8px; }
QLineEdit#projectTab { color: #e7ebf0; background: #1d232c; font-size: 11px;
    font-weight: 600; border: 1px solid #2c3440; border-bottom: 2px solid #25b9c4;
    border-radius: 0; padding: 0 12px; }
QToolBar#actionStrip { background: #191e26; border-bottom: 1px solid #29313b; padding: 0 7px; spacing: 1px; }
QToolBar#organizeStrip { padding: 3px 5px; spacing: 4px; }
QToolBar#organizeStrip QToolButton { padding: 3px 7px; }
QWidget#workspaceBand { background: #14181e; border-bottom: 1px solid #252d37; }
QLabel#workspaceCaption { color: #7d8897; font-size: 8px; font-weight: 600; }
QLabel#workspaceActive { color: #ffffff; font-size: 8px; font-weight: 600; border-bottom: 2px solid #25b9c4; }
QToolButton, QPushButton { color: #e1e8f2; background: #202d3a;
    border: 1px solid #42566b; border-radius: 3px; padding: 6px 10px; }
QToolButton:hover, QPushButton:hover { background: #2c4051; border-color: #5b7288; }
QToolButton:pressed, QPushButton:pressed { background: #365266; }
QToolButton:focus, QPushButton:focus, QPushButton:default { border-color: #25b9c4; }
QToolButton:disabled, QPushButton:disabled { color: #718091;
    background: #191e26; border-color: #2e3b49; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {
    color: #edf2f7; background: #0f141a; border: 1px solid #303a46;
    border-radius: 5px; padding: 6px 9px;
    selection-color: #edf2f7; selection-background-color: #365266; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QTextEdit:focus, QPlainTextEdit:focus { border-color: #25b9c4; }
QLineEdit#projectTitle { padding: 7px; font-size: 13px; }
QComboBox::drop-down { border: 0; width: 20px; }
QComboBox QAbstractItemView, QListView, QTreeView {
    color: #e1e8f2; background: #171b22; border: 1px solid #303a46;
    selection-background-color: #2c4051; selection-color: #edf2f7; }
QTableView { color: #e1e8f2; background: #171b22; border: 1px solid #303a46;
    selection-background-color: #2c4051; selection-color: #edf2f7; }
QTableView QLineEdit, QTableView QComboBox {
    padding: 1px 3px; border-radius: 0; border: 1px solid #25b9c4; }
QHeaderView { background: #1d232c; }
QHeaderView::section { background: #1d232c; color: #8e97a4; border: 0; }
QTableCornerButton::section { background: #1d232c; border: 1px solid #303a46; }
QStatusBar { color: #8e97a4; background: #15171c; border-top: 1px solid #30343d; }
QStatusBar::item { border: 0; }
QToolTip { color: #edf2f7; background: #202d3a; border: 1px solid #42566b; padding: 5px; }
QMenu { color: #e1e8f2; background: #191e26; border: 1px solid #303a46; padding: 4px; }
QMenu::item:selected { background: #2c4051; }
QScrollBar:vertical { background: #11151b; width: 12px; margin: 0; }
QScrollBar:horizontal { background: #11151b; height: 12px; margin: 0; }
QScrollBar::handle { background: #384554; border-radius: 4px; }
QScrollBar::handle:hover { background: #526575; }
QScrollBar::handle:vertical { min-height: 24px; margin: 2px; }
QScrollBar::handle:horizontal { min-width: 24px; margin: 2px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
"""


def apply_theme(window):
    app = QApplication.instance()
    app.setStyle("Fusion")
    palette = QPalette()
    for role, color in (
        (QPalette.Window, WINDOW), (QPalette.WindowText, TEXT),
        (QPalette.Base, INPUT), (QPalette.AlternateBase, HEADER),
        (QPalette.Text, TEXT), (QPalette.Button, PANEL),
        (QPalette.ButtonText, TEXT), (QPalette.Highlight, SELECTION),
        (QPalette.HighlightedText, "#edf2f7"), (QPalette.ToolTipBase, PANEL),
        (QPalette.ToolTipText, TEXT), (QPalette.PlaceholderText, MUTED),
        (QPalette.Light, BORDER), (QPalette.Midlight, BORDER),
        (QPalette.Mid, BORDER), (QPalette.Dark, WINDOW),
        (QPalette.Shadow, "#090c10"), (QPalette.Link, ACCENT),
    ):
        palette.setColor(role, QColor(color))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor("#718091"))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#718091"))
    app.setPalette(palette)
    font = QFont(FONT_FAMILY)
    font.setPixelSize(11)
    app.setFont(font)
    app.setStyleSheet(STYLE)
    window.setPalette(palette)
