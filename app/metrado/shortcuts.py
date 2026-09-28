"""Discoverable and user-configurable keyboard navigation."""
from dataclasses import dataclass
import sqlite3
import unicodedata

from PySide6.QtCore import QEvent, QItemSelectionModel, QObject, QSize, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QDialog, QDialogButtonBox, QHeaderView,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QKeySequenceEdit, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from metrado.database import ConflictError
from metrado.shortcut_store import normalize_shortcuts


def searchable(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.casefold())
                   if not unicodedata.combining(c))


def keys(action):
    return ' / '.join(key.toString(QKeySequence.NativeText) for key in action.shortcuts())


def tag_action(action, action_id, category, base_tooltip=None):
    """Attach stable configuration metadata to an existing QAction."""
    action.setObjectName('shortcut.' + action_id)
    action.setProperty('shortcut_id', action_id)
    action.setProperty('shortcut_category', category)
    action.setProperty('base_tooltip', base_tooltip or action.toolTip() or action.text())
    return action


@dataclass(frozen=True)
class ShortcutBinding:
    action_id: str
    category: str
    title: str
    action: QAction
    defaults: tuple


# These belong to cell/text navigation and remain stable so editing cannot be
# made inaccessible through an accidental assignment.
RESERVED = {
    '/', 'F2', 'Return', 'Enter', 'Esc', 'Tab', 'Shift+Tab', 'Shift+Space',
    'Ctrl+A', 'Ctrl+Home', 'Ctrl+End',
}


def validate_configuration(configuration, known_ids=None):
    normalized = normalize_shortcuts(configuration)
    if known_ids is not None and not set(normalized) <= set(known_ids):
        raise ValueError('La configuración contiene una acción que esta versión no reconoce.')
    reserved = {QKeySequence(value).toString(QKeySequence.PortableText).casefold()
                for value in RESERVED}
    owners = {}
    for action_id, alternatives in normalized.items():
        for shortcut in alternatives:
            key = shortcut.casefold()
            if key in reserved:
                raise ValueError(f'«{shortcut}» está reservado para editar o navegar por la planilla.')
            if key in owners:
                raise ValueError(
                    f'«{shortcut}» está repetido en «{owners[key]}» y «{action_id}».')
            owners[key] = action_id
    return normalized


