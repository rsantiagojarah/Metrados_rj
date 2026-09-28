from pathlib import Path
import sqlite3
from shiboken6 import isValid

from PySide6.QtCore import QItemSelectionModel, QSignalBlocker, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QInputDialog, QLineEdit, QMainWindow, QMenu, QMessageBox,
    QToolBar, QVBoxLayout, QWidget,
)

from metrado.grid import SheetModel, SheetView
from metrado.chrome import add_action, add_flat_action, action_toolbar, header_toolbar, ContextStatusBar, SPECS
from metrado.theme import apply_theme
from metrado.sheet import (
    example_rows, new_row, parent_item, write_project,
)
from metrado.steel import first_steel_item
from metrado.hierarchy import (
    MAX_ROWS, MEASUREMENT_KINDS, change_levels, level_selection, container, materialize, move_sibling, move_to, renumber,
)
from metrado.clipboard import ROW_MIME, cell_text, decode_rows, encode_rows, insert_rows, parse_tsv, selected_roots, tsv
from metrado.organize import DestinationDialog
from metrado.database import open_document, write_database
from metrado.history import ProjectTitle
from metrado.swelling_dialog import SwellingDialog
from metrado.navigation import PartidaWorkspace
from metrado import steel_config as sc
from metrado.steel_store import CatalogStore
from metrado.steel_dialog import CatalogDialog, DistributionFormatDialog, HooksDialog
from metrado.steel_distribution import (
    DEFAULT_TEMPLATE, distributed_bar_count, parse_distribution,
)
from metrado.shortcuts import KeyboardController
from metrado.reference_dialog import ReferencePicker, ConversionDialog
from metrado import references as refs


