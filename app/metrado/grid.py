"""Editable desktop grid with the reference sheet's two-level header."""
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QComboBox, QHeaderView, QStyledItemDelegate, QTableView

from metrado.sheet import DIMENSIONS, UNITS, calculate
from metrado.steel import (
    DIAMETERS, STEEL_LABELS, STEEL_WIDTHS, apply_bar_spec, header_mode, set_bar_diameter,
)
from metrado import theme

LABELS = ("ÍTEM", "DESCRIPCIÓN", "Und", "Elem.\nsimil.", "Largo", "Ancho", "Alto",
          "N.º de\nveces", "Lon.", "Área", "Vol.", "Kg.", "Und.", "Total")
WIDTHS = (88, 490, 44, 48, 66, 66, 66, 48, 64, 64, 64, 64, 64, 88)


DISPLAY_ROLE = int(Qt.DisplayRole)
EDIT_ROLE = int(Qt.EditRole)
ALIGNMENT_ROLE = int(Qt.TextAlignmentRole)
FONT_ROLE = int(Qt.FontRole)
FOREGROUND_ROLE = int(Qt.ForegroundRole)
BACKGROUND_ROLE = int(Qt.BackgroundRole)
TOOLTIP_ROLE = int(Qt.ToolTipRole)
DATA_ROLES = frozenset((DISPLAY_ROLE, EDIT_ROLE, ALIGNMENT_ROLE, FONT_ROLE,
                        FOREGROUND_ROLE, BACKGROUND_ROLE, TOOLTIP_ROLE))
READ_FLAGS = Qt.ItemIsSelectable | Qt.ItemIsEnabled
EDIT_FLAGS = READ_FLAGS | Qt.ItemIsEditable


