"""Compact header and flat action strip, matching Gitbin's visual hierarchy."""
from PySide6.QtCore import QEvent, QObject, QRect, Qt
from PySide6.QtGui import QAction, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMenu, QSizePolicy, QStatusBar, QToolBar, QToolButton, QWidget, QWidgetAction,
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
    '↑ Subir': ('↑', 'Subir', 42),
    '↓ Bajar': ('↓', 'Bajar', 42),
    '→ Aumentar nivel': ('→', 'Nivel +', 48),
    '← Reducir nivel': ('←', 'Nivel −', 48),
    'Mover a…': ('↔', 'Mover a', 52),
    'Copiar': ('▱', 'Copiar', 46),
    'Pegar': ('▣', 'Pegar', 46),
    'Deshacer': ('↶', 'Deshacer', 58),
    'Rehacer': ('↷', 'Rehacer', 54),
    'Factor de esponjamiento…': ('FE', 'Esponjam.', 64),
    'Aplicar ganchos…': ('⌝', 'Ganchos', 56),
}


class ActionButton(QToolButton):
    """QAction supplies behavior; this painter supplies the reference's styling."""

    def __init__(self, action, parent=None, spec=None):
        super().__init__(parent)
        self.symbol, self.caption, width = spec or SPECS[action.text()]
        self.setDefaultAction(action)
        self.setAccessibleName(action.text())
        self.setFixedSize(width, 36)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAutoRaise(True)
        self.setMouseTracking(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        hovered = self.underMouse() and self.isEnabled()
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


class FlatAction(QWidgetAction):
    """Flat toolbar widget, ordinary menu entry when the toolbar overflows."""
    def __init__(self, source, toolbar, spec=None):
        super().__init__(toolbar)
        self.source = source
        self.spec = spec or SPECS[source.text()]
        source.changed.connect(self.sync)
        self.triggered.connect(source.trigger)
        self.sync()

    def sync(self):
        self.setText(self.source.text())
        self.setToolTip(self.source.toolTip())
        self.setEnabled(self.source.isEnabled())
        self.setVisible(self.source.isVisible())

    def createWidget(self, parent):
        return ActionButton(self.source, parent, self.spec) if isinstance(parent, QToolBar) else None


def add_flat_action(toolbar, action, spec=None):
    toolbar.addAction(FlatAction(action, toolbar, spec))


class ContextStatusBar(QStatusBar):
    """Single elided line; keep QStatusBar's timed messages and public API."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.context = ''
        self.summary = ''
        self.setFixedHeight(24)
        self.messageChanged.connect(self.refresh)

    def set_context(self, context, summary):
        self.context, self.summary = context, summary
        self.refresh()

    def line_text(self):
        message = self.currentMessage()
        return (message + ' · F1: ayuda' if message and message != self.summary else
                self.context + ' · ' + self.summary)

    def refresh(self, *_):
        self.setToolTip(self.line_text())
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#15171c'))
        painter.setPen(QColor('#30343d'))
        painter.drawLine(0, 0, self.width(), 0)
        painter.setFont(self.font())
        painter.setPen(QColor('#f0bc78' if self.currentMessage() and self.currentMessage() != self.summary else '#8e97a4'))
        rect = self.rect().adjusted(6, 0, -22, 0)
        painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter,
                         painter.fontMetrics().elidedText(self.line_text(), Qt.ElideRight, max(0, rect.width())))


def add_action(window, toolbar, text, callback, shortcut=None):
    action = QAction(text, window)
    if shortcut:
        action.setShortcut(shortcut)
    action.setToolTip(text + (f" ({shortcut})" if shortcut else ""))
    action.triggered.connect(lambda checked=False: callback())
    window.addAction(action)
    add_flat_action(toolbar, action)
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


class OverflowMenu(QObject):
    """Intercept the extension control so Qt cannot expand into a second row."""
    def __init__(self, toolbar):
        super().__init__(toolbar)
        self.toolbar = toolbar
        self.extension = toolbar.findChild(QToolButton, 'qt_toolbar_ext_button')
        self.extension.setStyleSheet('QToolButton { padding: 0; border: 0; background: transparent; }')
        self.extension.setToolTip('Más acciones')
        self.extension.setAccessibleName('Más acciones')
        self.menu = QMenu(toolbar)
        self.menu.aboutToShow.connect(self.populate)
        self.extension.installEventFilter(self)

    def populate(self):
        self.menu.clear()
        for action in self.toolbar.actions():
            if isinstance(action, FlatAction):
                button = self.toolbar.widgetForAction(action)
                if button is not None and not button.isVisible():
                    self.menu.addAction(action.source)

    def eventFilter(self, watched, event):
        mouse = event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton
        keyboard = event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space, Qt.Key_Down)
        if mouse or keyboard:
            self.menu.popup(self.extension.mapToGlobal(self.extension.rect().bottomLeft()))
            return True
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            return True
        return super().eventFilter(watched, event)


def action_toolbar(window):
    toolbar = QToolBar("Acciones", window)
    toolbar.setObjectName("actionStrip")
    toolbar.setMovable(False)
    toolbar.setFixedHeight(38)
    window.addToolBar(toolbar)
    # Qt can expand a toolbar into extra rows for widget actions. Force a menu
    # instead, keeping the user's one-row layout at every window width.
    toolbar.overflow = OverflowMenu(toolbar)
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
