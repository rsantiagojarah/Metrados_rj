"""Editable desktop grid with the reference sheet's two-level header."""
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QComboBox, QHeaderView, QStyledItemDelegate, QTableView

from metrado.sheet import DIMENSIONS, UNITS, calculate
from metrado import theme

LABELS = ("ÍTEM", "DESCRIPCIÓN", "Und", "Elem.\nsimil.", "Largo", "Ancho", "Alto",
          "N.º de\nveces", "Lon.", "Área", "Vol.", "Kg.", "Und.", "Total")
WIDTHS = (88, 490, 44, 48, 66, 66, 66, 48, 64, 64, 64, 64, 64, 88)


class SheetModel(QAbstractTableModel):
    changed = Signal()

    def __init__(self, engine, rows):
        super().__init__()
        self.engine, self.rows = engine, rows
        self.values, self.errors = calculate(rows, engine)

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else 14

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return LABELS[section] if orientation == Qt.Horizontal else str(section + 1)

    def editable(self, row, column):
        kind = self.rows[row]["kind"]
        if kind == "chapter":
            return column in (0, 1)
        if kind == "item":
            return column in (0, 1, 2)
        unit = self.rows[row]["cells"][2]
        return column in (1, 3, 7) or column in [c for c, _ in DIMENSIONS.get(unit, ())]

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if self.editable(index.row(), index.column()):
            flags |= Qt.ItemIsEditable
        return flags

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        r, c = index.row(), index.column()
        row, value = self.rows[r], self.values.get((r, c))
        if role == Qt.EditRole:
            return row["cells"][c]
        if role == Qt.DisplayRole:
            if value is not None:
                return f"{value:.2f}"
            if c == 13 and r in self.errors and row["kind"] == "item":
                return "Pendiente"
            if c == 4 and row["direct"]:
                return "ÁREA" if row["cells"][2] == "m2" else "DIRECTO"
            if c == 1 and row["kind"] == "detail":
                return "      " + row["cells"][c]
            return row["cells"][c]
        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignVCenter | (Qt.AlignLeft if c in (0, 1) else Qt.AlignCenter if c == 2 else Qt.AlignRight))
        if role == Qt.FontRole:
            font = QFont(theme.FONT_FAMILY if c in (1, 2) else "Consolas")
            font.setPixelSize(11)
            font.setWeight(QFont.DemiBold if row["kind"] != "detail" else QFont.Normal)
            return font
        if role == Qt.ForegroundRole:
            if row["kind"] == "chapter":
                return QColor(theme.CHAPTER)
            if r in self.errors and c in (3, 4, 5, 6, 7, 13):
                return QColor(theme.WARNING)
            return QColor(theme.DETAIL if row["kind"] == "detail" else theme.TEXT)
        if role == Qt.BackgroundRole:
            if row["kind"] == "chapter":
                return QColor(theme.HEADER)
            if r in self.errors and row["kind"] == "detail" and c in (3, 4, 5, 6, 7):
                return QColor(theme.WARNING_BACKGROUND)
            return QColor(theme.SURFACE)
        if role == Qt.ToolTipRole:
            if r in self.errors:
                return self.errors[r]
            if row["direct"]:
                return "Cantidad base directa: " + row["direct"] + ". Se aplican elementos similares y n.º de veces."
            return row["cells"][c] or "Doble clic o F2 para editar."
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid() or not self.editable(index.row(), index.column()):
            return False
        r, c = index.row(), index.column()
        value = str(value).strip()
        if c == 2 and value not in UNITS:
            return False
        if self.rows[r]["cells"][c] == value and not (c in (4, 5, 6) and self.rows[r]["direct"]):
            return False
        self.rows[r]["cells"][c] = value
        if c in (4, 5, 6):
            self.rows[r]["direct"] = ""
        if c == 2:
            for child in self.rows[r + 1:]:
                if child["kind"] != "detail":
                    break
                child["cells"][2] = value
                child["cells"][4:7] = [""] * 3
                child["direct"] = ""
        self.recalculate()
        return True

    def recalculate(self):
        self.values, self.errors = calculate(self.rows, self.engine)
        if self.rows:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self.rows) - 1, 13))
        self.changed.emit()

    def replace(self, rows):
        self.beginResetModel()
        self.rows = rows
        self.values, self.errors = calculate(rows, self.engine)
        self.endResetModel()
        self.changed.emit()

    def set_direct(self, index, value):
        if self.rows[index]["kind"] != "detail":
            return
        self.rows[index]["direct"] = value
        self.rows[index]["cells"][4:7] = [""] * 3
        self.recalculate()


class GroupedHeader(QHeaderView):
    def __init__(self, parent):
        super().__init__(Qt.Horizontal, parent)
        self.setFixedHeight(62)
        self.setMinimumSectionSize(38)
        self.setSectionResizeMode(QHeaderView.Interactive)
        self.setSectionsMovable(False)

    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        painter.fillRect(event.rect(), QColor(theme.HEADER))
        font = QFont(theme.FONT_FAMILY)
        font.setPixelSize(11)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        height, half = self.height(), self.height() // 2

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
            cell(column, column, 0, height, LABELS[column], column in (2, 3, 7))
        cell(4, 6, 0, half, "DIMENSIONES")
        cell(8, 12, 0, half, "METRADO")
        for column in (4, 5, 6, 8, 9, 10, 11, 12):
            cell(column, column, half, height, LABELS[column])
        painter.end()


class SheetDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        if index.column() == 2:
            editor = QComboBox(parent)
            editor.addItems(UNITS)
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
        painter.setPen(QPen(QColor(theme.BORDER), 1, Qt.DotLine))
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
