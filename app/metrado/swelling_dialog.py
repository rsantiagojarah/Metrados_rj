"""Direct FE input for selected consecutive details."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout

from metrado.swelling import adjusted_volume, factor_number


class SwellingDialog(QDialog):
    def __init__(self, count, base, engine, config=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Factor de esponjamiento')
        self.setMinimumWidth(390)
        self.base, self.engine = base, engine
        self.remove = False
        config = config or {}
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f'{count} detalle(s) consecutivo(s) seleccionados · m³'))
        form = QFormLayout()
        self.factor = QLineEdit(config.get('factor', ''))
        self.factor.setPlaceholderText('Por ejemplo: 1,20')
        self.note = QLineEdit(config.get('note', ''))
        self.note.setMaxLength(1200)
        self.note.setPlaceholderText('Opcional; visible al pasar el cursor sobre FE')
        form.addRow('FE (factor):', self.factor)
        form.addRow('Observación:', self.note)
        layout.addLayout(form)
        self.preview = QLabel()
        self.preview.setTextFormat(Qt.PlainText)
        self.preview.setWordWrap(True)
        layout.addWidget(self.preview)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.remove_button = self.buttons.addButton('Quitar FE', QDialogButtonBox.ActionRole)
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
        config = dict(factor=self.factor.text().strip(), note=self.note.text().strip())
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
                                 f'{self.base:.2f} × {config["factor"]} = {total:.2f} m³')
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(True)
        except (ValueError, OverflowError) as error:
            self.preview.setText(str(error))
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)

    def accept(self):
        try:
            self.configuration()
        except (ValueError, OverflowError):
            self.refresh_preview()
            return
        super().accept()
