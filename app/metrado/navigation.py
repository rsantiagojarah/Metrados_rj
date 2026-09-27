"""A live outline and an item-scoped view of the same sheet, without data copies."""
from bisect import bisect_left, bisect_right

from PySide6.QtCore import QAbstractItemModel, QEvent, QItemSelectionModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QHeaderView, QLabel, QSizePolicy, QSplitter,
    QStyledItemDelegate, QTreeView, QVBoxLayout, QWidget,
)

from metrado.grid import SheetView
from metrado.sheet import UNITS


class PartidaModel(QAbstractItemModel):
    columns = (0, 1, 2, 13)

    def __init__(self, sheet, parent=None):
        super().__init__(parent)
        self.sheet = sheet
        self.rebuild()
        sheet.modelAboutToBeReset.connect(self.beginResetModel)
        sheet.modelReset.connect(self.reset_outline)
        sheet.dataChanged.connect(self.update_rows)

    def rebuild(self):
        self.children, self.positions, self.by_id, self.node_rows = {None: []}, {}, {}, []
        for row, entry in enumerate(self.sheet.rows):
            self.by_id[entry['id']] = row
            if entry['kind'] not in ('chapter', 'item'):
                continue
            parent = self.sheet.outline.parents[row]
            siblings = self.children.setdefault(parent, [])
            self.positions[row] = len(siblings)
            siblings.append(row)
            self.node_rows.append(row)

    def reset_outline(self):
        self.rebuild()
        self.endResetModel()

    def source_row(self, index):
        return index.internalId() - 1 if index.isValid() else None

    def for_row(self, row, column=0):
        return self.createIndex(self.positions[row], column, row + 1) if row in self.positions else QModelIndex()

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        return self.for_row(self.children[self.source_row(parent)][row], column)

    def parent(self, index):
        row = self.source_row(index)
        return self.for_row(self.sheet.outline.parents[row]) if row is not None else QModelIndex()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() and parent.column() else len(self.children.get(self.source_row(parent), ()))

    def columnCount(self, parent=QModelIndex()):
        return 4

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return ('ÍTEM', 'PARTIDAS', 'Und', 'Total')[section]

    def data(self, index, role=Qt.DisplayRole):
        row = self.source_row(index)
        if row is None:
            return None
        if index.column() == 1 and role in (Qt.DisplayRole, Qt.EditRole, Qt.ToolTipRole):
            return self.sheet.rows[row]['cells'][1]
        return self.sheet.data(self.sheet.index(row, self.columns[index.column()]), role)

    def flags(self, index):
        row = self.source_row(index)
        return self.sheet.flags(self.sheet.index(row, self.columns[index.column()])) if row is not None else Qt.NoItemFlags

    def setData(self, index, value, role=Qt.EditRole):
        row = self.source_row(index)
        return self.sheet.setData(self.sheet.index(row, self.columns[index.column()]), value, role) if row is not None else False

    def update_rows(self, first, last, roles=None):
        # Only outline nodes in the changed item/range; no whole-tree rebuild.
        left = bisect_left(self.node_rows, first.row())
        right = bisect_right(self.node_rows, last.row())
        for row in self.node_rows[left:right]:
            self.dataChanged.emit(self.for_row(row), self.for_row(row, 3))


class PartidaDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        if index.column() == 2:
            editor = QComboBox(parent)
            editor.addItems(UNITS)
            return editor
        return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        if isinstance(editor, QComboBox):
            editor.setCurrentText(index.data(Qt.EditRole))
        else:
            super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        if isinstance(editor, QComboBox):
            model.setData(index, editor.currentText())
        else:
            super().setModelData(editor, model, index)


class PartidaTree(QTreeView):
    levelRequested = Signal(bool)
    focusEntered = Signal()
    beforeNavigate = Signal()
    commit_editor = SheetView.commit_editor

    def setCurrentIndex(self, index):
        # Programmatic navigation is a single selection even if a shortcut is
        # still holding Ctrl/Shift. Mouse multi-selection remains Qt's default.
        self.selectionModel().setCurrentIndex(
            index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)

    def focusInEvent(self, event):
        self.focusEntered.emit()
        super().focusInEvent(event)

    def mousePressEvent(self, event):
        self.beforeNavigate.emit()
        super().mousePressEvent(event)

    def event(self, event):
        if event.type() == QEvent.KeyPress and self.state() != QAbstractItemView.EditingState and self.currentIndex().column() in (0, 1):
            if event.key() in (Qt.Key_Tab, Qt.Key_Backtab) and not event.modifiers() & (Qt.ControlModifier | Qt.AltModifier):
                self.levelRequested.emit(event.key() == Qt.Key_Tab and not bool(event.modifiers() & Qt.ShiftModifier))
                event.accept()
                return True
        return super().event(event)


