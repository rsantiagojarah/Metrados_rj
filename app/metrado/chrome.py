"""Compact header and flat action strip, matching Gitbin's visual hierarchy."""
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QAction, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QSizePolicy, QToolBar, QToolButton, QWidget,
)

SPECS = {
    "Nueva planilla": ("+", "Nueva", 54),
    "Abrir…": ("▱", "Abrir", 54),
    "Guardar": ("↓", "Guardar", 54),
    "Guardar como…": ("↧", "Guardar como", 78),
    "Cargar ejemplo": ("≡", "Ejemplo", 54),
    "+ Título": ("▤", "Título", 54),
    "+ Subtítulo": ("↳", "Subtítulo", 62),
    "+ Partida": ("+", "Partida", 54),
    "+ Detalle": ("↳", "Detalle", 54),
    "+ Título de detalle": ("T", "Título detalle", 78),
    "+ Subtítulo de detalle": ("↳", "Subt. detalle", 78),
    "Cantidad directa…": ("∑", "Cant. directa", 74),
    "Eliminar fila…": ("×", "Eliminar", 54),
}


class ActionButton(QToolButton):
    """QAction supplies behavior; this painter supplies the reference's styling."""

    def __init__(self, action, parent=None):
        super().__init__(parent)
        self.symbol, self.caption, width = SPECS[action.text()]
        self.setDefaultAction(action)
        self.setAccessibleName(action.text())
        self.setFixedSize(width, 36)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAutoRaise(True)
        self.setMouseTracking(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        hovered = self.underMouse()
        if self.isDown() or hovered:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#33404d" if self.isDown() else "#29313b"))
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 2, 2)
        icon_font = QFont("Segoe UI")
        icon_font.setPixelSize(14)
        painter.setFont(icon_font)
        painter.setPen(QColor("#ffffff" if hovered else "#b4bbc5" if self.isEnabled() else "#5f6b79"))
        painter.drawText(QRect(0, 1, self.width(), 18), Qt.AlignCenter, self.symbol)
        label_font = QFont("Segoe UI")
        label_font.setPixelSize(9)
        painter.setFont(label_font)
        painter.setPen(QColor("#ffffff" if hovered else "#9ca5b2" if self.isEnabled() else "#5f6b79"))
        painter.drawText(QRect(0, 19, self.width(), 15), Qt.AlignCenter, self.caption)
        if self.hasFocus():
            painter.setPen(QPen(QColor("#25b9c4"), 1))
            painter.drawLine(6, self.height() - 2, self.width() - 6, self.height() - 2)

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()


def add_action(window, toolbar, text, callback, shortcut=None):
    action = QAction(text, window)
    if shortcut:
        action.setShortcut(shortcut)
    action.setToolTip(text + (f" ({shortcut})" if shortcut else ""))
    action.triggered.connect(lambda checked=False: callback())
    window.addAction(action)
    toolbar.addWidget(ActionButton(action, toolbar))
    return action


def header_toolbar(window, title_edit):
    toolbar = QToolBar("Proyecto", window)
    toolbar.setObjectName("appHeader")
    toolbar.setMovable(False)
    toolbar.setFixedHeight(34)
    toolbar.setContentsMargins(0, 0, 0, 0)
    body = QWidget()
    body.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    layout = QHBoxLayout(body)
    layout.setContentsMargins(9, 0, 9, 0)
    layout.setSpacing(8)
    brand = QLabel("<span style='color:#62cfda'>▦</span>  Metra<span style='color:#62cfda'>dos</span>")
    brand.setObjectName("appBrand")
    brand.setFixedWidth(104)
    layout.addWidget(brand)
    title_edit.setObjectName("projectTab")
    title_edit.setFixedSize(300, 32)
    layout.addWidget(title_edit)
    layout.addStretch()
    label = QLabel("ARCHIVO LOCAL")
    label.setObjectName("headerMeta")
    layout.addWidget(label)
    toolbar.addWidget(body)
    window.addToolBar(toolbar)
    window.addToolBarBreak()
    return toolbar


def action_toolbar(window):
    toolbar = QToolBar("Acciones", window)
    toolbar.setObjectName("actionStrip")
    toolbar.setMovable(False)
    toolbar.setFixedHeight(38)
    window.addToolBar(toolbar)
    return toolbar


def workspace_band():
    band = QWidget()
    band.setObjectName("workspaceBand")
    band.setFixedHeight(30)
    layout = QHBoxLayout(band)
    layout.setContentsMargins(12, 0, 12, 0)
    label = QLabel("METRADOS DE OBRA")
    label.setObjectName("workspaceCaption")
    layout.addWidget(label)
    layout.addStretch()
    active = QLabel("PLANILLA")
    active.setObjectName("workspaceActive")
    active.setAlignment(Qt.AlignCenter)
    active.setFixedSize(70, 30)
    layout.addWidget(active)
    return band
