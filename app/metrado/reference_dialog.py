"""Keyboard-only entry point for links; explicit, named unit conversions."""
from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout

from metrado.shortcuts import FinderDialog
from metrado.references import factor_number


class ReferencePicker(FinderDialog):
    def __init__(self, entries, parent=None):
        super().__init__('Referenciar partida — escribe para buscar', entries, parent)
        self.buttons.hide()
        self.search.setPlaceholderText('/ Nombre o código de la partida…')

    def eventFilter(self, watched, event):
        if watched is self.search and event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.accept()
            return True
        return super().eventFilter(watched, event)


class ConversionDialog(QDialog):
    def __init__(self, source_unit, target_unit, parent=None, name='', factor=''):
        super().__init__(parent)
        self.setWindowTitle('Conversión de unidades')
        self.resize(470, 230)
        layout = QVBoxLayout(self)
        text = QLabel(f'El origen está en {source_unit} y esta partida en {target_unit}.\n'
                      f'Resultado = valor referenciado × factor ({target_unit}/{source_unit}).\n'
                      'Indica qué representa el factor, por ejemplo: Espesor, Densidad o Rendimiento.')
        text.setWordWrap(True)
        layout.addWidget(text)
        form = QFormLayout()
        self.name = QLineEdit(name)
        self.name.setMaxLength(160)
        self.factor = QLineEdit(factor)
        self.factor.setPlaceholderText('Ejemplo: 0,15')
        form.addRow('Significado del factor', self.name)
        form.addRow(f'Valor ({target_unit}/{source_unit})', self.factor)
        layout.addLayout(form)
        self.error = QLabel()
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.name.setFocus()

    def accept(self):
        try:
            if not self.name.text().strip():
                raise ValueError('Indica qué representa el factor.')
            factor_number(self.factor.text())
        except ValueError as error:
            self.error.setText(str(error))
            return
        super().accept()
