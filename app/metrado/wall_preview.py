"""Lightweight vector section, redrawn from the current wall input."""
import math
from copy import deepcopy
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget
from metrado.wall_rebar import reinforcement, spaced_points, position_key
from metrado.wall_bar_preview import HookEditor
from metrado.wall_types import WALL_POSITIONS


class WallPreview(QWidget):
    positionSelected = Signal(str)
    hooksChanged = Signal(str, float, float)
    inputError = Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected = 'pantalla_vertical:izquierda'
        self._segments = []
        self.editor = HookEditor(self)
        self.editor.changed.connect(self.hooksChanged)
        self.editor.inputError.connect(self.inputError)
        self.editor.hide()
        self.wall = None
        self.steel = False
        self.pending = False
        self.setMinimumSize(330, 450)

    def set_wall(self, wall, steel=False, pending=False):
        self.wall = deepcopy(wall)
        self.steel = steel
        self.pending = pending
        self.editor.setVisible(steel)
        self._load_editor()
        self.update()

    def select_position(self, key):
        self.selected = key
        self._load_editor()
        self.update()

    def _load_editor(self):
        if not self.wall:
            return
        item = next((d for d in self.wall.distributions if position_key(d) == self.selected), None)
        if item and item['component'].startswith('dentellon') and not self.wall.dentellon:
            item = None
        label = next((label for c,s,label in WALL_POSITIONS if c+':'+s == self.selected), '')
        try:
            self.editor.load(self.wall, item, label)
        except ValueError:
            self.editor.load(self.wall, None, '')

    def resizeEvent(self, event):
        self.editor.setGeometry(8,self.height()-126,self.width()-16,124)
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        if not self.steel:
            return
        q = event.position()
        closest = None
        for key,a,b in self._segments:
            vx,vy = b.x()-a.x(),b.y()-a.y()
            denominator = vx*vx+vy*vy
            ratio = max(0,min(1,((q.x()-a.x())*vx+(q.y()-a.y())*vy)/denominator)) if denominator else 0
            distance = math.hypot(q.x()-a.x()-ratio*vx,q.y()-a.y()-ratio*vy)
            if distance < 10 and (closest is None or distance < closest[0]):
                closest = (distance,key)
        if closest:
            self.positionSelected.emit(closest[1])
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor('#111b25'))
        p.setPen(QColor('#dae5ef'))
        p.drawText(QRectF(12, 10, self.width()-24, 24), Qt.AlignCenter, 'SECCIÓN DEL MURO')
        if self.wall is None:
            p.drawText(self.rect(), Qt.AlignCenter, 'Ingresa las dimensiones para ver el muro')
            return
        w = self.wall
        h, t, b = w.screen_height, w.top_thickness, w.bottom_thickness
        left, right, base = w.footing_left, w.footing_right, w.footing_thickness
        width = left + b + right
        depth = w.dentellon_depth if w.dentellon else 0
        total = h + base + depth
        scale = min((self.width()-108) / width, (self.height()-(256 if self.steel else 160)) / total)
        ox = (self.width()-width*scale)/2
        oy = 62 + h*scale
        def point(x, y):
            return QPointF(ox + x*scale, oy-y*scale)
        def line(a, z, color='#d6e5ef', size=1):
            p.setPen(QPen(QColor(color), size))
            p.drawLine(a, z)
        def shape(coords):
            p.setPen(QPen(QColor('#96b3c7'), 1.5))
            p.setBrush(QColor('#263c4d'))
            p.drawPolygon(QPolygonF([point(x, y) for x, y in coords]))
        shape([(left,0),(left+b-t,h),(left+b,h),(left+b,0)])
        shape([(0,0),(width,0),(width,-base),(0,-base)])
        if w.dentellon:
            kr = left+b
            kl = kr-w.dentellon_width
            shape([(kl-w.dentellon_slope,-base),(kr,-base),
                   (kr,-base-depth),(kl,-base-depth)])
        p.setPen(QColor('#90a7b9'))
        p.drawText(QRectF(10, 38, self.width()/2-10, 20), Qt.AlignLeft, 'IZQUIERDA · RELLENO')
        p.drawText(QRectF(self.width()/2,38,self.width()/2-12,20), Qt.AlignRight, 'DERECHA')
        def horizontal(x1, x2, y, text, offset):
            a, z = point(x1,y), point(x2,y)
            ay = a.y()+offset
            for q in (a,z):
                line(q,QPointF(q.x(),ay+4),'#718798')
                line(QPointF(q.x()-3,ay+3),QPointF(q.x()+3,ay-3),'#acbdc9')
            line(QPointF(a.x(),ay),QPointF(z.x(),ay),'#718798')
            p.setPen(QColor('#d6e5ef'))
            p.drawText(QRectF((a.x()+z.x())/2-55,ay-20,110,18),Qt.AlignCenter,text)
        def vertical(x,y1,y2,text,offset):
            a,z=point(x,y1),point(x,y2)
            ax=a.x()+offset
            line(a,QPointF(ax+4,a.y()),'#718798')
            line(z,QPointF(ax+4,z.y()),'#718798')
            line(QPointF(ax,a.y()),QPointF(ax,z.y()),'#718798')
            p.save()
            p.translate(ax-5,(a.y()+z.y())/2)
            p.rotate(-90)
            p.setPen(QColor('#d6e5ef'))
            p.drawText(QRectF(-55,-18,110,18),Qt.AlignCenter,text)
            p.restore()
        if not self.steel:
            horizontal(left+b-t,left+b,h,f'{t:g} m',-14)
            horizontal(0,left,0,f'{left:g} m',-18)
            horizontal(left+b,width,0,f'{right:g} m',-18)
            horizontal(left,left+b,0,f'{b:g} m',22)
            vertical(left+b,0,h,f'H = {h:g} m',45)
            vertical(0,-base,0,f'{base:g} m',-25)
            if w.dentellon:
                horizontal(left+b-w.dentellon_width,left+b,-base-depth,f'{w.dentellon_width:g} m',30)
                vertical(left+b,-base-depth,-base,f'{depth:g} m',30)
                if w.dentellon_slope:
                    p.setPen(QColor('#90a7b9'))
                    p.drawText(QRectF(8,self.height()-58,self.width()-16,18),Qt.AlignCenter,
                               f'Vuelo inclinado del dentellón: {w.dentellon_slope:g} m')
        else:
            self._segments = []
            def callout(item, anchor, y, left_side, color):
                x=10 if left_side else self.width()-138
                label=f'Ø{item["diameter"]} @ {item["spacing"]:g}'
                p.setPen(QColor(color))
                p.drawText(QRectF(x,y-18,128,18),Qt.AlignLeft if left_side else Qt.AlignRight,label)
                end=QPointF(x+125 if left_side else x+4,y)
                line(anchor,end,color,.8)
            entries = sorted(w.distributions, key=lambda d: position_key(d) == self.selected)
            for entry in entries:
                component, side = entry['component'], entry['side']
                if component.startswith('dentellon') and not w.dentellon:
                    continue
                if component == 'refuerzo_cortado' and not w.cut_left:
                    continue
                try:
                    geometry = reinforcement(w,entry)
                except ValueError:
                    continue
                key = position_key(entry)
                color = ('#e98dad' if component == 'refuerzo_cortado' else
                         '#81d8a5' if component.startswith('dentellon') else
                         '#64d9ee' if component.startswith('zapata') else '#ffbf69')
                chosen = key == self.selected
                if geometry.section:
                    pen = QPen(QColor('#ffffff' if chosen else color), 2.6 if chosen else 1.7)
                    if component == 'refuerzo_cortado':
                        pen.setStyle(Qt.DashLine)
                    p.setPen(pen)
                    for a,z in zip(geometry.points,geometry.points[1:]):
                        pa,pz=point(*a),point(*z)
                        p.drawLine(pa,pz)
                        self._segments.append((key,pa,pz))
                else:
                    p.setPen(Qt.NoPen)
                    p.setBrush(QColor('#ffffff' if chosen else color))
                    for x,y in spaced_points(geometry.distribution,float(entry['spacing']),limit=90):
                        q=point(x,y)
                        p.drawEllipse(q,2.4 if chosen else 2,2.4 if chosen else 2)
                        self._segments.append((key,q,q))
                if component.startswith('pantalla'):
                    factor=.38 if geometry.section else .16
                    path=geometry.body if geometry.section else geometry.distribution
                    x=path[0][0]+(path[-1][0]-path[0][0])*factor
                    y=path[0][1]+(path[-1][1]-path[0][1])*factor
                    callout(entry,point(x,y),62+h*scale*factor,side=='izquierda',color)
                elif component == 'refuerzo_cortado':
                    callout(entry,point(*geometry.body[0]),62+h*scale*.62,True,color)
                elif component.startswith('zapata'):
                    y=0 if side=='superior' else -base
                    callout(entry,point(width*(.22 if geometry.section else .78),y),
                            oy-12 if side=='superior' else oy+base*scale+24,geometry.section,color)
                else:
                    anchor=geometry.body[1] if geometry.section else geometry.distribution[-2]
                    callout(entry,point(*anchor),oy+(base+depth)*scale+43,geometry.section,color)
        p.setPen(QColor('#90a7b9'))
        footer='Vista anterior: completa las dimensiones' if self.pending else ('Sin recubrimientos · ganchos en metros' if self.steel else f'Ancho total de zapata: {width:g} m')
        p.drawText(QRectF(8,self.height()-(149 if self.steel else 28),self.width()-16,20),Qt.AlignCenter,footer)
        p.end()
