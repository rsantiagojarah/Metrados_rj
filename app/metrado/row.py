from PySide6.QtWidgets import QFormLayout, QLabel, QLineEdit, QComboBox, QWidget

from metrado.messages import ERROR_TEXT, FIELDS, UNITS


class PartidaRow(QWidget):
    def __init__(self, enlace):
        super().__init__()
        self._enlace = enlace
        self._edits = {}
        self._labels = {}
        form = QFormLayout(self)
        self._name = QLineEdit()
        self._name.editingFinished.connect(self._recalculate)
        form.addRow("partida", self._name)
        self._unit = QComboBox()
        for code, label in UNITS:
            self._unit.addItem(label, code)
        self._unit.currentIndexChanged.connect(self._on_unit_changed)
        form.addRow("unidad", self._unit)
        for code, names in FIELDS.items():
            for name in names:
                if name in self._edits:
                    continue
                edit = QLineEdit()
                edit.editingFinished.connect(self._recalculate)
                label = QLabel(name)
                self._edits[name] = edit
                self._labels[name] = label
                form.addRow(label, edit)
        self._quantity = QLineEdit()
        self._quantity.setReadOnly(True)
        form.addRow("cantidad", self._quantity)
        self._error = QLabel("")
        form.addRow("", self._error)
        self._updating = False
        self._show_fields()

    def focus_name(self):
        self._name.setFocus()

    def _unit_code(self):
        return self._unit.currentData()

    def _on_unit_changed(self):
        self._updating = True
        self._show_fields()
        self._quantity.clear()
        self._error.setText("")
        self._updating = False
        if self._required_text_ready():
            self._recalculate()

    def _required_text_ready(self):
        return all(self._edits[name].text().strip() != "" for name in FIELDS[self._unit_code()])

    def _show_fields(self):
        visible = set(FIELDS[self._unit_code()])
        for name, edit in self._edits.items():
            shown = name in visible
            edit.setVisible(shown)
            self._labels[name].setVisible(shown)

    def _recalculate(self):
        if self._updating:
            return
        code = self._unit_code()
        measures = []
        for name in FIELDS[code]:
            text = self._edits[name].text().strip().replace(",", ".")
            if text == "":
                self._quantity.clear()
                self._error.setText(ERROR_TEXT["blank_measure"])
                return
            try:
                number = float(text)
            except ValueError:
                self._quantity.clear()
                self._error.setText(ERROR_TEXT["not_a_number"])
                return
            measures.append((name, number))
        try:
            quantity = self._enlace.ask_quantity(self._name.text(), code, measures)
        except ValueError as error:
            self._quantity.clear()
            self._error.setText(ERROR_TEXT.get(str(error), "No se pudo calcular la cantidad."))
            return
        self._error.setText("")
        self._quantity.setText(_format_quantity(quantity))


def _format_quantity(value):
    return f"{value:.10f}".rstrip("0").rstrip(".")