class ShortcutDialog(QDialog):
    """Searchable two-shortcut editor with immediate conflict feedback."""
    def __init__(self, bindings, current, parent=None):
        super().__init__(parent)
        self.bindings = sorted(
            bindings, key=lambda binding: (searchable(binding.category),
                                            searchable(binding.title)))
        self.defaults = {binding.action_id: list(binding.defaults)
                         for binding in self.bindings}
        self.editors = {}
        self.setWindowTitle('Configurar atajos de teclado')
        self.resize(820, 620)
        layout = QVBoxLayout(self)
        intro = QLabel(
            'Asigna hasta dos combinaciones por acción. Puedes borrar una combinación con el botón '
            'del campo. Enter, Esc, Tab, F2 y las teclas propias de la planilla permanecen reservadas.')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Buscar acción o categoría…')
        self.search.setClearButtonEnabled(True)
        layout.addWidget(self.search)
        self.table = QTableWidget(len(self.bindings), 4)
        self.table.setHorizontalHeaderLabels(
            ['Categoría', 'Acción', 'Atajo principal', 'Atajo alternativo'])
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        for row, binding in enumerate(self.bindings):
            category = QTableWidgetItem(binding.category)
            title = QTableWidgetItem(binding.title)
            category.setFlags(category.flags() & ~Qt.ItemIsEditable)
            title.setFlags(title.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, category)
            self.table.setItem(row, 1, title)
            values = current.get(binding.action_id, list(binding.defaults))
            row_editors = []
            for slot in range(2):
                editor = QKeySequenceEdit()
                editor.setClearButtonEnabled(True)
                if hasattr(editor, 'setMaximumSequenceLength'):
                    editor.setMaximumSequenceLength(1)
                if slot < len(values):
                    editor.setKeySequence(QKeySequence.fromString(
                        values[slot], QKeySequence.PortableText))
                editor.keySequenceChanged.connect(self.refresh)
                self.table.setCellWidget(row, slot + 2, editor)
                row_editors.append(editor)
            self.editors[binding.action_id] = row_editors
        layout.addWidget(self.table, 1)
        controls = QHBoxLayout()
        self.clear_button = QPushButton('Quitar atajos de la acción')
        self.defaults_button = QPushButton('Restaurar predeterminados')
        controls.addWidget(self.clear_button)
        controls.addStretch(1)
        controls.addWidget(self.defaults_button)
        layout.addLayout(controls)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setStyleSheet('color: #ff7b86;')
        layout.addWidget(self.error)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Save).setText('Guardar')
        self.buttons.button(QDialogButtonBox.Cancel).setText('Cancelar')
        layout.addWidget(self.buttons)
        self.search.textChanged.connect(self.filter)
        self.clear_button.clicked.connect(self.clear_current)
        self.defaults_button.clicked.connect(self.restore_defaults)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.table.setCurrentCell(0, 1)
        self.refresh()

    def configuration(self):
        configuration = {}
        for binding in self.bindings:
            values = []
            for editor in self.editors[binding.action_id]:
                value = editor.keySequence().toString(QKeySequence.PortableText)
                if value:
                    values.append(value)
            configuration[binding.action_id] = values
        try:
            return validate_configuration(configuration, self.editors)
        except ValueError as error:
            message = str(error)
            for binding in self.bindings:
                message = message.replace(
                    f'«{binding.action_id}»', f'«{binding.title}»')
            raise ValueError(message) from error

    def refresh(self, *args):
        for row_editors in self.editors.values():
            for editor in row_editors:
                editor.setStyleSheet('')
        try:
            self.configuration()
            self.error.setText('')
            self.buttons.button(QDialogButtonBox.Save).setEnabled(True)
        except ValueError as error:
            self.error.setText(str(error))
            self.buttons.button(QDialogButtonBox.Save).setEnabled(False)

    def filter(self, text):
        words = searchable(text).split()
        first_visible = None
        for row, binding in enumerate(self.bindings):
            haystack = searchable(binding.category + ' ' + binding.title)
            hidden = not all(word in haystack for word in words)
            self.table.setRowHidden(row, hidden)
            if not hidden and first_visible is None:
                first_visible = row
        current = self.table.currentRow()
        if first_visible is not None and (current < 0 or self.table.isRowHidden(current)):
            self.table.setCurrentCell(first_visible, 1)
        self.clear_button.setEnabled(first_visible is not None)

    def clear_current(self):
        row = self.table.currentRow()
        if row < 0:
            return
        binding = self.bindings[row]
        for editor in self.editors[binding.action_id]:
            editor.clear()
        self.refresh()

    def restore_defaults(self):
        for binding in self.bindings:
            values = self.defaults[binding.action_id]
            for slot, editor in enumerate(self.editors[binding.action_id]):
                editor.setKeySequence(QKeySequence(values[slot]) if slot < len(values)
                                      else QKeySequence())
        self.refresh()

    def accept(self):
        try:
            self.configuration()
        except ValueError:
            self.refresh()
            return
        super().accept()


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
    def __init__(self, window, store):
        super().__init__(window)
        self.window = window
        self.workspace = window.workspace
        self.store = store
        self.memory = {}
        self.actions = {}
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
            tag_action(action, 'navigate.' + name, 'Navegar', text)
            window.addAction(action)
            menu.addAction(action)
            self.actions[name] = action
        help_menu = window.menuBar().addMenu('Ayuda')
        action = QAction('Atajos de teclado…', window)
        action.setShortcut('F1')
        action.triggered.connect(self.help)
        tag_action(action, 'help.reference', 'Ayuda', 'Consultar atajos de teclado')
        window.addAction(action)
        help_menu.addAction(action)
        self.actions['help'] = action
        configure = QAction('Configurar atajos…', window)
        configure.setShortcut('Ctrl+Alt+K')
        configure.triggered.connect(self.configure_shortcuts)
        tag_action(configure, 'help.configure_shortcuts', 'Ayuda',
                   'Cambiar las combinaciones de teclas')
        window.addAction(configure)
        help_menu.addAction(configure)
        self.actions['configure'] = configure
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
        self.commands = [
            *window.command_actions, *window.row_actions.values(), window.undo_action,
            window.redo_action, window.export_action, window.import_excel_action,
            window.export_excel_action, window.swelling_action, window.catalog_action,
            window.distribution_format_action, window.hooks_action,
            window.update_steel_action, *self.actions.values(),
        ]
        self.bindings = []
        for command in self.commands:
            action_id = command.property('shortcut_id')
            category = command.property('shortcut_category')
            if not action_id or not category:
                raise ValueError(f'La acción «{command.text()}» no tiene un identificador de atajo.')
            defaults = tuple(sequence.toString(QKeySequence.PortableText)
                             for sequence in command.shortcuts())
            self.bindings.append(ShortcutBinding(
                action_id, category, command.text().replace('&', ''), command, defaults))
        self.defaults = {binding.action_id: list(binding.defaults)
                         for binding in self.bindings}
        self.configuration = dict(self.defaults)
        self.revision = None
        self.load_configuration()
        window.table.installEventFilter(self)
        window.navigator.installEventFilter(self)
        window.table.selectionModel().currentChanged.connect(self.remember)

    @property
    def known_ids(self):
        return {binding.action_id for binding in self.bindings}

    def load_configuration(self):
        try:
            stored, self.revision = self.store.read()
            configuration = {key: list(value) for key, value in self.defaults.items()}
            configuration.update({key: value for key, value in stored.items()
                                  if key in self.known_ids})
            self.apply_configuration(configuration)
        except (OSError, ValueError, sqlite3.Error) as error:
            self.revision = None
            self.apply_configuration(self.defaults)
            self.actions['configure'].setToolTip(
                'No se pudo leer la configuración global de atajos: ' + str(error))

    def apply_configuration(self, configuration):
        configuration = validate_configuration(configuration, self.known_ids)
        if set(configuration) != self.known_ids:
            raise ValueError('La configuración debe incluir todas las acciones disponibles.')
        by_id = {binding.action_id: binding for binding in self.bindings}
        for action_id, alternatives in configuration.items():
            action = by_id[action_id].action
            action.setShortcuts([
                QKeySequence.fromString(value, QKeySequence.PortableText)
                for value in alternatives])
            base = action.property('base_tooltip') or action.text().replace('&', '')
            action.setToolTip(base + (f' ({keys(action)})' if keys(action) else ''))
        self.configuration = {key: list(value) for key, value in configuration.items()}
        self.window._selection_status()

    def configure_shortcuts(self):
        self.window._commit_editors()
        try:
            stored, revision = self.store.read()
            current = {key: list(value) for key, value in self.defaults.items()}
            current.update({key: value for key, value in stored.items()
                            if key in self.known_ids})
            current = validate_configuration(current, self.known_ids)
            dialog = ShortcutDialog(self.bindings, current, self.window)
            if dialog.exec() != QDialog.Accepted:
                dialog.deleteLater()
                return
            configuration = dialog.configuration()
            dialog.deleteLater()
            self.revision = self.store.save(configuration, revision)
            self.apply_configuration(configuration)
            self.window.statusBar().showMessage(
                'Atajos guardados y aplicados para todos los proyectos.', 7000)
        except (ConflictError, OSError, ValueError, sqlite3.Error) as error:
            QMessageBox.warning(self.window, 'Configurar atajos', str(error))

    def status_hint(self):
        parts = ['/: referencia']
        for action_id, label in (
            ('navigate.panels', 'panel'), ('navigate.find', 'buscar'),
            ('navigate.commands', 'comandos'), ('help.reference', 'ayuda')):
            binding = next(binding for binding in self.bindings
                           if binding.action_id == action_id)
            shortcut = keys(binding.action)
            if shortcut:
                parts.append(f'{shortcut}: {label}')
        parts.append('Tab/Mayús+Tab: nivel')
        return ' · '.join(parts)

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
