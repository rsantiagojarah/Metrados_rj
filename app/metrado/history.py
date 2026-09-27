"""Undo payloads hold affected rows, not full-project copies per cell edit."""
from copy import deepcopy
from weakref import proxy

from PySide6.QtGui import QUndoCommand


class RowEdit(QUndoCommand):
    def __init__(self, model, start, before, after, column, label):
        super().__init__(label)
        self.model, self.start, self.column = proxy(model), start, column
        self.before, self.after = before, after
        self.first = True

    def _apply(self, rows, select=True):
        self.model.rows[self.start:self.start + len(rows)] = deepcopy(rows)
        self.model.recalculate(self.start)
        if select:
            self.model.selectionRequested.emit(self.start, self.column)

    def redo(self):
        self._apply(self.after, not self.first)
        self.first = False

    def undo(self):
        self._apply(self.before)


class RowStructure(QUndoCommand):
    def __init__(self, model, rows, label, before_selection, after_selection):
        super().__init__(label)
        self.model = proxy(model)
        before = {r['id']: r for r in model.rows}
        after = {r['id']: r for r in rows}
        self.before_order, self.after_order = list(before), list(after)
        self.before = {k: deepcopy(v) for k, v in before.items() if after.get(k) != v}
        self.after = {k: deepcopy(v) for k, v in after.items() if before.get(k) != v}
        self.before_selection, self.after_selection = before_selection, after_selection

    def _apply(self, order, changes, selection):
        current = {r['id']: r for r in self.model.rows}
        current.update(deepcopy(changes))
        self.model._replace([current[identity] for identity in order])
        if selection is not None and self.model.rows:
            self.model.selectionRequested.emit(min(selection[0], len(order) - 1), selection[1])

    def redo(self):
        self._apply(self.after_order, self.after, self.after_selection)

    def undo(self):
        self._apply(self.before_order, self.before, self.before_selection)


class ProjectTitle(QUndoCommand):
    def __init__(self, window, before, after):
        super().__init__('nombre de la obra')
        self.window, self.before, self.after = proxy(window), before, after

    def _apply(self, value):
        self.window._committed_title = value
        self.window.title_edit.setText(value)

    def undo(self):
        self._apply(self.before)

    def redo(self):
        self._apply(self.after)
