"""Small, editable catalogue and selection-based hook application."""
from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHeaderView,
    QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QVBoxLayout,
)
from metrado.steel_config import DIAMETERS, FIELDS, REFERENCE, SOURCE, number, validate_catalog


def label(text):
    widget = QLabel(text)
    widget.setTextFormat(Qt.PlainText)
    widget.setWordWrap(True)
    return widget


class CatalogDialog(QDialog):
    def __init__(self, catalog, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Tabla global de aceros')
        self.resize(680, 650)
        self.original = deepcopy(catalog)
        layout = QVBoxLayout(self)
        layout.addWidget(label('Valores para nuevas partidas. Guardar esta tabla NO recalcula las obras existentes.'))
        self.table = QTableWidget(len(DIAMETERS), 4)
        self.table.setHorizontalHeaderLabels(['Diámetro', 'Peso (kg/m)', 'Gancho 90° (m)', 'Empalme (m)'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        for i, dia in enumerate(DIAMETERS):
            for j, text in enumerate([dia, *(catalog[dia][f] for f in FIELDS)]):
                item = QTableWidgetItem(text)
                if j == 0:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, j, item)
        layout.addWidget(self.table, 1)
        layout.addWidget(label('Gancho = longitud libre + longitud del doblez. Un único valor por gancho.'))
        layout.addWidget(label(REFERENCE))
        source = QLabel(f'<a href="{SOURCE}">Consultar E.060 — fuente de las referencias iniciales</a>')
        source.setOpenExternalLinks(True)
        layout.addWidget(source)
        self.error = label('')
        layout.addWidget(self.error)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Save).setText('Guardar')
        self.buttons.button(QDialogButtonBox.Cancel).setText('Cancelar')
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.table.itemChanged.connect(self.refresh)
        self.refresh()

    def configuration(self):
        catalog = {dia: {field: self.table.item(i, j + 1).text().strip()
                         for j, field in enumerate(FIELDS)} for i, dia in enumerate(DIAMETERS)}
        validate_catalog(catalog)
        return catalog

    def refresh(self, *args):
        try:
            self.configuration()
            self.error.setText('')
            self.buttons.button(QDialogButtonBox.Save).setEnabled(True)
        except ValueError as error:
            self.error.setText(str(error))
            self.buttons.button(QDialogButtonBox.Save).setEnabled(False)

    def accept(self):
        self.table.clearFocus()
        try:
            self.configuration()
        except ValueError:
            self.refresh()
            return
        super().accept()


class HooksDialog(QDialog):
    def __init__(self, rows, catalogs, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Aplicar ganchos de 90°')
        self.resize(520, 420)
        layout = QVBoxLayout(self)
        layout.addWidget(label(f'{len(rows)} detalle(s) seleccionado(s). Se reemplazan sus ganchos; no se acumulan.'))
        proposals = {}
        for row, catalog in zip(rows, catalogs):
            dia = row['cells'][7]
            key = (dia, catalog[dia]['hook'])
            proposals[key] = proposals.get(key, 0) + 1
        table = QTableWidget(len(proposals), 3)
        table.setHorizontalHeaderLabels(['Diámetro', 'Propuesto por gancho (m)', 'Detalles'])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().hide()
        for i, ((dia, hook), count) in enumerate(proposals.items()):
            for j, text in enumerate((dia, hook, str(count))):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                table.setItem(i, j, item)
        layout.addWidget(table, 1)
        form = QFormLayout()
        self.count = QComboBox()
        self.count.addItems(['1 gancho', '2 ganchos'])
        form.addRow('Para toda la selección:', self.count)
        self.custom = QCheckBox('Usar otra longitud por gancho en toda la selección')
        form.addRow(self.custom)
        self.length = QLineEdit()
        self.length.setMaxLength(64)
        self.length.setPlaceholderText('Metros, incluye el doblez; por ejemplo 0,30')
        self.length.setEnabled(False)
        form.addRow('Longitud personalizada (m):', self.length)
        layout.addLayout(form)
        layout.addWidget(label('Se usan los valores guardados con cada detalle o partida. '
                               'Los empalmes se recalculan con largo + ganchos, por tramos de 9 m.'))
        if any('steel_hooks' not in row for row in rows):
            layout.addWidget(label('Esta selección incluye detalles antiguos: al aplicar, sus empalmes pasarán '
                                   'a cálculo automático y usarán el peso de la tabla. Puedes deshacer con Ctrl+Z.'))
        self.error = label('')
        layout.addWidget(self.error)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText('Aplicar')
        self.buttons.button(QDialogButtonBox.Cancel).setText('Cancelar')
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.custom.toggled.connect(self.length.setEnabled)
        self.custom.toggled.connect(self.refresh)
        self.length.textChanged.connect(self.refresh)
        self.refresh()

    def configuration(self):
        override = self.length.text().strip() if self.custom.isChecked() else None
        if override is not None:
            number(override)
        return self.count.currentIndex() + 1, override

    def refresh(self, *args):
        try:
            self.configuration()
            self.error.setText('')
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(True)
        except ValueError as error:
            self.error.setText(str(error))
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)

    def accept(self):
        try:
            self.configuration()
        except ValueError:
            self.refresh()
            return
        super().accept()