class PlantillaWindow(QMainWindow):
    def __init__(self, enlace, catalog_store=None):
        super().__init__()
        self._enlace, self._path, self._dirty = enlace, None, False
        self._revision = None
        self.command_actions = []
        self.setStatusBar(ContextStatusBar(self))
        self.resize(1480, 780)
        self.setMinimumSize(900, 480)
        self.model = SheetModel(enlace, example_rows())
        self.catalog_store = catalog_store or CatalogStore()
        self._catalog_error = None
        self._distribution_error = None
        self.steel_distribution_template = DEFAULT_TEMPLATE
        try:
            self.model.steel_defaults, _ = self.catalog_store.read()
        except (OSError, ValueError, sqlite3.Error) as error:
            self._catalog_error = str(error)
        try:
            self.steel_distribution_template, _ = self.catalog_store.read_distribution_format()
        except (OSError, ValueError, sqlite3.Error) as error:
            self._distribution_error = str(error)
        self.model.setParent(self)
        self.table = SheetView(self.model)
        self.table.referenceRequested.connect(self.reference_partida)
        self.workspace = PartidaWorkspace(self.model, self.table, self)
        self.navigator = self.workspace.navigator
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(6, 0, 6, 6)
        layout.setSpacing(3)
        self.title_edit = QLineEdit("Ejemplo de planilla de metrado")
        self._committed_title = self.title_edit.text()
        self.title_edit.setPlaceholderText("Nombre de la obra o proyecto")
        header_toolbar(self, self.title_edit)
        layout.addWidget(self.workspace, 1)
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
        self._swelling_actions()
        self._steel_actions()
        self._navigation_actions()
        self.keyboard = KeyboardController(self)
        self.model.changed.connect(self._changed)
        self.title_edit.textEdited.connect(self._changed)
        self.title_edit.editingFinished.connect(self._commit_title)
        self.model.undo_stack.indexChanged.connect(self._changed)
        self.model.undo_stack.cleanChanged.connect(self._changed)
        self.model.selectionRequested.connect(self._select)
        self.table.selectionModel().currentChanged.connect(self._selection_status)
        self.table.selectionModel().selectionChanged.connect(self._selection_status)
        self.navigator.selectionModel().selectionChanged.connect(self._selection_status)
        apply_theme(self)
        self._refresh_title()
        self._selection_status()
        self._focus_steel()

    def reference_partida(self, index):
        if not 0 <= index < len(self.model.rows):
            return
        owner = self.model.outline.owners[index]
        if owner is None:
            return
        target_unit = self.model.rows[owner]['cells'][2]
        entries = []
        for row in self.model.rows:
            if row['kind'] == 'item' and row['id'] != self.model.rows[owner]['id']:
                entries.append((f"{row['cells'][0]} · {row['cells'][1]}", row['cells'][2], row['id'], True))
        picker = ReferencePicker(entries, self)
        if picker.exec() != QDialog.Accepted:
            picker.deleteLater()
            return
        source_id = picker.chosen
        picker.deleteLater()
        source = next(row for row in self.model.rows if row['id'] == source_id)
        name, factor = '', ''
        if source['cells'][2] != target_unit:
            previous = self.model.rows[index].get('reference', {})
            same_units = (previous.get('source_unit'), previous.get('target_unit')) == (source['cells'][2], target_unit)
            dialog = ConversionDialog(source['cells'][2], target_unit, self,
                previous.get('factor_name', '') if same_units else '', previous.get('factor', '') if same_units else '')
            if dialog.exec() != QDialog.Accepted:
                dialog.deleteLater()
                return
            name, factor = dialog.name.text(), dialog.factor.text()
            dialog.deleteLater()
        try:
            if self.model.rows[index]['kind'] == 'detail':
                self.model.set_reference(index, source_id, name, factor)
                position = index
            else:
                if len(self.model.rows) >= MAX_ROWS:
                    raise ValueError('La planilla admite hasta 10 000 filas.')
                rows = materialize(self.model.rows)
                position = index + 1
                row = new_row('detail', description=source['cells'][1], unit=target_unit,
                              level=self.model.outline.levels[index] + 1)
                row['cells'][7] = '1'
                row['reference'] = refs.make_reference(source, target_unit, name, factor)
                refs.validate_row(row)
                rows.insert(position, row)
                self.model.replace(rows, 'referencia de partida', (index, 1), (position, 1))
            self._select(position, 1)
            self.table.setFocus()
        except ValueError as error:
            QMessageBox.warning(self, 'Referencia de partida', str(error))

    def _focus_steel(self):
        index = first_steel_item(self.model.rows)
        if index is not None:
            self._select(index)
        elif self.workspace.outline.node_rows:
            self._select(self.workspace.outline.node_rows[0])

    def _action(self, toolbar, text, callback, shortcut=None):
        action = add_action(self, toolbar, text, callback, shortcut)
        self.command_actions.append(action)
        return action

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
        toolbar = self.findChild(QToolBar, 'actionStrip')
        toolbar.addSeparator()
        add_flat_action(toolbar, self.undo_action, SPECS['Deshacer'])
        add_flat_action(toolbar, self.redo_action, SPECS['Rehacer'])
        file_menu = self.menuBar().addMenu('Archivo')
        self.import_excel_action = file_menu.addAction('Importar partidas desde Excel…', self.import_excel)
        self.import_excel_action.setToolTip('Crear una planilla desde ítems, descripciones y unidades de un Excel .xlsx.')
        self.export_excel_action = file_menu.addAction('Exportar metrados a Excel…', self.export_excel)
        self.export_excel_action.setToolTip('Desarrollo completo y resumen enlazado, editables con fórmulas e impresión A4.')
        self.export_action = file_menu.addAction('Exportar copia JSON…', self.export_json)

    def _selection_status(self, *args):
        if self.workspace._resetting:
            return
        index = self.table.currentIndex()
        if hasattr(self, 'hooks_action'):
            row = index.row()
            self.hooks_action.setEnabled(
                index.isValid() and self.model.rows[row]['kind'] == 'detail' and
                self.model.rows[row]['cells'][2] == 'kg' and not self.model.rows[row]['direct'])
        if hasattr(self, 'swelling_action'):
            self.swelling_action.setEnabled(self.model.swelling_owner(index.row()) is not None)
        if hasattr(self, 'row_actions'):
            valid = index.isValid()
            row = index.row()
            outline = self.model.outline
            previous = outline.previous[row] if valid else None
            enabled = {
                'up': valid and previous is not None,
                'down': valid and outline.following[row] is not None,
                'move': valid, 'copy': valid, 'copy_rows': valid,
            }
            selected, _ = self._selected_rows()
            for key, inward in (('indent', True), ('outdent', False)):
                try:
                    level_selection(self.model.rows, selected, inward, outline)
                    enabled[key] = True
                except ValueError:
                    enabled[key] = False
            for key, active in enabled.items():
                self.row_actions[key].setEnabled(active)
        if index.isValid() and index.row() in self.model.errors:
            message = self.model.errors[index.row()]
        else:
            message = self.model.summary_text
        mode = self.model.selection_mode(index.row())
        help_text = '/: referencia · F6: panel · Ctrl+F: buscar · Ctrl+K: comandos · F1: ayuda · Tab/Mayús+Tab: nivel'
        if self.workspace.navigation_active:
            context = 'Partidas: Enter abre el desarrollo · F2 edita · ' + help_text
        elif mode in ('reference', 'conversion'):
            context = 'Total = valor referenciado × ' + ('factor × ' if mode == 'conversion' else '') + 'Elem. simil. × N.º veces · ' + help_text
        elif mode == 'steel':
            context = 'Acero: Lon. = Elem. × (Largo + ganchos + empalmes) × N.º veces; Kg = Lon. × kg/m · ' + help_text
        elif (index.isValid() and self.model.rows[index.row()]['kind'] == 'detail' and
              self.model.rows[index.row()]['cells'][2] == 'm3' and
              self.model.rows[index.row()]['cells'][9].strip()):
            context = 'Volumen = Área base × una sola dimensión (Largo, Ancho o Alto) × Elem. simil. × N.º veces · ' + help_text
        else:
            context = 'Metrado: dimensiones × Elem. simil. × N.º veces · ' + help_text
        self.statusBar().set_context(context, self.model.summary_text)
        if self.statusBar().currentMessage() != message:
            self.statusBar().showMessage(message)

    def _select(self, row, column=1):
        self.workspace.select(row, column)

    def _commit_editors(self):
        self.workspace.commit_editors()

    def _navigation_actions(self):
        for action in [*self.row_actions.values(), self.undo_action, self.redo_action]:
            self.navigator.addAction(action)
        self.navigator.levelRequested.connect(self.indent_row)
        self.navigator.setContextMenuPolicy(Qt.CustomContextMenu)
        self.navigator.customContextMenuRequested.connect(self._navigation_menu)

    def _navigation_menu(self, point):
        index = self.navigator.indexAt(point)
        if index.isValid() and not self.navigator.selectionModel().isSelected(index):
            self.navigator.setCurrentIndex(index)
        self.workspace.navigation_active = True
        self._context_menu(point, self.navigator)

    def _organize_actions(self):
        toolbar = self.findChild(QToolBar, 'actionStrip')
        toolbar.addSeparator()
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
            add_flat_action(toolbar, action)
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
                add_flat_action(toolbar, action)
            action.triggered.connect(lambda checked=False, fn=callback: fn())
            self.edit_menu.addAction(action)
            self.row_actions[key] = action
        self.table.levelRequested.connect(self.indent_row)
        self.table.clipboardRequested.connect(lambda op: self.copy_selection() if op == 'copy' else self.paste_selection())
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)

    def _context_menu(self, point, view=None):
        view = view or self.table
        index = self.table.indexAt(point) if view is self.table else self.table.currentIndex()
        footer_owner = self.table.footer_owner_at(point) if view is self.table else None
        if footer_owner is not None:
            index = self.model.index(footer_owner, 1)
        selected_rows = self.table.selected_row_numbers()
        if view is self.table and index.isValid() and index.row() not in selected_rows:
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
        menu.addAction(self.swelling_action)
        menu.addAction(self.hooks_action)
        menu.addSeparator()
        menu.addAction('Eliminar bloque…', self.remove_row)
        menu.exec(view.viewport().mapToGlobal(point))

    def _steel_actions(self):
        menu = self.menuBar().addMenu('Acero')
        self.catalog_action = menu.addAction('Tabla global de aceros…', self.edit_steel_catalog)
        self.distribution_format_action = menu.addAction(
            'Formato de distribución CAD…', self.edit_steel_distribution_format)
        self.hooks_action = menu.addAction('Aplicar ganchos…', self.edit_steel_hooks)
        menu.addSeparator()
        self.update_steel_action = menu.addAction('Actualizar aceros de esta obra…', self.update_project_steel)
        self.hooks_action.setToolTip('Selecciona detalles de acero y aplica 1 o 2 ganchos. Reemplaza los anteriores.')
        toolbar = self.findChild(QToolBar, 'actionStrip')
        toolbar.addSeparator()
        add_flat_action(toolbar, self.hooks_action)
        if self._catalog_error:
            self.catalog_action.setToolTip(self._catalog_error)

    def edit_steel_distribution_format(self):
        self._commit_editors()
        try:
            template, revision = self.catalog_store.read_distribution_format()
            dialog = DistributionFormatDialog(template, self)
            if dialog.exec() != QDialog.Accepted:
                return
            template = dialog.configuration()
            self.catalog_store.save_distribution_format(template, revision)
            self.steel_distribution_template = template
            self._distribution_error = None
            self.statusBar().showMessage(
                'Formato de distribución CAD guardado para todos los proyectos.', 8000)
        except (OSError, ValueError, sqlite3.Error) as error:
            QMessageBox.warning(self, 'Formato de distribución CAD', str(error))

    def edit_steel_catalog(self):
        self._commit_editors()
        try:
            catalog, revision = self.catalog_store.read()
            dialog = CatalogDialog(catalog, self)
            if dialog.exec() != QDialog.Accepted:
                return
            catalog = dialog.configuration()
            self.catalog_store.save(catalog, revision)
            self.model.steel_defaults = catalog
            self._catalog_error = None
            self.statusBar().showMessage('Tabla global guardada. Los valores de esta obra no se modificaron.', 8000)
        except (OSError, ValueError, sqlite3.Error) as error:
            QMessageBox.warning(self, 'Tabla global de aceros', str(error))

    def edit_steel_hooks(self):
        self._commit_editors()
        selected = self.table.selected_row_numbers()
        try:
            indexes = sc.selected_details(self.model.rows, selected)
            if self._catalog_error and any('steel_catalog' not in self.model.rows[i] and
                    'steel_catalog' not in self.model.rows[self.model._owners[i]] for i in indexes):
                raise ValueError('No se pudo leer la tabla global: ' + self._catalog_error)
            dialog = HooksDialog([self.model.rows[i] for i in indexes],
                                 [self.model.steel_catalog_for(i) for i in indexes], self)
            if dialog.exec() == QDialog.Accepted:
                count, override = dialog.configuration()
                self.model.apply_steel_hooks(indexes, count, override)
        except ValueError as error:
            QMessageBox.information(self, 'Aplicar ganchos', str(error))

    def update_project_steel(self):
        self._commit_editors()
        try:
            catalog, _ = self.catalog_store.read()
            answer = QMessageBox.question(self, 'Actualizar aceros de esta obra',
                'Se actualizarán los pesos y empalmes de todas las partidas de acero de ESTA obra. '
                'Los empalmes se calcularán automáticamente por tramos de 9 m. '
                'Se conservarán las longitudes personalizadas de gancho y las cantidades directas.\n\n'
                'Las otras obras no se modificarán. Puedes deshacer con Ctrl+Z. ¿Continuar?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer == QMessageBox.Yes:
                self.model.update_steel_catalog(catalog)
                self.model.steel_defaults = catalog
                self._catalog_error = None
        except (OSError, ValueError, sqlite3.Error) as error:
            QMessageBox.warning(self, 'Actualizar aceros', str(error))

    def _swelling_actions(self):
        self.swelling_action = QAction('Factor de esponjamiento…', self)
        self.swelling_action.setToolTip('Selecciona detalles consecutivos en m³ y aplica un FE al bloque. Doble clic en FE para editar o quitar.')
        self.swelling_action.triggered.connect(lambda checked=False: self.edit_swelling())
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.swelling_action)
        toolbar = self.findChild(QToolBar, 'actionStrip')
        toolbar.addSeparator()
        add_flat_action(toolbar, self.swelling_action)
        self.table.swellingRequested.connect(self.edit_swelling)

    def edit_swelling(self, owner=None):
        self._commit_editors()
        selected = (self.table.selected_row_numbers()
                    if owner is None else {owner})
        try:
            start, end = self.model.swelling_selection(selected)
            if start == end:
                start, end = self.model.swelling_bounds(start)
        except ValueError as error:
            QMessageBox.information(self, 'Esponjamiento', str(error))
            return
        configs = [self.model.rows[i].get('volume_factor') for i in range(start, end + 1)]
        config = configs[0] if all(c == configs[0] for c in configs) else None
        dialog = SwellingDialog(end - start + 1, self.model.swelling_base(start, end), self._enlace, config, self)
        dialog.remove_button.setEnabled(any(c is not None for c in configs))
        if dialog.exec() == QDialog.Accepted:
            try:
                self.model.set_swelling(range(start, end + 1), dialog.configuration())
                self._select(start)
            except (ValueError, OverflowError) as error:
                QMessageBox.warning(self, 'Esponjamiento', str(error))
        dialog.deleteLater()

    def _apply_structure(self, operation, *args):
        self._commit_editors()
        index = self.table.currentIndex()
        if not index.isValid():
            return
        try:
            rows, position = operation(self.model.rows, index.row(), *args)
            self.model.replace(rows, 'movimiento de bloque',
                               (index.row(), index.column()), (position, index.column()))
        except ValueError as error:
            self.statusBar().showMessage(str(error), 7000)
            return
        self._select(position, index.column())

    def move_row(self, direction):
        self._apply_structure(move_sibling, direction)

    def indent_row(self, inward):
        self._commit_editors()
        selected, tree = self._selected_rows()
        if not selected:
            return
        identities = {self.model.rows[i]['id'] for i in selected}
        current = self.table.currentIndex()
        try:
            rows = change_levels(self.model.rows, selected, inward)
            positions = [i for i, row in enumerate(rows) if row['id'] in identities]
            self.workspace.navigation_active = tree
            self.model.replace(rows, 'aumento de nivel de selección' if inward else 'reducción de nivel de selección',
                               (current.row(), current.column()), (positions[0], 1))
        except ValueError as error:
            self.statusBar().showMessage(str(error), 7000)
            return
        self._select(positions[0], 1)
        view = self.navigator if tree else self.table
        with QSignalBlocker(view.selectionModel()):
            for position in positions:
                index = self.workspace.outline.for_row(position, 1) if tree else self.model.index(position, 1)
                flags = QItemSelectionModel.Select | (QItemSelectionModel.Rows if tree else QItemSelectionModel.NoUpdate)
                view.selectionModel().select(index, flags)
        self._selection_status()

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
        if self.workspace.navigation_active:
            selected = self.navigator.selectionModel().selectedRows()
            if selected:
                try:
                    mime = encode_rows(self.model, {self.workspace.outline.source_row(i) for i in selected})
                    QApplication.clipboard().setMimeData(mime)
                    self.statusBar().showMessage('Bloque copiado con todos sus detalles. Selecciona destino y pulsa Ctrl+V.', 6000)
                except ValueError as error:
                    QMessageBox.warning(self, 'No se pudo copiar', str(error))
            return
        selection = self.table.selectionModel()
        rows = self.table.selected_row_numbers()
        if not rows:
            return
        try:
            if whole_rows or self.table.selection_has_full_row():
                mime = encode_rows(self.model, rows)
                QApplication.clipboard().setMimeData(mime)
                self.statusBar().showMessage('Bloque copiado con sus descendientes. Selecciona un destino y pulsa Ctrl+V.', 6000)
            else:
                top, bottom = min(rows), max(rows)
                ranges = [r for r in selection.selection() if any(r.top() <= row <= r.bottom() for row in rows)]
                left, right = min(r.left() for r in ranges), max(r.right() for r in ranges)
                columns = [c for c in self.table.visible_columns() if left <= c <= right]
                matrix = [[cell_text(self.model, r, c) for c in columns] for r in range(top, bottom + 1) if not self.table.isRowHidden(r)]
                QApplication.clipboard().setText(tsv(matrix))
                self.statusBar().showMessage('Celdas copiadas. Para copiar un bloque completo, usa Ctrl+Mayús+C.', 6000)
        except ValueError as error:
            QMessageBox.warning(self, 'No se pudo copiar', str(error))

    def paste_selection(self):
        self._commit_editors()
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
                matrix = parse_tsv(mime.text())
                if not matrix:
                    return
                if self.workspace.navigation_active:
                    self.workspace.paste_outline(matrix)
                    return
                owner = self.model.outline.owners[current.row()]
                if owner is None or current.row() + len(matrix) > self.model.outline.ends[owner]:
                    raise ValueError('El bloque supera la partida visible. Agrega primero sus filas de detalle; no se modificaron otras partidas.')
                columns = [c for c in self.table.visible_columns() if c >= current.column()]
                if any(len(cells) > len(columns) for cells in matrix):
                    raise ValueError('El bloque supera las columnas visibles de la planilla.')
                targets = [(current.row() + offset, columns[c], value)
                           for offset, cells in enumerate(matrix) for c, value in enumerate(cells)]
                self.model.paste_mapped_cells(targets, (current.row(), current.column()))
                self._select(current.row(), current.column())
        except ValueError as error:
            QMessageBox.warning(self, 'No se pudo pegar', str(error))

    def add_row(self, kind):
        self._commit_editors()
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
            if row['cells'][2] == 'kg':
                if self._catalog_error and 'steel_catalog' not in rows[parent]:
                    QMessageBox.warning(self, 'Tabla de aceros', self._catalog_error)
                    return
                catalog = rows[parent].get('steel_catalog') or self.model.steel_defaults
                sc.adopt(rows[parent], catalog)
                sc.adopt(row, catalog)
        rows.insert(position, row)
        try:
            rows = renumber(rows)
        except ValueError as error:
            self.statusBar().showMessage(str(error), 5000)
            return
        self.model.replace(rows, 'creación de fila', (selected, 1), (position, 1))
        self._select(position)
        self.workspace.edit_description(position)

    def insert_autocad_area(self, name, area_m2, entity_count,
                            region_count=None, drawing='', drawing_unit=''):
        """Append one area detail while preserving the original API."""
        result = self.insert_autocad_areas([{
            'name': name, 'area_m2': area_m2, 'entity_count': entity_count,
            'region_count': region_count,
        }], drawing=drawing, drawing_unit=drawing_unit)
        measurement = result['measurements'][0]
        return {
            'item_code': result['item_code'],
            'item_description': result['item_description'],
            'detail_id': result['detail_ids'][0],
            'area_m2': measurement['area_m2'],
        }

    def insert_autocad_areas(self, measurements, drawing='', drawing_unit=''):
        """Append an area batch as one undoable operation."""
        self._commit_editors()
        visible = self.workspace._visible
        if visible is None:
            raise ValueError('Selecciona primero una partida en Metrados.')
        owner = visible[0]
        if not 0 <= owner < len(self.model.rows) or self.model.rows[owner]['kind'] != 'item':
            raise ValueError('Selecciona primero una partida en Metrados.')
        unit = self.model.rows[owner]['cells'][2]
        if unit not in ('m2', 'm3'):
            raise ValueError('La partida activa debe tener unidad m² o m³ para recibir un área de AutoCAD.')
        if not isinstance(measurements, list) or not measurements:
            raise ValueError('AutoCAD no envió áreas para agregar.')
        if len(self.model.rows) + len(measurements) > MAX_ROWS:
            raise ValueError('La planilla admite hasta 10 000 filas.')

        rows = materialize(self.model.rows)
        position = self.model.outline.ends[owner]
        accepted = []
        for offset, measurement in enumerate(measurements):
            try:
                area_m2 = self._enlace.ask_sheet_quantity(
                    'm2', [], 1.0, 1.0, measurement['area_m2'])
            except (KeyError, TypeError, ValueError, OverflowError) as error:
                raise ValueError('Una de las áreas recibidas está fuera del rango admitido.') from error
            name = str(measurement.get('name', '')).strip()
            if not name:
                raise ValueError('Una de las áreas recibidas no tiene nombre.')
            row = new_row('detail', description=name, unit=unit,
                          level=self.model.outline.levels[owner] + 1)
            if unit == 'm2':
                row['direct'] = format(area_m2, '.12g')
            else:
                row['cells'][9] = format(area_m2, '.12g')
            rows.insert(position + offset, row)
            accepted.append({
                'name': name,
                'area_m2': area_m2,
                'entity_count': measurement.get('entity_count', 1),
                'region_count': measurement.get('region_count'),
            })
        rows = renumber(rows)
        current = self.table.currentIndex()
        before = (current.row(), current.column()) if current.isValid() else (owner, 1)
        last = position + len(accepted) - 1
        self.model.replace(rows, 'áreas desde AutoCAD', before, (last, 1))
        self._select(last)
        suffix = (' Completa una sola dimensión en Largo, Ancho o Alto.'
                  if unit == 'm3' else '')
        total = sum(value['area_m2'] for value in accepted)
        self.statusBar().showMessage(
            f'{len(accepted)} área(s) de AutoCAD agregada(s); total: '
            f'{total:.2f} m².{suffix}', 10000)
        return {
            'item_code': self.model.rows[owner]['cells'][0],
            'item_description': self.model.rows[owner]['cells'][1],
            'detail_ids': [self.model.rows[index]['id']
                           for index in range(position, last + 1)],
            'measurements': accepted,
        }

    def insert_autocad_length(self, name, length_m, entity_count,
                              drawing='', drawing_unit=''):
        """Append one length detail while preserving the original API."""
        result = self.insert_autocad_lengths([{
            'name': name, 'length_m': length_m, 'entity_count': entity_count,
        }], drawing=drawing, drawing_unit=drawing_unit)
        measurement = result['measurements'][0]
        return {
            'item_code': result['item_code'],
            'item_description': result['item_description'],
            'detail_id': result['detail_ids'][0],
            'length_m': measurement['length_m'],
        }

    def insert_autocad_lengths(self, measurements, drawing='', drawing_unit=''):
        """Append a length batch as one undoable operation."""
        self._commit_editors()
        visible = self.workspace._visible
        if visible is None:
            raise ValueError('Selecciona primero una partida en Metrados.')
        owner = visible[0]
        if not 0 <= owner < len(self.model.rows) or self.model.rows[owner]['kind'] != 'item':
            raise ValueError('Selecciona primero una partida en Metrados.')
        unit = self.model.rows[owner]['cells'][2]
        if unit not in ('m', 'm2', 'm3'):
            raise ValueError('La partida activa debe tener unidad m, m² o m³ para recibir una longitud de AutoCAD.')
        if not isinstance(measurements, list) or not measurements:
            raise ValueError('AutoCAD no envió longitudes para agregar.')
        if len(self.model.rows) + len(measurements) > MAX_ROWS:
            raise ValueError('La planilla admite hasta 10 000 filas.')

        rows = materialize(self.model.rows)
        position = self.model.outline.ends[owner]
        accepted = []
        for offset, measurement in enumerate(measurements):
            try:
                length_m = self._enlace.ask_sheet_quantity(
                    'm', [], 1.0, 1.0, measurement['length_m'])
            except (KeyError, TypeError, ValueError, OverflowError) as error:
                raise ValueError('Una de las longitudes recibidas está fuera del rango admitido.') from error
            length_text = f'{length_m:.2f}'
            length_m = float(length_text)
            if length_m <= 0:
                raise ValueError('Una longitud es demasiado pequeña para expresarla con dos decimales.')
            name = str(measurement.get('name', '')).strip()
            if not name:
                raise ValueError('Una de las longitudes recibidas no tiene nombre.')
            row = new_row('detail', description=name, unit=unit,
                          level=self.model.outline.levels[owner] + 1)
            if unit == 'm':
                row['direct'] = length_text
            else:
                row['cells'][4] = length_text
            rows.insert(position + offset, row)
            accepted.append({
                'name': name,
                'length_m': length_m,
                'entity_count': measurement.get('entity_count', 1),
            })
        rows = renumber(rows)
        current = self.table.currentIndex()
        before = (current.row(), current.column()) if current.isValid() else (owner, 1)
        last = position + len(accepted) - 1
        self.model.replace(rows, 'longitudes desde AutoCAD', before, (last, 1))
        self._select(last)
        suffix = (' Completa las dimensiones restantes en Metrados.'
                  if unit in ('m2', 'm3') else '')
        total = sum(value['length_m'] for value in accepted)
        self.statusBar().showMessage(
            f'{len(accepted)} longitud(es) de AutoCAD agregada(s); total: '
            f'{total:.2f} m.{suffix}', 10000)
        return {
            'item_code': self.model.rows[owner]['cells'][0],
            'item_description': self.model.rows[owner]['cells'][1],
            'detail_ids': [self.model.rows[index]['id']
                           for index in range(position, last + 1)],
            'measurements': accepted,
        }

    def insert_autocad_steel(self, description, length_m, distribution_m,
                             distribution_text, drawing='', drawing_unit=''):
        """Create one managed steel detail from geometry and a CAD label."""
        self._commit_editors()
        visible = self.workspace._visible
        if visible is None:
            raise ValueError('Selecciona primero una partida de acero en Metrados.')
        owner = visible[0]
        if (not 0 <= owner < len(self.model.rows) or
                self.model.rows[owner]['kind'] != 'item' or
                self.model.rows[owner]['cells'][2] != 'kg'):
            raise ValueError('La partida activa debe tener unidad kg para recibir acero desde AutoCAD.')
        if len(self.model.rows) >= MAX_ROWS:
            raise ValueError('La planilla admite hasta 10 000 filas.')
        if self._distribution_error:
            raise ValueError('No se pudo leer el formato de distribución CAD: ' + self._distribution_error)
        try:
            length_m = self._enlace.ask_sheet_quantity('m', [], 1.0, 1.0, length_m)
            distribution_m = self._enlace.ask_sheet_quantity(
                'm', [], 1.0, 1.0, distribution_m)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError('Las distancias recibidas deben ser positivas y finitas.') from error
        length_text = f'{length_m:.2f}'
        length_m = float(length_text)
        if length_m <= 0:
            raise ValueError('El largo es demasiado pequeño para expresarlo con dos decimales.')
        parsed = parse_distribution(distribution_text, self.steel_distribution_template)
        bars = distributed_bar_count(
            distribution_m, parsed['spacing_m'], parsed['multiplier'])
        description = str(description).strip()
        if not description:
            raise ValueError('Escribe una descripción para el detalle de acero.')

        rows = materialize(self.model.rows)
        catalog = rows[owner].get('steel_catalog') or self.model.steel_defaults
        if catalog is None:
            raise ValueError('No hay una tabla de aceros disponible para calcular el detalle.')
        if self._catalog_error and 'steel_catalog' not in rows[owner]:
            raise ValueError('No se pudo leer la tabla global de aceros: ' + self._catalog_error)
        if 'steel_catalog' not in rows[owner]:
            sc.adopt(rows[owner], catalog)
        row = new_row('detail', description=description, unit='kg',
                      level=self.model.outline.levels[owner] + 1)
        row['cells'][3] = '1'
        row['cells'][4] = length_text
        row['cells'][7] = parsed['diameter']
        row['cells'][9] = '1'
        row['cells'][10] = str(bars)
        sc.adopt(row, catalog)

        position = self.model.outline.ends[owner]
        rows.insert(position, row)
        rows = renumber(rows)
        current = self.table.currentIndex()
        before = (current.row(), current.column()) if current.isValid() else (owner, 1)
        self.model.replace(rows, 'acero desde AutoCAD', before, (position, 1))
        self._select(position)
        inserted = self.model.rows[position]
        self.statusBar().showMessage(
            f'Acero de AutoCAD agregado: {inserted["cells"][1]} · largo '
            f'{length_m:.2f} m · distribución {distribution_m:.2f} m.', 10000)
        return {
            'item_code': self.model.rows[owner]['cells'][0],
            'item_description': self.model.rows[owner]['cells'][1],
            'detail_id': inserted['id'],
            'description': inserted['cells'][1],
            'length_m': length_m,
            'distribution_m': distribution_m,
            'diameter': parsed['diameter'],
            'spacing_m': float(parsed['spacing_m']),
            'bars': bars,
        }

    def _selected_rows(self):
        """The same active-panel selection for deletion and bulk level changes."""
        current = self.table.currentIndex().row()
        sheet_selected = self.table.selected_row_numbers()
        # The hidden partida can still be the logical target after selecting an
        # empty item or creating a title. Its selection lives in the left panel.
        tree = self.workspace.navigation_active or (
            not sheet_selected and 0 <= current < len(self.model.rows) and self.model.rows[current]['kind'] in ('chapter', 'item'))
        if tree:
            selected = {self.workspace.outline.source_row(i)
                        for i in self.navigator.selectionModel().selectedRows()}
        else:
            selected = sheet_selected
        return {i for i in selected if i is not None and 0 <= i < len(self.model.rows)}, tree

    def remove_row(self):
        self._commit_editors()
        selected, tree = self._selected_rows()
        if not selected:
            return
        roots = selected_roots(self.model.rows, selected)
        index = roots[0]
        removed = {i for root in roots for i in range(root, self.model.outline.ends[root])}
        count = len(removed)
        answer = QMessageBox.question(self, "Eliminar filas",
            f"Se eliminarán {count} fila(s), incluidos los descendientes de los títulos o partidas seleccionados. "
            "Puedes recuperarlas con Ctrl+Z. ¿Continuar?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        survivors = [i for i in range(len(self.model.rows)) if i not in removed]
        if tree:
            candidates = [i for i in self.workspace.outline.node_rows if i not in removed]
        else:
            owner = self.model.outline.owners[index]
            candidates = [i for i in survivors if i > owner and self.model.outline.owners[i] == owner]
            if not candidates and owner in survivors:
                candidates = [owner]
        target = next((i for i in candidates if i >= index), candidates[-1] if candidates else None)
        position = survivors.index(target) if target is not None else 0
        rows = [self.model.rows[i] for i in survivors]
        self.workspace.navigation_active = tree
        self.model.replace(renumber(rows), 'eliminación de filas', (index, 1), (position, 1))

    def direct_quantity(self):
        self._commit_editors()
        index = self.table.currentIndex().row()
        if index < 0 or self.model.rows[index]["kind"] != "detail":
            QMessageBox.information(self, "Cantidad directa", "Selecciona una fila de detalle.")
            return
        row = self.model.rows[index]
        if 'reference' in row:
            self.statusBar().showMessage('Este detalle usa el total de otra partida. Escribe / en Descripción para cambiar su referencia.', 7000)
            return
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
        self._commit_editors()
        if not self._dirty:
            return True
        answer = QMessageBox.question(self, "Cambios sin guardar", "¿Guardar los cambios de esta planilla?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if answer == QMessageBox.Save:
            return self.save_project()
        return answer == QMessageBox.Discard

    def _load(self, title, rows, path=None, revision=None):
        self.keyboard.memory.clear()
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

    def import_excel(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Importar partidas desde Excel', '', 'Excel (*.xlsx)')
        if not filename:
            return
        # Parse and preview before asking to discard anything in the open work.
        from metrado.excel_import import ExcelBudget
        from metrado.excel_dialog import ExcelImportDialog
        try:
            with ExcelBudget(filename) as budget:
                dialog = ExcelImportDialog(budget, self)
                try:
                    if dialog.exec() != QDialog.Accepted:
                        return
                    result = dialog.result
                finally:
                    dialog.deleteLater()
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, 'No se pudo importar Excel', str(error))
            return
        if result is None or not self._can_discard():
            return
        self._load(Path(filename).stem, result.rows)
        self.model.undo_stack.resetClean()
        self._select(next(i for i, row in enumerate(result.rows) if row['kind'] == 'item'))
        self.navigator.scrollToTop()
        self.navigator.setFocus()
        self.statusBar().showMessage(
            f'Excel importado: {result.titles} títulos/subtítulos y {result.items} partidas. '
            'Guardar creará una base SQLite nueva; el Excel se conserva.', 12000)

    def save_project(self, save_as=False):
        self._commit_editors()
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

    def export_excel(self):
        self._commit_editors()
        self._commit_title()
        suggested = self._path.with_suffix('.xlsx') if self._path else Path('Metrados.xlsx')
        filename, _ = QFileDialog.getSaveFileName(self, 'Exportar desarrollo y resumen de metrados',
                                                str(suggested), 'Excel (*.xlsx)')
        if not filename:
            return False
        path = Path(filename)
        if path.suffix.lower() != '.xlsx':
            path = Path(str(path) + '.xlsx')
            if path.exists() and QMessageBox.question(self, 'Reemplazar archivo',
                    'El archivo ya existe. ¿Reemplazarlo?', QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No) != QMessageBox.Yes:
                return False
        if self._path is not None and path.resolve() == self._path.resolve():
            QMessageBox.warning(self, 'No se pudo exportar', 'Elige otro archivo para conservar la base SQLite.')
            return False
        from metrado.excel_export import export_workbook
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            count, pending = export_workbook(path, self.title_edit.text(), self.model.rows, self._enlace)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, 'No se pudo exportar Excel', str(error))
            return False
        finally:
            QApplication.restoreOverrideCursor()
        self.statusBar().showMessage(f'Excel exportado: {count} partidas · Desarrollo y Resumen · '
                                    f'{pending} filas pendientes · {path}', 15000)
        return True

    def export_json(self):
        self._commit_editors()
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
