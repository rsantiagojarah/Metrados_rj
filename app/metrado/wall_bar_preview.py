"""Selected bar development and editable independent hooks."""
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from metrado.arithmetic import numeric_text
from metrado.numeric_edit import NumericEdit
from metrado.wall_rebar import reinforcement, position_key


def _validate_hook(value):
    if not 0 <= float(value or 0) <= 1e6:
        raise ValueError('Los ganchos deben estar entre 0 y 1 000 000 m.')


class BarDevelopment(QWidget):
    def __init__(self):
        super().__init__()
        self.geometry = None
        self.setMinimumHeight(62)

    def paintEvent(self, event):
        if self.geometry is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pts = self.geometry.points
        if max(y for x,y in pts)-min(y for x,y in pts) > max(x for x,y in pts)-min(x for x,y in pts):
            pts = tuple((-y, x) for x,y in pts)
        xmin, xmax = min(x for x,y in pts), max(x for x,y in pts)
        ymin, ymax = min(y for x,y in pts), max(y for x,y in pts)
        scale = min((self.width()-64)/max(xmax-xmin,.01), 28/max(ymax-ymin,.01))
        ox = (self.width()-(xmax-xmin)*scale)/2
        def point(v):
            return QPointF(ox+(v[0]-xmin)*scale, 13+(ymax-v[1])*scale)
        p.setPen(QPen(QColor('#ffbf69'),2))
        for a,b in zip(pts,pts[1:]):
            p.drawLine(point(a),point(b))
        p.setPen(QColor('#dceaf3'))
        for label, index in [('G1',0), ('G2',-1)]:
            q=point(pts[index])
            p.drawText(QRectF(q.x()-15,q.y()-14,30,14),Qt.AlignCenter,label)
        p.drawText(QRectF(0,43,self.width(),18),Qt.AlignCenter,
                   f'Cuerpo {self.geometry.body_length:.3f} + ganchos '
                   f'{self.geometry.hook_start+self.geometry.hook_end:.3f} = {self.geometry.total_length:.3f} m')


class HookEditor(QWidget):
    changed = Signal(str, float, float)
    inputError = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.key = None
        self.geometry = None
        self._invalid = False
        root = QVBoxLayout(self)
        root.setContentsMargins(4,0,4,0)
        root.setSpacing(2)
        self.title = QLabel()
        self.title.setAlignment(Qt.AlignCenter)
        root.addWidget(self.title)
        self.bar = BarDevelopment()
        root.addWidget(self.bar)
        fields = QHBoxLayout()
        fields.setSpacing(5)
        self.start = NumericEdit(allow_blank=True,validate=_validate_hook)
        self.end = NumericEdit(allow_blank=True,validate=_validate_hook)
        for label, edit in [('G1 (m)',self.start),('G2 (m)',self.end)]:
            fields.addWidget(QLabel(label))
            edit.setMaximumWidth(80)
            edit.setFixedHeight(27)
            fields.addWidget(edit)
            edit.inputError.connect(self.inputError)
            edit.inputError.connect(self._invalid_input)
            edit.editingFinished.connect(self.commit)
        root.addLayout(fields)

    def load(self, wall, item, label):
        self.key = position_key(item) if item else None
        self.setEnabled(item is not None)
        self.title.setText(label if item else 'Selecciona una posición con acero')
        if item:
            self.geometry = reinforcement(wall,item)
            self.title.setToolTip('Barra por cada metro lineal de muro.' if not self.geometry.section else
                                  'G1: primer extremo del despiece. G2: segundo extremo. 0 = sin gancho.')
            for edit, value in ((self.start,self.geometry.hook_start),(self.end,self.geometry.hook_end)):
                if not edit.hasFocus():
                    edit.setText(f'{value:g}')
                    edit._previous = edit.text()
        else:
            self.geometry = None
            self.start.clear()
            self.end.clear()
        self.bar.geometry = self.geometry
        self.bar.update()

    def _invalid_input(self, message):
        self._invalid = True

    def commit(self):
        if self._invalid:
            self._invalid = False
            return
        if not self.key:
            return
        try:
            values = [float(numeric_text(edit.text(),allow_blank=True) or 0) for edit in (self.start,self.end)]
            if any(not 0 <= value <= 1e6 for value in values):
                raise ValueError('Los ganchos deben ser mayores o iguales a cero.')
        except ValueError as error:
            self.inputError.emit(str(error))
            return
        self.changed.emit(self.key,*values)