class SheetModel(QAbstractTableModel):
    changed = Signal()

    def __init__(self, engine, rows):
        super().__init__()
        self.engine, self.rows = engine, rows
        self.values, self.errors = calculate(rows, engine)
        self._fonts = {}
        for textual in (False, True):
            for bold in (False, True):
                font = QFont(theme.FONT_FAMILY if textual else "Consolas")
                font.setPixelSize(11)
                font.setWeight(QFont.DemiBold if bold else QFont.Normal)
                self._fonts[textual, bold] = font
        self._colors = {color: QColor(color) for color in (
            theme.CHAPTER, theme.WARNING, theme.DETAIL, theme.TEXT,
            theme.HEADER, theme.WARNING_BACKGROUND, theme.SURFACE)}
        self._alignments = tuple(int(Qt.AlignVCenter | (
            Qt.AlignLeft if c in (0, 1) else Qt.AlignCenter if c == 2 else Qt.AlignRight))
            for c in range(14))
        self._rebuild_structure()
        self._pending = sum(self.rows[r]["kind"] == "detail" for r in self.errors)
        self._refresh_summary()

    def _rebuild_structure(self):
        self._owners, self._ends = [], {}
        self._items = self._details = 0
        owner = None
        for index, row in enumerate(self.rows):
            kind = row["kind"]
            if kind != "detail":
                if owner is not None:
                    self._ends[owner] = index
                owner = index if kind == "item" else None
            self._owners.append(owner)
            self._items += kind == "item"
            self._details += kind == "detail"
        if owner is not None:
            self._ends[owner] = len(self.rows)

    def _refresh_summary(self):
        self.summary_text = f"{self._items} partidas · {self._details} detalles · {self._pending} detalles pendientes"

    def selection_mode(self, row):
        if row < 0 or row >= len(self.rows):
            return "standard"
        owner = self._owners[row]
        return "steel" if owner is not None and self.rows[owner]["cells"][2] == "kg" else "standard"

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else 14

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return getattr(self, "header_labels", LABELS)[section] if orientation == Qt.Horizontal else str(section + 1)

    def editable(self, row, column):
        kind = self.rows[row]["kind"]
        if kind == "chapter":
            return column in (0, 1)
        if kind == "item":
            return column in (0, 1, 2)
        unit = self.rows[row]["cells"][2]
        if unit == "kg":
            return column in (1, 3, 4, 5, 6, 7, 9)
        return column in (1, 3, 7) or column in [c for c, _ in DIMENSIONS.get(unit, ())]

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return EDIT_FLAGS if self.editable(index.row(), index.column()) else READ_FLAGS

    def data(self, index, role=DISPLAY_ROLE):
        if not index.isValid() or role not in DATA_ROLES:
            return None
        r, c = index.row(), index.column()
        row = self.rows[r]
        kind = row["kind"]
        if role == ALIGNMENT_ROLE:
            return self._alignments[c]
        if role == FONT_ROLE:
            return self._fonts[c in (1, 2), kind != "detail"]
        if role == FOREGROUND_ROLE:
            if kind == "chapter":
                return self._colors[theme.CHAPTER]
            if r in self.errors and c in (3, 4, 5, 6, 7, 9, 10, 13):
                return self._colors[theme.WARNING]
            return self._colors[theme.DETAIL if kind == "detail" else theme.TEXT]
        if role == BACKGROUND_ROLE:
            if kind == "chapter":
                return self._colors[theme.HEADER]
            if r in self.errors and kind == "detail" and c in (3, 4, 5, 6, 7, 9, 10):
                return self._colors[theme.WARNING_BACKGROUND]
            return self._colors[theme.SURFACE]
        steel = kind == "detail" and row["cells"][2] == "kg"
        if role == TOOLTIP_ROLE:
            if steel and c == 9:
                return "Elige el diámetro con doble clic o F2. El peso se recalcula automáticamente."
            if steel and c == 1:
                return row["cells"][1] + " · También puedes incluir el diámetro, por ejemplo: 53 Ø1\"."
            if steel and c == 7:
                return "Cantidad de barras. Incluye las repeticiones guardadas; editar aquí establece la cantidad total."
            if r in self.errors:
                return self.errors[r]
            if row["direct"]:
                return "Cantidad base directa: " + row["direct"] + ". Se aplican elementos similares y n.º de veces."
            return row["cells"][c] or "Doble clic o F2 para editar."
        if steel:
            if c == 9:
                return row["cells"][7]
            if c == 7:
                times = self.values.get((r, 7))
                if times is None:
                    return row["cells"][9] if row["direct"] else row["cells"][10]
                return f"{times:g}"
        if role == EDIT_ROLE:
            return row["cells"][c]
        value = self.values.get((r, c))
        if steel:
            if c == 12:
                return ""
            if c in (10, 11):
                value = self.values.get((r, 11 if c == 10 else 12))
                return "" if value is None else f"{value:.2f}"
            if c in (4, 5, 6) and not row["direct"]:
                try:
                    return f"{float(row['cells'][c].replace(',', '.') or '0'):.2f}" if row["cells"][c] or c != 4 else ""
                except ValueError:
                    return row["cells"][c]
        if value is not None:
            return f"{value:.2f}"
        if c == 13 and r in self.errors and kind == "item":
            return "Pendiente"
        if c == 4 and row["direct"]:
            return "ÁREA" if row["cells"][2] == "m2" else "DIRECTO"
        if c == 1 and kind == "detail":
            return "      " + row["cells"][c]
        return row["cells"][c]

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid() or not self.editable(index.row(), index.column()):
            return False
        r, c = index.row(), index.column()
        value = str(value).strip()
        if c == 2 and value not in UNITS:
            return False
        row = self.rows[r]
        if row["kind"] == "detail" and row["cells"][2] == "kg" and c == 9:
            if value == row["cells"][7]:
                return False
            try:
                self.engine.ask_sheet_steel(1.0, 0.0, 0.0, value, 1.0, 1.0, 1.0)
            except (ValueError, OverflowError):
                return False
            set_bar_diameter(row["cells"], value)
            self.recalculate(r)
            return True
        if row["kind"] == "detail" and row["cells"][2] == "kg" and c == 7:
            if value == self.data(index, Qt.EditRole):
                return False
            if row["direct"]:
                row["cells"][9] = value
            else:
                row["cells"][10] = value
                row["cells"][9] = "1"
            self.recalculate(r)
            return True
        if self.rows[r]["cells"][c] == value and not (c in (4, 5, 6) and self.rows[r]["direct"]):
            return False
        self.rows[r]["cells"][c] = value
        if c in (4, 5, 6, 7, 9, 10):
            self.rows[r]["direct"] = ""
        if c == 1 and self.rows[r]["kind"] == "detail" and self.rows[r]["cells"][2] == "kg":
            apply_bar_spec(self.rows[r]["cells"], value)
        if c == 2:
            for child in self.rows[r + 1:]:
                if child["kind"] != "detail":
                    break
                child["cells"][2] = value
                child["cells"][4:7] = [""] * 3
                if value == "kg":
                    child["cells"][7] = ""
                    child["cells"][9] = "1"
                    child["cells"][10] = ""
                else:
                    child["cells"][7] = "1"
                    child["cells"][9] = ""
                    child["cells"][10] = ""
                child["direct"] = ""
        self.recalculate(r)
        return True

    def recalculate(self, row=None):
        if row is None:
            self.values, self.errors = calculate(self.rows, self.engine)
            self._rebuild_structure()
            self._pending = sum(self.rows[r]["kind"] == "detail" for r in self.errors)
            start, end = 0, len(self.rows)
        else:
            owner = self._owners[row]
            start = row if owner is None else owner
            end = row + 1 if owner is None else self._ends[owner]
            before = sum(r in self.errors and self.rows[r]["kind"] == "detail"
                         for r in range(start, end))
            values, errors = calculate(self.rows[start:end], self.engine)
            for r in range(start, end):
                self.errors.pop(r, None)
                for column in range(14):
                    self.values.pop((r, column), None)
            self.values.update(((r + start, c), value) for (r, c), value in values.items())
            self.errors.update((r + start, error) for r, error in errors.items())
            after = sum(self.rows[start + r]["kind"] == "detail" for r in errors)
            self._pending += after - before
        self._refresh_summary()
        if end > start:
            self.dataChanged.emit(self.index(start, 0), self.index(end - 1, 13))
        self.changed.emit()

    def replace(self, rows):
        self.beginResetModel()
        self.rows = rows
        self.values, self.errors = calculate(rows, self.engine)
        self._rebuild_structure()
        self._pending = sum(self.rows[r]["kind"] == "detail" for r in self.errors)
        self._refresh_summary()
        self.endResetModel()
        self.changed.emit()

    def set_direct(self, index, value):
        if self.rows[index]["kind"] != "detail":
            return
        self.rows[index]["direct"] = value
        self.rows[index]["cells"][4:7] = [""] * 3
        self.recalculate(index)


