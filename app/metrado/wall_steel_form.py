"""The eleven optional reinforcement positions in the reference wall."""
from PySide6.QtCore import Signal, Qt, QEvent
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QAbstractItemView
from metrado.numeric_edit import NumericEdit
from metrado.arithmetic import numeric_text
from metrado.steel_config import DIAMETERS
from metrado.wall_types import WALL_POSITIONS, positive


class DistributionTable(QTableWidget):
    changed = Signal()
    inputError = Signal(str)
    positionSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(len(WALL_POSITIONS), 4, parent)
        self.setHorizontalHeaderLabels(['Posición del acero', 'Diámetro', 'Sep. (m)', 'Corte (m)'])
        self.verticalHeader().hide()
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col, width in ((1, 80), (2, 72), (3, 76)):
            self.horizontalHeader().setSectionResizeMode(col, QHeaderView.Fixed)
            self.setColumnWidth(col, width)
        self.verticalHeader().setDefaultSectionSize(34)
        self.setMinimumHeight(410)
        self.setMinimumWidth(485)
        for r, (component, side, label) in enumerate(WALL_POSITIONS):
            self.setItem(r, 0, QTableWidgetItem(label))
            diameter = QComboBox()
            diameter.addItem('—', None)
            for value in DIAMETERS:
                diameter.addItem(value, value)
            spacing = NumericEdit(positive=True, allow_blank=True)
            spacing.setPlaceholderText('—')
            self.setCellWidget(r, 1, diameter)
            self.setCellWidget(r, 2, spacing)
            edits = [spacing]
            if component == 'refuerzo_cortado':
                fixed = NumericEdit(positive=True, allow_blank=True)
                fixed.setPlaceholderText('—')
                self.setCellWidget(r, 3, fixed)
                edits.append(fixed)
            else:
                label = QTableWidgetItem('—')
                label.setTextAlignment(Qt.AlignCenter)
                self.setItem(r, 3, label)
            diameter.currentIndexChanged.connect(self.changed)
            for edit in edits:
                edit.textChanged.connect(self.changed)
                edit.inputError.connect(self.inputError)
            for widget in (diameter, *edits):
                widget.installEventFilter(self)
        self.currentCellChanged.connect(self._select)
        self.setCurrentCell(0,0)

    def _select(self, row, column, previous_row, previous_column):
        if row >= 0:
            c,s,_ = WALL_POSITIONS[row]
            self.positionSelected.emit(c+':'+s)

    def select_position(self, key):
        for r,(c,s,_) in enumerate(WALL_POSITIONS):
            if c+':'+s == key:
                self.setCurrentCell(r,0)
                return

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.FocusIn,QEvent.MouseButtonPress):
            for r in range(self.rowCount()):
                for c in (1,2,3):
                    if self.cellWidget(r,c) is watched:
                        self.setCurrentCell(r,0)
                        return False
        return super().eventFilter(watched,event)

    def load(self, wall):
        self.blockSignals(True)
        self._extra = []
        by_position = {}
        for item in wall.distributions:
            key = (item['component'], item['side'])
            if key not in {(c, s) for c, s, _ in WALL_POSITIONS} or key in by_position:
                self._extra.append(item)
            else:
                by_position[key] = item
        if wall.cut_left and ('refuerzo_cortado', 'izquierda') not in by_position:
            by_position['refuerzo_cortado', 'izquierda'] = dict(diameter=wall.cut_diameter,
                spacing=wall.cut_spacing, fixed_length=wall.cut_length)
        for r, (component, side, label) in enumerate(WALL_POSITIONS):
            item = by_position.get((component, side))
            if component == 'refuerzo_cortado' and not wall.cut_left:
                item = None
            self.cellWidget(r, 1).setCurrentIndex(self.cellWidget(r, 1).findData(item['diameter'] if item else None))
            self.cellWidget(r, 2).setText(format(float(item['spacing']), '.12g') if item else '')
            value = (item.get('fixed_length') or wall.cut_length) if item and component == 'refuerzo_cortado' else None
            if self.cellWidget(r, 3):
                self.cellWidget(r, 3).setText(format(float(value), '.12g') if value is not None else '')
                self.cellWidget(r, 3).setToolTip('Cota del corte sobre la zapata en el tipo original. '
                    'El desarrollo incluye la penetración hasta el fondo de zapata; conserva '
                    'esa longitud al variar la altura del tramo. Ganchos aparte.')
            for col in (2, 3):
                if self.cellWidget(r, col):
                    self.cellWidget(r, col)._previous = self.cellWidget(r, col).text()
        self.blockSignals(False)

    def set_dentellon(self, enabled):
        for r, (component, _, _) in enumerate(WALL_POSITIONS):
            if component.startswith('dentellon'):
                self.item(r, 0).setFlags(Qt.ItemIsEnabled if enabled else Qt.NoItemFlags)
                for col in (1, 2):
                    self.cellWidget(r, col).setEnabled(enabled)

    def configuration(self, *, preview=False):
        result = []
        for r, (component, side, label) in enumerate(WALL_POSITIONS):
            dia = self.cellWidget(r, 1).currentData()
            spacing = self.cellWidget(r, 2).text().strip()
            fixed = self.cellWidget(r, 3).text().strip() if self.cellWidget(r, 3) else ''
            # An incomplete position is simply not included in the takeoff.
            if not dia or not spacing or (component == 'refuerzo_cortado' and not fixed):
                continue
            try:
                spacing = positive(numeric_text(spacing, positive=True), label)
                fixed = positive(numeric_text(fixed, positive=True), label) if component == 'refuerzo_cortado' else None
            except ValueError:
                if preview:
                    continue
                raise
            result.append(dict(component=component, side=side, diameter=dia,
                               spacing=spacing, fixed_length=fixed))
        return result
