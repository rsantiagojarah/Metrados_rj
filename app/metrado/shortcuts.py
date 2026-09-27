"""Discoverable keyboard navigation; commands reuse the application's QActions."""
import unicodedata

from PySide6.QtCore import QEvent, QItemSelectionModel, QObject, QSize, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QDialog, QDialogButtonBox, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QVBoxLayout,
)


def searchable(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.casefold())
                   if not unicodedata.combining(c))


def keys(action):
    return ' / '.join(key.toString(QKeySequence.NativeText) for key in action.shortcuts())


class FinderDialog(QDialog):
    """One keyboard-first picker for commands, partidas and shortcut reference."""
    def __init__(self, title, entries, parent=None, reference=False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(690, 470)
        self.entries, self.reference = entries, reference
        self.chosen = None
        self._search_text = [
            searchable(title + ' ' + shortcut + ' ' + (value.toolTip() if isinstance(value, QAction) else ''))
            for title, shortcut, value, _ in entries]
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Escribe para filtrar… (no hace falta escribir tildes)')
        self.search.setClearButtonEnabled(True)
        layout.addWidget(self.search)
        self.results = QListWidget()
        self.results.setUniformItemSizes(True)
        layout.addWidget(self.results, 1)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        hint = QLabel('↑ / ↓ elegir · Enter confirmar · Esc cerrar' if not reference else
                      'Dentro de un editor, Ctrl+C/V/Z actúan sobre el texto. Esc cancela la edición. '
                      'Tab cambia nivel solo en Ítem/Descripción fuera de edición.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText('Cerrar' if reference else 'Elegir')
        self.buttons.button(QDialogButtonBox.Cancel).setText('Cancelar')
        if reference:
            self.buttons.button(QDialogButtonBox.Cancel).hide()
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.search.textChanged.connect(self.filter)
        self.search.installEventFilter(self)
        self.results.itemDoubleClicked.connect(lambda *_: self.accept())
        self.results.currentRowChanged.connect(self.update_button)
        self.filter('')
        self.search.setFocus()

    def filter(self, text):
        words = searchable(text).split()
        self.results.clear()
        first_enabled = None
        for index, (title, shortcut, _, enabled) in enumerate(self.entries):
            if not all(word in self._search_text[index] for word in words):
                continue
            caption = title + ('    [' + shortcut + ']' if shortcut else '')
            if not enabled and not self.reference:
                caption += ' — no disponible en esta selección'
            item = QListWidgetItem(caption)
            item.setSizeHint(QSize(0, 28))
            item.setToolTip(caption)
            item.setData(Qt.UserRole, index)
            if not enabled and not self.reference:
                item.setFlags(item.flags() & ~(Qt.ItemIsEnabled | Qt.ItemIsSelectable))
            elif first_enabled is None:
                first_enabled = self.results.count()
            self.results.addItem(item)
        self.results.setCurrentRow(-1 if first_enabled is None else first_enabled)
        self.summary.setText(f'{self.results.count()} resultado(s)' if self.results.count() else 'Sin coincidencias.')
        self.update_button()

    def update_button(self, *args):
        item = self.results.currentItem()
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(
            self.reference or bool(item and item.flags() & Qt.ItemIsEnabled))

    def eventFilter(self, watched, event):
        if watched is self.search and event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Up, Qt.Key_Down):
            step = 1 if event.key() == Qt.Key_Down else -1
            index = self.results.currentRow() + step
            while 0 <= index < self.results.count():
                if self.results.item(index).flags() & Qt.ItemIsEnabled:
                    self.results.setCurrentRow(index)
                    self.results.scrollToItem(self.results.item(index))
                    break
                index += step
            return True
        return super().eventFilter(watched, event)

    def accept(self):
        if not self.reference:
            item = self.results.currentItem()
            if not item or not item.flags() & Qt.ItemIsEnabled:
                return
            self.chosen = self.entries[item.data(Qt.UserRole)][2]
        super().accept()


class KeyboardController(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.workspace = window.workspace
        self.memory = {}
        self.actions = {}
        self.commands = [
            *window.command_actions, *window.row_actions.values(), window.undo_action, window.redo_action,
            window.export_action, window.swelling_action, window.catalog_action,
            window.hooks_action, window.update_steel_action,
        ]
        menu = window.menuBar().addMenu('Navegar')
        definitions = (
            ('panels', 'Alternar paneles: Partidas / Planilla', ['F6', 'Shift+F6'], self.toggle_panel),
            ('partidas', 'Ir al panel de partidas', ['Ctrl+1'], lambda: self.focus_panel(True)),
            ('sheet', 'Ir al panel de planilla', ['Ctrl+2'], lambda: self.focus_panel(False)),
            ('previous', 'Partida anterior', ['Ctrl+PgUp'], lambda: self.next_item(-1)),
            ('next', 'Partida siguiente', ['Ctrl+PgDown'], lambda: self.next_item(1)),
            ('find', 'Buscar partida…', ['Ctrl+F'], self.find_item),
            ('commands', 'Buscar comando…', ['Ctrl+K'], self.command_palette),
            ('title', 'Editar nombre de la obra', ['Ctrl+L'], self.focus_title),
            ('expand', 'Expandir todos los títulos', [], window.navigator.expandAll),
            ('collapse', 'Contraer todos los títulos', [], window.navigator.collapseAll),
        )
        for name, text, shortcuts, callback in definitions:
            action = QAction(text, window)
            action.setShortcuts(shortcuts)
            action.triggered.connect(lambda checked=False, fn=callback: fn())
            window.addAction(action)
            menu.addAction(action)
            self.actions[name] = action
            self.commands.append(action)
        help_menu = window.menuBar().addMenu('Ayuda')
        action = QAction('Atajos de teclado…', window)
        action.setShortcut('F1')
        action.triggered.connect(self.help)
        window.addAction(action)
        help_menu.addAction(action)
        self.actions['help'] = action
        self.commands.append(action)
        # Widget scope keeps spreadsheet commands out of text editors/dialogs.
        for action, shortcut in ((window.hooks_action, 'Ctrl+Shift+H'),
                                  (window.swelling_action, 'Ctrl+Shift+E')):
            action.setShortcut(shortcut)
            action.setShortcutContext(Qt.WidgetShortcut)
            window.table.addAction(action)
        for action, shortcut in ((window.catalog_action, 'Ctrl+Shift+A'),
                                  (window.update_steel_action, 'Ctrl+Shift+U'),
                                  (window.export_action, 'Ctrl+Shift+J')):
            action.setShortcut(shortcut)
            window.addAction(action)
        for action in self.commands:
            if keys(action):
                tooltip = action.toolTip()
                action.setToolTip(tooltip if keys(action) in tooltip else tooltip + ' · ' + keys(action))
        window.table.installEventFilter(self)
        window.navigator.installEventFilter(self)
        window.table.selectionModel().currentChanged.connect(self.remember)

    def remember(self, current=None, previous=None):
        index = self.window.table.currentIndex() if current is None else current
        if self.workspace._resetting or not index.isValid():
            return
        model = self.window.model
        row = index.row()
        if row >= len(model.rows) or model.rows[row]['kind'] not in ('detail', 'detail_group'):
            return
        owner = model.outline.owners[row]
        if owner is not None:
            self.memory[model.rows[owner]['id']] = (model.rows[row]['id'], index.column())

    def focus_panel(self, tree):
        self.remember()
        self.window._commit_editors()
        if tree:
            self.window.navigator.setFocus()
            return
        index = self.window.navigator.currentIndex()
        owner = self.workspace.outline.source_row(index)
        if owner is None or self.window.model.rows[owner]['kind'] != 'item':
            self.window.statusBar().showMessage('Elige una partida en el panel izquierdo; Enter abre su planilla.', 5000)
            self.window.navigator.setFocus()
            return
        row, column = owner, 1
        remembered = self.memory.get(self.window.model.rows[owner]['id'])
        if remembered:
            candidate = self.workspace.outline.by_id.get(remembered[0])
            if candidate is not None and self.window.model.outline.owners[candidate] == owner:
                row, column = candidate, remembered[1]
        if row == owner and owner + 1 < self.window.model.outline.ends[owner]:
            row = owner + 1
        if self.window.table.isColumnHidden(column):
            column = 1
        self.workspace.navigation_active = False
        self.workspace.select(row, column)
        self.window.table.setFocus()

    def toggle_panel(self):
        self.focus_panel(not self.workspace.navigation_active)

    def open_item(self, row, tree=False):
        self.remember()
        self.window._commit_editors()
        self.workspace.navigation_active = True
        self.workspace.select(row, 1)
        if not tree:
            self.focus_panel(False)

    def next_item(self, direction):
        self.remember()
        self.window._commit_editors()
        model = self.window.model
        items = [r for r in self.workspace.outline.node_rows if model.rows[r]['kind'] == 'item']
        current = self.window.table.currentIndex().row()
        owner = model.outline.owners[current] if 0 <= current < len(model.rows) else None
        anchor = owner if owner is not None else current
        candidates = [r for r in items if (r > anchor if direction > 0 else r < anchor)]
        if not candidates:
            self.window.statusBar().showMessage('No hay otra partida en esa dirección.', 4000)
            return
        self.open_item(candidates[0] if direction > 0 else candidates[-1], self.workspace.navigation_active)

    def focus_title(self):
        self.remember()
        self.window._commit_editors()
        self.window.title_edit.setFocus()
        self.window.title_edit.selectAll()

    def picker(self, title, entries, reference=False):
        from_title = QApplication.focusWidget() is self.window.title_edit
        self.window._commit_editors()
        focus = (self.window.title_edit if from_title else
                 self.window.navigator if self.workspace.navigation_active else self.window.table)
        dialog = FinderDialog(title, entries, self.window, reference)
        accepted = dialog.exec() == QDialog.Accepted
        self.window.activateWindow()
        focus.setFocus()
        chosen = dialog.chosen if accepted else None
        dialog.deleteLater()
        return chosen

    def find_item(self):
        self.window._commit_editors()
        entries = []
        for row in self.workspace.outline.node_rows:
            entry = self.window.model.rows[row]
            if entry['kind'] == 'item':
                code, title, unit = entry['cells'][:3]
                total = self.window.model.data(self.window.model.index(row, 13))
                entries.append((f'{code} · {title} · {unit} · Total: {total}', '', row, True))
        row = self.picker('Buscar partida', entries)
        if row is not None:
            self.open_item(row)

    def command_palette(self):
        self.window._commit_editors()
        entries = [(a.text().replace('&', ''), keys(a), a, a.isEnabled()) for a in self.commands]
        action = self.picker('Buscar comando', entries)
        if action is not None and action.isEnabled():
            action.trigger()

    def help(self):
        entries = [(a.text().replace('&', ''), keys(a) or 'Ctrl+K → buscar comando', None, True)
                   for a in self.commands]
        entries.extend((text, shortcut, None, True) for text, shortcut in (
            ('Referenciar total de otra partida (en Descripción del detalle)', '/'),
            ('Abrir la partida seleccionada (desde Partidas)', 'Enter'),
            ('Volver a Partidas (desde Planilla, sin editar)', 'Esc'),
            ('Seleccionar fila completa (fuera de edición)', 'Shift+Space'),
            ('Ir a primera / última fila del panel', 'Ctrl+Home / Ctrl+End'),
            ('Desplazarse por celdas / páginas', 'Flechas / PgUp / PgDown'),
            ('Extender selección / seleccionar todo el panel', 'Shift+Flechas / Ctrl+A'),
            ('Editar celda / confirmar / cancelar edición', 'F2 / Enter / Esc'),
            ('Aumentar / reducir nivel en Ítem o Descripción', 'Tab / Shift+Tab'),
            ('Abrir / cerrar título en Partidas', 'Derecha / Izquierda'),
        ))
        self.picker('Atajos de teclado', entries, reference=True)

    def eventFilter(self, view, event):
        if event.type() != QEvent.KeyPress or view.state() == QAbstractItemView.EditingState:
            return super().eventFilter(view, event)
        key, mods = event.key(), event.modifiers()
        if mods == Qt.NoModifier and view is self.window.navigator and key in (Qt.Key_Return, Qt.Key_Enter):
            self.focus_panel(False)
            return True
        if mods == Qt.NoModifier and view is self.window.table and key == Qt.Key_Escape:
            self.focus_panel(True)
            return True
        if key == Qt.Key_Space and mods == Qt.ShiftModifier:
            current = view.currentIndex()
            if current.isValid():
                view.selectionModel().select(current, QItemSelectionModel.Select | QItemSelectionModel.Rows)
            return True
        return super().eventFilter(view, event)
