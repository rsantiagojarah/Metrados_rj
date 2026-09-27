from pathlib import Path
import sqlite3
from shiboken6 import isValid

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QInputDialog, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox,
    QToolBar, QVBoxLayout, QWidget,
)

from metrado.grid import SheetModel, SheetView
from metrado.chrome import add_action, action_toolbar, header_toolbar, workspace_band
from metrado.theme import apply_theme
from metrado.sheet import (
    example_rows, new_row, parent_item, subtree_end, write_project,
)
from metrado.steel import first_steel_item
from metrado.hierarchy import (
    MAX_ROWS, MEASUREMENT_KINDS, change_level, container, materialize, move_sibling, move_to, renumber,
)
from metrado.clipboard import ROW_MIME, cell_text, decode_rows, encode_rows, insert_rows, parse_tsv, tsv
from metrado.organize import DestinationDialog
from metrado.database import open_document, write_database
from metrado.history import ProjectTitle


class PlantillaWindow(QMainWindow):
    def __init__(self, enlace):
        super().__init__()
        self._enlace, self._path, self._dirty = enlace, None, False
        self._revision = None
        self.resize(1480, 780)
        self.setMinimumSize(900, 480)
        self.model = SheetModel(enlace, example_rows())
        self.model.setParent(self)
        self.table = SheetView(self.model)
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(6, 0, 6, 6)
        layout.setSpacing(6)
        layout.addWidget(workspace_band())
        self.title_edit = QLineEdit("Ejemplo de planilla de metrado")
        self._committed_title = self.title_edit.text()
        self.title_edit.setPlaceholderText("Nombre de la obra o proyecto")
        header_toolbar(self, self.title_edit)
        hint = QLabel("Organizar: Tab / Mayús+Tab en Ítem o Descripción · Alt+↑ / ↓ mueve el bloque · Clic derecho: más opciones · Ctrl+C / Ctrl+V")
        hint.setObjectName("sheetHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addWidget(self.table, 1)
        note = QLabel("Acero: Lon. = Elem. simil. × (Largo + gancho + empalme) × N.º de veces; Kg = Lon. × kg/m. Totales por partida.")
        note.setObjectName("sheetNote")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.setCentralWidget(central)
        files = action_toolbar(self)
        self._action(files, "Nueva planilla", self.new_project, "Ctrl+N")
        self._action(files, "Abrir…", self.open_project, "Ctrl+O")
        self._action(files, "Guardar", self.save_project, "Ctrl+S")
        self._action(files, "Guardar como…", lambda: self.save_project(True), "Ctrl+Shift+S")
        files.addSeparator()
        self._action(files, "Cargar ejemplo", self.load_example)
        files.addSeparator()
        edit = files
        self._action(edit, "+ Título", lambda: self.add_row("chapter"), "Alt+C")
        self._action(edit, "+ Subtítulo", lambda: self.add_row("subtitle"), "Alt+S")
        self._action(edit, "+ Partida", lambda: self.add_row("item"), "Ctrl+Shift+N")
        self._action(edit, "+ Detalle", lambda: self.add_row("detail"), "Ctrl+Return")
        self._action(edit, "+ Título de detalle", lambda: self.add_row('detail_group'), 'Alt+G')
        self._action(edit, "+ Subtítulo de detalle", lambda: self.add_row('detail_subgroup'), 'Alt+Shift+G')
        edit.addSeparator()
        self._action(edit, "Cantidad directa…", self.direct_quantity, "Ctrl+D")
        self._action(edit, "Eliminar fila…", self.remove_row, "Ctrl+Delete")
        self._organize_actions()
        self._history_actions()
        self.model.changed.connect(self._changed)
        self.title_edit.textEdited.connect(self._changed)
        self.title_edit.editingFinished.connect(self._commit_title)
        self.model.undo_stack.indexChanged.connect(self._changed)
        self.model.undo_stack.cleanChanged.connect(self._changed)
        self.model.selectionRequested.connect(self._select)
        self.table.selectionModel().currentChanged.connect(self._selection_status)
        apply_theme(self)
        self._refresh_title()
        self._selection_status()
        self._focus_steel()

    def _focus_steel(self):
        index = first_steel_item(self.model.rows)
        if index is not None:
            self._select(index)

    def _action(self, toolbar, text, callback, shortcut=None):
        return add_action(self, toolbar, text, callback, shortcut)

    def _refresh_title(self):
        name = self._path.name if self._path else "Sin guardar"
        self.setWindowTitle(f"Metrados — {name}" + (" *" if self._dirty else ""))

    def _changed(self, *args):
        # QUndoStack emits state changes while its C++ destructor clears it.
        if not isValid(self.model.undo_stack) or not isValid(self.title_edit):
            return
        self._dirty = (not self.model.undo_stack.isClean() or
                       self.title_edit.text() != self._committed_title)
        self._refresh_title()
        self._selection_status()

    def _commit_title(self):
        value = self.title_edit.text()
        if value != self._committed_title:
            self.model.undo_stack.push(ProjectTitle(self, self._committed_title, value))

    def _history_actions(self):
        self.undo_action = self.model.undo_stack.createUndoAction(self, 'Deshacer')
        self.redo_action = self.model.undo_stack.createRedoAction(self, 'Rehacer')
        self.undo_action.setShortcut('Ctrl+Z')
        self.redo_action.setShortcuts(['Ctrl+Y', 'Ctrl+Shift+Z'])
        for action in (self.undo_action, self.redo_action):
            # Cell/text editors keep their native text undo while editing.
            action.setShortcutContext(Qt.WidgetShortcut)
            self.table.addAction(action)
        first = self.edit_menu.actions()[0]
        self.edit_menu.insertAction(first, self.undo_action)
        self.edit_menu.insertAction(first, self.redo_action)
        self.edit_menu.insertSeparator(first)
        toolbar = self.findChild(QToolBar, 'organizeStrip')
        toolbar.addSeparator()
        toolbar.addActions([self.undo_action, self.redo_action])
        file_menu = self.menuBar().addMenu('Archivo')
        file_menu.addAction('Exportar copia JSON…', self.export_json)

    def _selection_status(self, *args):
        index = self.table.currentIndex()
        if hasattr(self, 'row_actions'):
            valid = index.isValid()
            row = index.row()
            outline = self.model.outline
            previous = outline.previous[row] if valid else None
            measurement = valid and self.model.rows[row]['kind'] in MEASUREMENT_KINDS
            parent = outline.parents[row] if valid else None
            expected = 'detail_group' if measurement else 'chapter'
            enabled = {
                'up': valid and previous is not None,
                'down': valid and outline.following[row] is not None,
                'indent': valid and previous is not None and self.model.rows[previous]['kind'] == expected,
                'outdent': valid and parent is not None and (not measurement or self.model.rows[parent]['kind'] == 'detail_group'),
                'move': valid, 'copy': valid, 'copy_rows': valid,
            }
            for key, active in enabled.items():
                self.row_actions[key].setEnabled(active)
        if index.isValid() and index.row() in self.model.errors:
            message = self.model.errors[index.row()]
        else:
            message = self.model.summary_text
        if self.statusBar().currentMessage() != message:
            self.statusBar().showMessage(message)

    def _select(self, row, column=1):
        index = self.model.index(row, column)
        self.table.setCurrentIndex(index)
        self.table.scrollTo(index)
        self.table.setFocus()

    def _organize_actions(self):
        toolbar = QToolBar('Organizar', self)
        toolbar.setObjectName('organizeStrip')
        toolbar.setMovable(False)
        self.addToolBarBreak()
        self.addToolBar(toolbar)
        self.organize_menu = self.menuBar().addMenu('Organizar')
        self.edit_menu = self.menuBar().addMenu('Edición')
        self.row_actions = {}
        definitions = (
            ('up', '↑ Subir', lambda: self.move_row(-1), 'Alt+Up'),
            ('down', '↓ Bajar', lambda: self.move_row(1), 'Alt+Down'),
            ('indent', '→ Aumentar nivel', lambda: self.indent_row(True), 'Alt+Right'),
            ('outdent', '← Reducir nivel', lambda: self.indent_row(False), 'Alt+Left'),
            ('move', 'Mover a…', self.choose_destination, 'Ctrl+M'),
        )
        for key, text, callback, shortcut in definitions:
            action = QAction(text, self.table)
            action.setShortcut(shortcut)
            action.setShortcutContext(Qt.WidgetShortcut)
            action.setToolTip(text + ' (' + shortcut + ') · Incluye todos los descendientes')
            action.triggered.connect(lambda checked=False, fn=callback: fn())
            self.table.addAction(action)
            self.organize_menu.addAction(action)
            toolbar.addAction(action)
            self.row_actions[key] = action
        toolbar.addSeparator()
        for key, text, callback, shortcut in (
            ('copy', 'Copiar', self.copy_selection, 'Ctrl+C'),
            ('paste', 'Pegar', self.paste_selection, 'Ctrl+V'),
            ('copy_rows', 'Copiar bloque con descendientes', lambda: self.copy_selection(True), 'Ctrl+Shift+C'),
            ('paste_rows', 'Pegar bloque', self.paste_selection, 'Ctrl+Shift+V'),
        ):
            action = QAction(text, self.table)
            if shortcut:
                action.setShortcut(shortcut)
                action.setShortcutContext(Qt.WidgetShortcut)
                self.table.addAction(action)
            action.setToolTip(text + (f' ({shortcut})' if shortcut else ''))
            if key in ('copy', 'paste'):
                toolbar.addAction(action)
            action.triggered.connect(lambda checked=False, fn=callback: fn())
            self.edit_menu.addAction(action)
            self.row_actions[key] = action
        self.table.levelRequested.connect(self.indent_row)
        self.table.clipboardRequested.connect(lambda op: self.copy_selection() if op == 'copy' else self.paste_selection())
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)

    def _context_menu(self, point):
        index = self.table.indexAt(point)
        if index.isValid() and not self.table.selectionModel().isSelected(index):
            self._select(index.row(), index.column())
        menu = QMenu(self)
        menu.addActions([self.undo_action, self.redo_action])
        menu.addSeparator()
        for text, kind in (('Nuevo título', 'chapter'), ('Nuevo subtítulo', 'subtitle'),
                           ('Nueva partida', 'item'), ('Nuevo detalle', 'detail'),
                           ('Título dentro del desagregado', 'detail_group'),
                           ('Subtítulo dentro del desagregado', 'detail_subgroup')):
            menu.addAction(text, lambda checked=False, k=kind: self.add_row(k))
        menu.addSeparator()
        menu.addActions(list(self.row_actions.values()))
        menu.addSeparator()
        menu.addAction('Eliminar bloque…', self.remove_row)
        menu.exec(self.table.viewport().mapToGlobal(point))

    def _apply_structure(self, operation, *args):
        self.table.commit_editor()
        index = self.table.currentIndex()
        if not index.isValid():
            return
        try:
            rows, position = operation(self.model.rows, index.row(), *args)
        except ValueError as error:
            self.statusBar().showMessage(str(error), 7000)
            return
        self.model.replace(rows, 'movimiento de bloque',
                           (index.row(), index.column()), (position, index.column()))
        self._select(position, index.column())

    def move_row(self, direction):
        self._apply_structure(move_sibling, direction)

    def indent_row(self, inward):
        self._apply_structure(change_level, inward)

    def move_to_parent(self, destination):
        self._apply_structure(move_to, destination)

    def choose_destination(self):
        source = self.table.currentIndex().row()
        if source < 0:
            return
        dialog = DestinationDialog(self.model.rows, source, self.model.outline, self)
        if dialog.exec() == QDialog.Accepted:
            self.move_to_parent(dialog.destination)
        dialog.deleteLater()

    def copy_selection(self, whole_rows=False):
        selection = self.table.selectionModel()
        indexes = selection.selectedIndexes()
        if not indexes:
            return
        try:
            if whole_rows or selection.selectedRows():
                mime = encode_rows(self.model, {index.row() for index in indexes})
                QApplication.clipboard().setMimeData(mime)
                self.statusBar().showMessage('Bloque copiado con sus descendientes. Selecciona un destino y pulsa Ctrl+V.', 6000)
            else:
                top, bottom = min(i.row() for i in indexes), max(i.row() for i in indexes)
                left, right = min(i.column() for i in indexes), max(i.column() for i in indexes)
                matrix = [[cell_text(self.model, r, c) for c in range(left, right + 1)] for r in range(top, bottom + 1)]
                QApplication.clipboard().setText(tsv(matrix))
                self.statusBar().showMessage('Celdas copiadas. Para copiar un bloque completo, usa Ctrl+Mayús+C.', 6000)
        except ValueError as error:
            QMessageBox.warning(self, 'No se pudo copiar', str(error))

    def paste_selection(self):
        self.table.commit_editor()
        mime = QApplication.clipboard().mimeData()
        if mime is None:
            return
        current = self.table.currentIndex()
        try:
            if mime.hasFormat(ROW_MIME):
                block = decode_rows(mime.data(ROW_MIME))
                rows, position = insert_rows(self.model.rows, current.row(), block)
                self.model.replace(rows, 'pegado de bloque',
                                   (current.row(), current.column()), (position, 1))
                self._select(position)
            elif mime.hasText() and current.isValid():
                self.model.paste_cells(current.row(), current.column(), parse_tsv(mime.text()))
                self._select(current.row(), current.column())
        except ValueError as error:
            QMessageBox.warning(self, 'No se pudo pegar', str(error))

    def add_row(self, kind):
        self.table.commit_editor()
        rows = materialize(self.model.rows)
        if len(rows) >= MAX_ROWS:
            self.statusBar().showMessage('La planilla admite hasta 10 000 filas.', 5000)
            return
        outline = self.model.outline
        selected = self.table.currentIndex().row()
        if kind == "chapter":
            root = selected
            while root >= 0 and outline.parents[root] is not None:
                root = outline.parents[root]
            position = outline.ends[root] if root >= 0 else len(rows)
            row = new_row(kind, description="NUEVO TÍTULO", level=0)
        elif kind == 'subtitle':
            parent = container(rows, selected, outline)
            if parent is None:
                self.statusBar().showMessage('Selecciona un título para crear un subtítulo dentro de él.', 5000)
                return
            position = outline.ends[parent]
            row = new_row('chapter', description='NUEVO SUBTÍTULO',
                          level=outline.levels[parent] + 1)
        elif kind == "item":
            parent = container(rows, selected, outline)
            position = outline.ends[selected] if selected >= 0 else len(rows)
            if selected >= 0 and rows[selected]['kind'] in MEASUREMENT_KINDS:
                position = outline.ends[outline.owners[selected]]
            row = new_row(kind, description="NUEVA PARTIDA",
                          level=outline.levels[parent] + 1 if parent is not None else 0)
        elif kind in ('detail_group', 'detail_subgroup'):
            owner = outline.owners[selected] if selected >= 0 else None
            if owner is None:
                self.statusBar().showMessage('Selecciona una partida o una fila de su desagregado.', 5000)
                return
            if kind == 'detail_subgroup':
                parent = selected if rows[selected]['kind'] == 'detail_group' else outline.parents[selected]
                if parent is None or rows[parent]['kind'] != 'detail_group':
                    self.statusBar().showMessage('Selecciona un título de detalle para crear un subtítulo dentro de él.', 5000)
                    return
                position, level = outline.ends[parent], outline.levels[parent] + 1
            elif rows[selected]['kind'] == 'item':
                position, level = selected + 1, outline.levels[selected] + 1
            else:
                position, level = outline.ends[selected], outline.levels[selected]
            row = new_row('detail_group', description='NUEVO SUBTÍTULO DE DETALLE' if kind == 'detail_subgroup' else 'NUEVO TÍTULO DE DETALLE',
                          unit=rows[owner]['cells'][2], level=level)
        else:
            selected = selected if selected >= 0 else len(rows) - 1
            parent = parent_item(rows, selected) if selected >= 0 else None
            if parent is None:
                QMessageBox.information(self, "Agregar detalle", "Selecciona primero una partida o uno de sus detalles.")
                return
            selected_kind = rows[selected]['kind']
            position = outline.ends[selected] if selected_kind == 'detail_group' else selected + 1
            level = outline.levels[selected] if selected_kind == 'detail' else outline.levels[selected] + 1
            row = new_row(kind, description="Nuevo detalle", unit=rows[parent]["cells"][2],
                          level=level)
        rows.insert(position, row)
        try:
            rows = renumber(rows)
        except ValueError as error:
            self.statusBar().showMessage(str(error), 5000)
            return
        self.model.replace(rows, 'creación de fila', (selected, 1), (position, 1))
        self._select(position)
        self.table.edit(self.model.index(position, 1))

    def remove_row(self):
        self.table.commit_editor()
        index = self.table.currentIndex().row()
        if index < 0:
            return
        end = subtree_end(self.model.rows, index)
        count = end - index
        answer = QMessageBox.question(self, "Eliminar filas",
            f"Se eliminarán {count} fila(s), incluidos los detalles que dependan de la selección. ¿Continuar?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        rows = self.model.rows[:index] + self.model.rows[end:]
        self.model.replace(renumber(rows), 'eliminación de bloque', (index, 1), (index, 1))
        if rows:
            self._select(min(index, len(rows) - 1))

    def direct_quantity(self):
        self.table.commit_editor()
        index = self.table.currentIndex().row()
        if index < 0 or self.model.rows[index]["kind"] != "detail":
            QMessageBox.information(self, "Cantidad directa", "Selecciona una fila de detalle.")
            return
        row = self.model.rows[index]
        value, accepted = QInputDialog.getText(self, "Cantidad directa",
            "Cantidad base (" + row["cells"][2] + "), antes de aplicar los factores.\n"
            "Vacía el campo para volver al cálculo por dimensiones:",
            QLineEdit.Normal, row["direct"])
        if not accepted:
            return
        value = value.strip()
        if value:
            try:
                self._enlace.ask_sheet_quantity(row["cells"][2], [], 1.0, 1.0, float(value.replace(",", ".")))
            except (ValueError, OverflowError):
                QMessageBox.warning(self, "Cantidad inválida", "Ingresa un número positivo y finito.")
                return
        self.model.set_direct(index, value)
        self._select(index)

    def _can_discard(self):
        self.table.commit_editor()
        if not self._dirty:
            return True
        answer = QMessageBox.question(self, "Cambios sin guardar", "¿Guardar los cambios de esta planilla?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if answer == QMessageBox.Save:
            return self.save_project()
        return answer == QMessageBox.Discard

    def _load(self, title, rows, path=None, revision=None):
        self.model.replace(rows)
        self.title_edit.setText(title)
        self._committed_title = title
        self._revision = revision
        self._path, self._dirty = path, False
        self._refresh_title()
        self._selection_status()
        self._focus_steel()

    def new_project(self):
        if self._can_discard():
            self._load("", [])
            self.title_edit.setFocus()

    def load_example(self):
        if self._can_discard():
            self._load("Ejemplo de planilla de metrado", example_rows())

    def open_project(self):
        if not self._can_discard():
            return
        filename, _ = QFileDialog.getOpenFileName(self, "Abrir obra o importar JSON", "",
            "Obras de Metrados (*.metrado.db *.db *.sqlite *.metrado.json *.json);;SQLite (*.metrado.db *.db *.sqlite);;JSON anterior (*.json)")
        if not filename:
            return
        try:
            title, rows, revision = open_document(filename)
        except (OSError, ValueError, UnicodeError, RecursionError, sqlite3.Error) as error:
            QMessageBox.warning(self, "No se pudo abrir", str(error))
            return
        self._load(title, rows, Path(filename) if revision is not None else None, revision)
        if revision is None:
            # Imported data must be saved to a new SQLite file, never over JSON.
            self.model.undo_stack.resetClean()
            self.statusBar().showMessage('JSON importado. Guardar creará una base SQLite; el original se conserva.', 10000)

    def save_project(self, save_as=False):
        self.table.commit_editor()
        self._commit_title()
        path = self._path
        if save_as or path is None:
            filename, _ = QFileDialog.getSaveFileName(self, "Guardar obra SQLite", str(path or "Planilla.metrado.db"),
                "Base de Metrados (*.metrado.db)")
            if not filename:
                return False
            path = Path(filename)
            if not str(path).lower().endswith(('.db', '.sqlite')):
                path = Path(str(path) + ".metrado.db")
                if path.exists() and QMessageBox.question(self, "Reemplazar archivo",
                        "El archivo ya existe. ¿Reemplazarlo?", QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No) != QMessageBox.Yes:
                    return False
        try:
            same_file = self._path is not None and path.resolve() == self._path.resolve()
            revision = write_database(path, self.title_edit.text(), self.model.rows,
                                      self._revision if same_file else None)
        except (OSError, ValueError, sqlite3.Error) as error:
            QMessageBox.warning(self, "No se pudo guardar", str(error))
            return False
        self._path, self._dirty = path, False
        self._revision = revision
        self.model.undo_stack.setClean()
        self._refresh_title()
        self.statusBar().showMessage("Planilla guardada: " + str(path))
        return True

    def export_json(self):
        self.table.commit_editor()
        filename, _ = QFileDialog.getSaveFileName(self, 'Exportar copia JSON', 'Planilla.metrado.json',
                                                'Intercambio JSON (*.metrado.json)')
        if not filename:
            return False
        path = Path(filename)
        if path.suffix.lower() != '.json':
            path = Path(str(path) + '.metrado.json')
            if path.exists() and QMessageBox.question(self, 'Reemplazar archivo',
                    'El archivo ya existe. ¿Reemplazarlo?', QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No) != QMessageBox.Yes:
                return False
        if self._path is not None and path.resolve() == self._path.resolve():
            QMessageBox.warning(self, 'No se pudo exportar', 'Elige otro archivo para conservar la base SQLite.')
            return False
        try:
            write_project(path, self.title_edit.text(), self.model.rows)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, 'No se pudo exportar', str(error))
            return False
        self.statusBar().showMessage('Copia JSON exportada: ' + str(path))
        return True

    def closeEvent(self, event):
        if self._can_discard():
            # Dispose commands while their model/widgets are still alive.
            self.model.undo_stack.blockSignals(True)
            self.model.undo_stack.clear()
            event.accept()
        else:
            event.ignore()
