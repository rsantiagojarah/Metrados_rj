from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QVBoxLayout, QWidget,
)

from metrado.grid import SheetModel, SheetView
from metrado.chrome import add_action, action_toolbar, header_toolbar, workspace_band
from metrado.theme import apply_theme
from metrado.sheet import (
    example_rows, new_row, parent_item, read_project, subtree_end, write_project,
)


class PlantillaWindow(QMainWindow):
    def __init__(self, enlace):
        super().__init__()
        self._enlace, self._path, self._dirty = enlace, None, False
        self.resize(1480, 780)
        self.setMinimumSize(900, 480)
        self.model = SheetModel(enlace, example_rows())
        self.table = SheetView(self.model)
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(6, 0, 6, 6)
        layout.setSpacing(6)
        layout.addWidget(workspace_band())
        self.title_edit = QLineEdit("Ejemplo de planilla de metrado")
        self.title_edit.setPlaceholderText("Nombre de la obra o proyecto")
        header_toolbar(self, self.title_edit)
        hint = QLabel("Capítulo → partida → detalle  ·  Doble clic o F2 para editar  ·  Tab para avanzar  ·  Cantidad directa para áreas o pesos conocidos")
        hint.setObjectName("sheetHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addWidget(self.table, 1)
        note = QLabel("Dimensiones en metros. Los resultados incluyen elementos similares × n.º de veces. Totales por partida; visualización a 2 decimales.")
        note.setObjectName("sheetNote")
        note.setWordWrap(True)
        layout.addWidget(note)
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
        self._action(edit, "+ Capítulo", lambda: self.add_row("chapter"), "Alt+C")
        self._action(edit, "+ Partida", lambda: self.add_row("item"), "Ctrl+Shift+N")
        self._action(edit, "+ Detalle", lambda: self.add_row("detail"), "Ctrl+Return")
        edit.addSeparator()
        self._action(edit, "Cantidad directa…", self.direct_quantity, "Ctrl+D")
        self._action(edit, "Eliminar fila…", self.remove_row, "Ctrl+Delete")
        self.model.changed.connect(self._changed)
        self.title_edit.textEdited.connect(self._changed)
        self.table.selectionModel().currentChanged.connect(self._selection_status)
        apply_theme(self)
        self._refresh_title()
        self._selection_status()

    def _action(self, toolbar, text, callback, shortcut=None):
        return add_action(self, toolbar, text, callback, shortcut)

    def _refresh_title(self):
        name = self._path.name if self._path else "Sin guardar"
        self.setWindowTitle(f"Metrados — {name}" + (" *" if self._dirty else ""))

    def _changed(self, *args):
        self._dirty = True
        self._refresh_title()
        self._selection_status()

    def _selection_status(self, *args):
        index = self.table.currentIndex()
        if index.isValid() and index.row() in self.model.errors:
            message = self.model.errors[index.row()]
        else:
            items = sum(row["kind"] == "item" for row in self.model.rows)
            details = sum(row["kind"] == "detail" for row in self.model.rows)
            pending = sum(self.model.rows[r]["kind"] == "detail" for r in self.model.errors)
            message = f"{items} partidas · {details} detalles · {pending} detalles pendientes"
        self.statusBar().showMessage(message)

    def _select(self, row, column=1):
        index = self.model.index(row, column)
        self.table.setCurrentIndex(index)
        self.table.scrollTo(index)
        self.table.setFocus()

    def add_row(self, kind):
        rows = self.model.rows.copy()
        selected = self.table.currentIndex().row()
        if kind == "chapter":
            position = len(rows)
            used = {r["cells"][0] for r in rows}
            number = 1
            while f"{number:02d}" in used:
                number += 1
            row = new_row(kind, f"{number:02d}", "NUEVO CAPÍTULO")
        elif kind == "item":
            position = subtree_end(rows, selected) if selected >= 0 else len(rows)
            if selected >= 0 and rows[selected]["kind"] == "detail":
                position = subtree_end(rows, parent_item(rows, selected))
            prefix = "01"
            for previous in reversed(rows[:position]):
                if previous["kind"] == "chapter":
                    prefix = previous["cells"][0] or "01"
                    break
            used = {r["cells"][0] for r in rows}
            number = 1
            while f"{prefix}.{number:02d}" in used:
                number += 1
            row = new_row(kind, f"{prefix}.{number:02d}", "NUEVA PARTIDA")
        else:
            selected = selected if selected >= 0 else len(rows) - 1
            parent = parent_item(rows, selected) if selected >= 0 else None
            if parent is None:
                QMessageBox.information(self, "Agregar detalle", "Selecciona primero una partida o uno de sus detalles.")
                return
            position = selected + 1
            row = new_row(kind, description="Nuevo detalle", unit=rows[parent]["cells"][2])
        rows.insert(position, row)
        self.model.replace(rows)
        self._select(position)
        self.table.edit(self.model.index(position, 1))

    def remove_row(self):
        index = self.table.currentIndex().row()
        if index < 0:
            return
        end = subtree_end(self.model.rows, index)
        count = end - index
        answer = QMessageBox.question(self, "Eliminar filas",
            f"Se eliminarán {count} fila(s), incluidos los detalles que dependan de la selección. ¿Continuar?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        rows = self.model.rows[:index] + self.model.rows[end:]
        self.model.replace(rows)
        if rows:
            self._select(min(index, len(rows) - 1))

    def direct_quantity(self):
        index = self.table.currentIndex().row()
        if index < 0 or self.model.rows[index]["kind"] != "detail":
            QMessageBox.information(self, "Cantidad directa", "Selecciona una fila de detalle.")
            return
        row = self.model.rows[index]
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
        if not self._dirty:
            return True
        answer = QMessageBox.question(self, "Cambios sin guardar", "¿Guardar los cambios de esta planilla?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if answer == QMessageBox.Save:
            return self.save_project()
        return answer == QMessageBox.Discard

    def _load(self, title, rows, path=None):
        self.model.replace(rows)
        self.title_edit.setText(title)
        self._path, self._dirty = path, False
        self._refresh_title()
        self._selection_status()

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
        filename, _ = QFileDialog.getOpenFileName(self, "Abrir planilla", "", "Planilla de metrados (*.metrado.json);;JSON (*.json)")
        if not filename:
            return
        try:
            title, rows = read_project(filename)
        except (OSError, ValueError, UnicodeError, RecursionError) as error:
            QMessageBox.warning(self, "No se pudo abrir", str(error))
            return
        self._load(title, rows, Path(filename))

    def save_project(self, save_as=False):
        path = self._path
        if save_as or path is None:
            filename, _ = QFileDialog.getSaveFileName(self, "Guardar planilla", str(path or "Planilla.metrado.json"),
                "Planilla de metrados (*.metrado.json)")
            if not filename:
                return False
            path = Path(filename)
            if not str(path).lower().endswith(".json"):
                path = Path(str(path) + ".metrado.json")
                if path.exists() and QMessageBox.question(self, "Reemplazar archivo",
                        "El archivo ya existe. ¿Reemplazarlo?", QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No) != QMessageBox.Yes:
                    return False
        try:
            write_project(path, self.title_edit.text(), self.model.rows)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "No se pudo guardar", str(error))
            return False
        self._path, self._dirty = path, False
        self._refresh_title()
        self.statusBar().showMessage("Planilla guardada: " + str(path))
        return True

    def closeEvent(self, event):
        if self._can_discard():
            event.accept()
        else:
            event.ignore()
