"""Numeric editors calculate on commit and retain the previous valid value."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLineEdit, QStyledItemDelegate
from metrado.arithmetic import HELP, numeric_text


class NumericEdit(QLineEdit):
    inputError = Signal(str)

    def __init__(self, text='', parent=None, *, validate=None, **rules):
        super().__init__(text, parent)
        self._previous = text
        self._rules = rules
        self._validate = validate
        self.setToolTip(HELP)
        self.editingFinished.connect(self.commit_number)

    def number_text(self):
        value = numeric_text(self.text(), **self._rules)
        if self._validate is not None:
            self._validate(value)
        return value

    def commit_number(self):
        try:
            value = self.number_text()
        except ValueError as error:
            self.setText(self._previous)
            self.inputError.emit(str(error))
            return False
        self._previous = value
        self.setText(value)
        return True


class NumericDelegate(QStyledItemDelegate):
    inputError = Signal(str)

    def __init__(self, parent=None, *, validate=None):
        super().__init__(parent)
        self._validate = validate

    def setModelData(self, editor, model, index):
        try:
            value = numeric_text(editor.text(), positive=True)
            if self._validate is not None:
                self._validate(value)
        except ValueError as error:
            self.inputError.emit(str(error))
            return
        model.setData(index, value)
