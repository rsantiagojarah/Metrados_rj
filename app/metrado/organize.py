"""Searchable destination picker for moving complete outline blocks."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QLineEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
)

from metrado.hierarchy import MEASUREMENT_KINDS, can_parent


class DestinationDialog(QDialog):
    def __init__(self, rows, source, outline, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Mover a…')
        self.resize(570, 470)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Elige el grupo de destino. Se moverá la fila con todos sus descendientes.'))
        search = QLineEdit()
        search.setPlaceholderText('Buscar por código o descripción…')
        layout.addWidget(search)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setUniformRowHeights(True)
        layout.addWidget(self.tree)
        root = QTreeWidgetItem(self.tree, ['Nivel principal'])
        root.setData(0, Qt.UserRole, -1)
        if rows[source]['kind'] in MEASUREMENT_KINDS:
            root.setFlags(root.flags() & ~Qt.ItemIsSelectable)
        self.entries = [root]
        nodes = {}
        for index, row in enumerate(rows):
            if source <= index < outline.ends[source] or row['kind'] == 'detail':
                continue
            allowed = can_parent(rows, source, index, outline)
            if row['kind'] in ('item', 'detail_group') and not allowed:
                continue
            owner = nodes.get(outline.parents[index], root)
            item = QTreeWidgetItem(owner, [f"{row['cells'][0]}  {row['cells'][1]}"])
            item.setData(0, Qt.UserRole, index)
            if not allowed:
                item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            nodes[index] = item
            self.entries.append(item)
        self.tree.expandAll()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.accept_button = buttons.button(QDialogButtonBox.Ok)
        self.accept_button.setText('Mover aquí')
        self.accept_button.setEnabled(False)
        buttons.button(QDialogButtonBox.Cancel).setText('Cancelar')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.tree.itemSelectionChanged.connect(self._selection)
        self.tree.itemDoubleClicked.connect(lambda *_: self.accept() if self.accept_button.isEnabled() else None)
        search.textChanged.connect(self._filter)
        layout.addWidget(buttons)

    def _selection(self):
        selected = self.tree.selectedItems()
        self.accept_button.setEnabled(bool(selected) and not selected[0].isHidden())

    def _filter(self, text):
        text = text.casefold().strip()
        for item in reversed(self.entries):
            match = text in item.text(0).casefold()
            visible_child = any(not item.child(i).isHidden() for i in range(item.childCount()))
            item.setHidden(not match and not visible_child)
        self._selection()

    @property
    def destination(self):
        value = self.tree.currentItem().data(0, Qt.UserRole)
        return None if value == -1 else value