class GroupedHeader(QHeaderView):
    def __init__(self, parent):
        super().__init__(Qt.Horizontal, parent)
        self.mode = "standard"
        self.setFixedHeight(62)
        self.setMinimumSectionSize(38)
        self.setSectionResizeMode(QHeaderView.Interactive)
        self.setSectionsMovable(False)

    def set_mode(self, mode):
        if self.mode != mode:
            self.mode = mode
            self.viewport().update()

    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        painter.fillRect(event.rect(), QColor(theme.HEADER))
        font = QFont(theme.FONT_FAMILY)
        font.setPixelSize(11)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        height, half = self.height(), self.height() // 2
        labels = STEEL_LABELS if self.mode == "steel" else LABELS

        def cell(first, last, top, bottom, text, rotate=False):
            x = self.sectionViewportPosition(first)
            width = sum(self.sectionSize(i) for i in range(first, last + 1))
            rect = QRect(x, top, width, bottom - top)
            painter.setPen(QPen(QColor(theme.BORDER), 1))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
            painter.setPen(QColor(theme.TEXT))
            if rotate:
                painter.save()
                painter.translate(rect.center())
                painter.rotate(-90)
                painter.drawText(QRect(-rect.height() // 2, -rect.width() // 2,
                                       rect.height(), rect.width()), Qt.AlignCenter, text)
                painter.restore()
            else:
                painter.drawText(rect.adjusted(2, 1, -2, -1), Qt.AlignCenter, text)

        for column in (0, 1, 2, 3, 7, 13):
            cell(column, column, 0, height, labels[column], column in (2, 3, 7))
        cell(4, 6, 0, half, "DIMENSIONES")
        cell(8, 12, 0, half, "METRADO")
        for column in (4, 5, 6, 8, 9, 10, 11, 12):
            cell(column, column, half, height, labels[column])
        painter.end()


class SheetDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._grid_pen = QPen(QColor(theme.BORDER), 1, Qt.DotLine)

    def createEditor(self, parent, option, index):
        if index.column() == 2:
            editor = QComboBox(parent)
            editor.addItems(UNITS)
            return editor
        row = index.model().rows[index.row()]
        if index.column() == 9 and row["kind"] == "detail" and row["cells"][2] == "kg":
            editor = QComboBox(parent)
            editor.addItems(DIAMETERS)
            current = index.data(Qt.EditRole)
            if current not in DIAMETERS:
                editor.insertItem(0, current)
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

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        painter.save()
        painter.setPen(self._grid_pen)
        painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())
        painter.drawLine(option.rect.topRight(), option.rect.bottomRight())
        painter.restore()


class SheetView(QTableView):
    def __init__(self, model):
        super().__init__()
        self.setModel(model)
        self.setHorizontalHeader(GroupedHeader(self))
        self.setItemDelegate(SheetDelegate(self))
        self.setShowGrid(False)
        self.setAlternatingRowColors(False)
        self.setWordWrap(False)
        self.setSelectionMode(QTableView.SingleSelection)
        self.setEditTriggers(QTableView.DoubleClicked | QTableView.EditKeyPressed | QTableView.AnyKeyPressed)
        self.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.verticalHeader().setDefaultSectionSize(28)
        self.verticalHeader().setMinimumSectionSize(24)
        self.verticalHeader().setFixedWidth(34)
        for column, width in enumerate(WIDTHS):
            self.setColumnWidth(column, width)
        self.selectionModel().currentChanged.connect(self.sync_header)
        self.model().modelReset.connect(lambda: self.sync_header(self.currentIndex()))
        self.model().changed.connect(lambda: self.sync_header(self.currentIndex()))
        self.sync_header(self.currentIndex())

    def sync_header(self, current, _previous=None):
        row = current.row() if current.isValid() else -1
        mode = self.model().selection_mode(row)
        if self.horizontalHeader().mode == mode:
            return
        self.horizontalHeader().set_mode(mode)
        self.model().header_labels = STEEL_LABELS if mode == "steel" else LABELS
        self.model().headerDataChanged.emit(Qt.Horizontal, 0, 13)
        for column, width in enumerate(STEEL_WIDTHS if mode == "steel" else WIDTHS):
            self.setColumnWidth(column, width)
        # Qt repaints selection changes and resized columns only where needed.
