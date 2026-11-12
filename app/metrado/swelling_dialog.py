"""Named factor adjustment for selected consecutive details."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout

from metrado.swelling import adjusted_volume, factor_number
from metrado.display import format_two_decimals
from metrado.numeric_edit import NumericEdit


class SwellingDialog(QDialog):
    def __init__(self, count, base, engine, config=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Ajuste por factor')
        self.setMinimumWidth(470)
        self.base, self.engine = base, engine
        self.remove = False
        config = config or {}
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f'{count} detalle(s) consecutivo(s) seleccionados · m³'))
        layout.addWidget(QLabel('0,70 aplica el 70 % del volumen; 1,20 aplica el 120 %.'))
        form = QFormLayout()
        self.factor = NumericEdit(config.get('factor', ''), positive=True, validate=factor_number)
        self.factor.setPlaceholderText('0,70 = 70 % · 1,20 = 120 %')
        self.note = QLineEdit(config.get('note', ''))
        self.note.setMaxLength(1200)
        self.note.setPlaceholderText('Ej.: Reparto de relleno: material de préstamo — 70 %')
        form.addRow('F (factor):', self.factor)
        form.addRow('Descripción del ajuste:', self.note)
        layout.addLayout(form)
        self.preview = QLabel()
        self.preview.setTextFormat(Qt.PlainText)
        self.preview.setWordWrap(True)
        self.factor.inputError.connect(self.preview.setText)
        layout.addWidget(self.preview)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.remove_button = self.buttons.addButton('Quitar ajuste', QDialogButtonBox.ActionRole)
        self.remove_button.setEnabled(bool(config))
        self.remove_button.clicked.connect(self.remove_factor)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.factor.textChanged.connect(self.refresh_preview)
        self.refresh_preview()
        self.factor.setFocus()
        self.factor.selectAll()

    def configuration(self):
        if self.remove:
            return None
        config = dict(factor=self.factor.number_text(), note=self.note.text().strip())
        factor_number(config['factor'])
        if self.base is not None:
            adjusted_volume(self.base, config, self.engine)
        return config

    def remove_factor(self):
        self.remove = True
        super().accept()

    def refresh_preview(self, *args):
        try:
            config = self.configuration()
            total = None if self.base is None else adjusted_volume(self.base, config, self.engine)
            self.preview.setText('Subtotal pendiente: completa los detalles.' if total is None else
                                 f'{format_two_decimals(self.base)} × {config["factor"]} = '
                                 f'{format_two_decimals(total)} m³')
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(True)
        except (ValueError, OverflowError) as error:
            self.preview.setText(str(error))
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)

    def accept(self):
        try:
            config = self.configuration()
        except (ValueError, OverflowError):
            self.refresh_preview()
            return
        self.factor.setText(config['factor'])
        super().accept()