class PartidaHeading(QLabel):
    """Single-line heading: elide long descriptions, keeping the total visible."""

    def __init__(self):
        super().__init__()
        self._title = self._suffix = ''
        self.setTextFormat(Qt.PlainText)
        self.setWordWrap(False)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.setObjectName('partidaHeading')

    def set_parts(self, title, suffix=''):
        self._title = ' '.join(title.split())
        self._suffix = suffix
        self.setText(self._title + suffix)
        self.setToolTip(self.text())

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.contentsRect().adjusted(6, 0, -6, 0)
        metrics = self.fontMetrics()
        available = max(0, rect.width() - metrics.horizontalAdvance(self._suffix))
        title = metrics.elidedText(self._title, Qt.ElideRight, available)
        painter.setPen(self.palette().windowText().color())
        painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, title + self._suffix)


class PartidaWorkspace(QWidget):
    def __init__(self, sheet, table, parent=None):
        super().__init__(parent)
        self.sheet, self.table = sheet, table
        self.sheet.local_row_numbers = True
        self.navigation_active = False
        self._syncing = self._resetting = False
        self._visible = None
        self._active_id = self._owner_id = None
        self._column = 1
        self._collapsed = set()
        sheet.modelAboutToBeReset.connect(self.before_reset)
        self.outline = PartidaModel(sheet, self)
        self.navigator = PartidaTree()
        self.navigator.setObjectName('partidaNavigator')
        self.navigator.setModel(self.outline)
        self.navigator.setItemDelegate(PartidaDelegate(self.navigator))
        self.navigator.setUniformRowHeights(True)
        self.navigator.setIndentation(14)
        self.navigator.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.navigator.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.navigator.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.navigator.setExpandsOnDoubleClick(False)
        self.navigator.header().setStretchLastSection(False)
        for column, width in enumerate((94, 120, 36, 74)):
            self.navigator.setColumnWidth(column, width)
        self.navigator.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.navigator.setMinimumWidth(240)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(3)
        # Matching heading widgets share font metrics, padding and vertical
        # size policy at every display scale, so both tables start together.
        caption = PartidaHeading()
        caption.set_parts('PARTIDAS · Doble clic o F2 para editar')
        left_layout.addWidget(caption)
        left_layout.addWidget(self.navigator, 1)
        right = QWidget()
        right.setMinimumWidth(400)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(3)
        self.heading = PartidaHeading()
        right_layout.addWidget(self.heading)
        right_layout.addWidget(table, 1)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setObjectName('partidaSplitter')
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(7)
        self.splitter.addWidget(left)
        self.splitter.addWidget(right)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([320, 1120])
        table.enable_compact_layout()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.splitter)
        self.navigator.selectionModel().currentChanged.connect(self.from_tree)
        self.navigator.clicked.connect(lambda current: self.from_tree(current, QModelIndex()))
        self.table.selectionModel().currentChanged.connect(self.from_table)
        self.navigator.focusEntered.connect(lambda: self.activate_navigation(True))
        self.table.focusEntered.connect(lambda: self.activate_navigation(False))
        self.navigator.beforeNavigate.connect(self.table.commit_editor)
        sheet.modelReset.connect(self.after_reset)
        sheet.dataChanged.connect(self.refresh_heading)
        self.after_reset()

    def activate_navigation(self, active):
        if not self._syncing:
            self.navigation_active = active
            if active and not self._resetting:
                self.from_tree(self.navigator.currentIndex(), QModelIndex())
            elif not active and self._visible:
                first, end = self._visible[0] + 1, self._visible[1]
                if first < end and self.table.isRowHidden(self.table.currentIndex().row()):
                    self.select(first, 1, focus=False)

    def before_reset(self):
        self._resetting = True
        self._collapsed = {self.sheet.rows[r]['id'] for r in self.outline.node_rows
                           if self.outline.children.get(r) and not self.navigator.isExpanded(self.outline.for_row(r))}

    def after_reset(self):
        self._syncing = True
        try:
            for row in range(self.sheet.rowCount()):
                self.table.setRowHidden(row, True)
            self._visible = None
            for row in self.outline.node_rows:
                identity = self.sheet.rows[row]['id']
                self.navigator.setExpanded(self.outline.for_row(row), identity not in self._collapsed)
        finally:
            self._syncing = self._resetting = False
        row = self.outline.by_id.get(self._active_id, self.outline.by_id.get(self._owner_id))
        if row is None and self.outline.node_rows:
            row = self.outline.node_rows[0]
        if row is not None:
            self.select(row, self._column, focus=False)
        else:
            self._active_id = self._owner_id = None
            self.refresh_heading()

    def show_item(self, row):
        owner = self.sheet.outline.owners[row]
        visible = (owner, self.sheet.outline.ends[owner]) if owner is not None else None
        if visible != self._visible:
            # Hide only the previous block and reveal the new one. Domain indexes
            # stay unchanged, so history, clipboard and FE keep their semantics.
            self.table.setUpdatesEnabled(False)
            try:
                if self._visible:
                    for index in range(*self._visible):
                        self.table.setRowHidden(index, True)
                if visible:
                    # The partida remains the action target in the tree, but
                    # only its development belongs in the right-hand table.
                    for index in range(visible[0] + 1, visible[1]):
                        self.table.setRowHidden(index, False)
                self._visible = visible
            finally:
                self.table.setUpdatesEnabled(True)
        self._owner_id = self.sheet.rows[owner]['id'] if owner is not None else None
        self.refresh_heading()

    def refresh_heading(self, *args):
        if self._resetting:
            return
        if self._visible is None:
            self.heading.set_parts('Selecciona una partida en el panel izquierdo para ver su metrado.')
            return
        owner = self._visible[0]
        row = self.sheet.rows[owner]
        total = self.sheet.data(self.sheet.index(owner, 13))
        self.heading.set_parts(f'{row["cells"][0]} · {row["cells"][1]}',
                               f' · {row["cells"][2]} · Total: {total}')

    def select(self, row, column=1, focus=True):
        if not 0 <= row < self.sheet.rowCount():
            return
        self._syncing = True
        try:
            self.show_item(row)
            entry = self.sheet.rows[row]
            node = row if entry['kind'] in ('chapter', 'item') else self.sheet.outline.owners[row]
            tree_index = self.outline.for_row(node, column if column < 3 else 3)
            cursor = tree_index.parent()
            while cursor.isValid():
                self.navigator.setExpanded(cursor, True)
                cursor = cursor.parent()
            if self.outline.source_row(self.navigator.currentIndex()) != node:
                self.navigator.selectionModel().setCurrentIndex(
                    tree_index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
                self.navigator.scrollTo(tree_index)
            index = self.sheet.index(row, column)
            if self.table.currentIndex() != index:
                self.table.setCurrentIndex(index)
            self._active_id, self._column = entry['id'], column
            if entry['kind'] == 'chapter':
                self.navigation_active = True
            elif entry['kind'] in ('detail', 'detail_group'):
                self.navigation_active = False
            if focus:
                if self.navigation_active:
                    self.navigator.setFocus()
                else:
                    self.table.setFocus()
                    self.table.scrollTo(index)
        finally:
            self._syncing = False

    def from_tree(self, current, previous):
        if self._syncing or self._resetting or not current.isValid():
            return
        self.table.commit_editor()
        self.navigation_active = True
        self.select(self.outline.source_row(current), self.outline.columns[current.column()], focus=False)

    def from_table(self, current, previous):
        if self._syncing or self._resetting or not current.isValid():
            return
        self.navigation_active = False
        self.select(current.row(), current.column(), focus=False)

    def commit_editors(self):
        self.table.commit_editor()
        self.navigator.commit_editor()

    def paste_outline(self, matrix):
        current = self.navigator.currentIndex()
        if not current.isValid() or not matrix:
            return False
        column = current.column()
        targets = []
        for cells in matrix:
            if not current.isValid() or column + len(cells) > 4:
                raise ValueError('El bloque no cabe en las filas y columnas visibles del árbol.')
            row = self.outline.source_row(current)
            targets.extend((row, self.outline.columns[column + dc], value) for dc, value in enumerate(cells))
            current = self.navigator.indexBelow(current)
        return self.sheet.paste_mapped_cells(targets, (targets[0][0], targets[0][1]))

    def edit_description(self, row):
        if self.sheet.rows[row]['kind'] in ('chapter', 'item'):
            self.navigation_active = True
            self.navigator.setFocus()
            self.navigator.setCurrentIndex(self.outline.for_row(row, 1))
            self.navigator.edit(self.outline.for_row(row, 1))
        else:
            self.table.edit(self.sheet.index(row, 1))
