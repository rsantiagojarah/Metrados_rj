"""Sheet choice and read-only preview; no writes until explicit confirmation."""
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QHeaderView,
    QLabel, QTableView, QVBoxLayout,
)


class PreviewModel(QAbstractTableModel):
    def __init__(self, rows, parent=None):
        super().__init__(parent)
        self.rows = rows

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else 3

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid() and role in (Qt.DisplayRole, Qt.ToolTipRole):
            row = self.rows[index.row()]
            text = row['cells'][index.column()]
            if index.column() == 1 and role == Qt.DisplayRole:
                text = '    ' * row['level'] + text
            return text

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return ('Ítem', 'Descripción', 'Unidad')[section] if orientation == Qt.Horizontal else section + 1


class ExcelImportDialog(QDialog):
    def __init__(self, budget, parent=None):
        super().__init__(parent)
        self.budget, self.result = budget, None
        self.setWindowTitle('Importar partidas desde Excel')
        self.resize(860, 560)
        layout = QVBoxLayout(self)
        label = QLabel('Elige la hoja. Se creará una planilla nueva con sus títulos, subtítulos y partidas.\n'
                       'Solo se importan ítems, descripciones y unidades; no precios, cantidades ni detalles.')
        label.setWordWrap(True)
        layout.addWidget(label)
        self.sheet = QComboBox()
        self.sheet.addItems(list(budget.headers))
        layout.addWidget(self.sheet)
        self.preview = QTableView()
        self.preview.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.preview.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.preview, 1)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.PlainText)
        layout.addWidget(self.summary)
        note = QLabel('El Excel original no se modifica. Antes de reemplazar la obra abierta podrás guardar sus cambios pendientes.')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText('Importar como nueva planilla')
        self.buttons.button(QDialogButtonBox.Cancel).setText('Cancelar')
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.sheet.currentTextChanged.connect(self.show_sheet)
        self.show_sheet(self.sheet.currentText())

    def show_sheet(self, name):
        self.result = None
        try:
            self.result = self.budget.read(name)
            self.summary.setText(f'{self.result.titles} títulos/subtítulos · {self.result.items} partidas · '
                                 f'{len(self.result.rows)} filas. Los códigos se conservarán como están en Excel.')
        except (OSError, ValueError) as error:
            self.summary.setText(str(error))
        old = self.preview.model()
        self.preview.setModel(PreviewModel(self.result.rows if self.result else [], self.preview))
        if old:
            old.deleteLater()
        self.preview.setColumnWidth(0, 115)
        self.preview.setColumnWidth(2, 70)
        self.preview.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(self.result is not None)

    def accept(self):
        if self.result is not None:
            super().accept()
