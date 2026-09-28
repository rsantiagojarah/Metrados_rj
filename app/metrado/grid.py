"""Editable desktop grid with the reference sheet's two-level header."""
from copy import deepcopy
from uuid import uuid4

from PySide6.QtCore import QAbstractTableModel, QEvent, QItemSelection, QItemSelectionModel, QModelIndex, QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QUndoStack
from PySide6.QtWidgets import QApplication, QAbstractItemDelegate, QComboBox, QHeaderView, QStyleOptionViewItem, QStyledItemDelegate, QTableView

from metrado.sheet import DIMENSIONS, UNITS, calculate, _calculate_plain
from metrado.steel import (
    DIAMETERS, STEEL_LABELS, description_base, edit_description, header_mode,
    set_bar_diameter, sync_description,
)
from metrado import theme
from metrado.hierarchy import Outline
from metrado.identity import ensure_ids
from metrado.history import RowEdit, RowStructure
from metrado import steel_config as sc
from metrado import references as refs
from metrado.steel_snapshot import freeze_rows, editable_copy
from metrado.swelling import adjusted_volume, factor_text, validate_swelling, volume_blocks, upgrade_legacy

LABELS = ("ÍTEM", "DESCRIPCIÓN", "Und", "Elem.\nsimil.", "Largo", "Ancho", "Alto",
          "N.º de\nveces", "Lon.", "Área", "Vol.", "Kg.", "Und.", "Total")
REFERENCE_LABELS = (*LABELS[:4], 'Valor ref.', '', '', *LABELS[7:])
CONVERSION_LABELS = (*LABELS[:4], 'Valor ref.', 'Factor', '', *LABELS[7:])


def labels_for_mode(mode):
    return {'reference': REFERENCE_LABELS, 'conversion': CONVERSION_LABELS,
            'steel': STEEL_LABELS}.get(mode, LABELS)


WIDTHS = (88, 490, 44, 48, 66, 66, 66, 48, 64, 64, 64, 64, 64, 88)
ROW_HEIGHT = 28
FOOTER_HEIGHT = 28


DISPLAY_ROLE = int(Qt.DisplayRole)
EDIT_ROLE = int(Qt.EditRole)
ALIGNMENT_ROLE = int(Qt.TextAlignmentRole)
FONT_ROLE = int(Qt.FontRole)
FOREGROUND_ROLE = int(Qt.ForegroundRole)
BACKGROUND_ROLE = int(Qt.BackgroundRole)
DATA_ROLES = frozenset((DISPLAY_ROLE, EDIT_ROLE, ALIGNMENT_ROLE, FONT_ROLE,
                        FOREGROUND_ROLE, BACKGROUND_ROLE))
READ_FLAGS = Qt.ItemIsSelectable | Qt.ItemIsEnabled
EDIT_FLAGS = READ_FLAGS | Qt.ItemIsEditable


class SheetModel(QAbstractTableModel):
    changed = Signal()
    selectionRequested = Signal(int, int)
    footersChanged = Signal()

    def __init__(self, engine, rows):
        super().__init__()
        ensure_ids(rows)
        upgrade_legacy(rows)
        freeze_rows(rows)
        for row in rows:
            sc.sync_dimensions(row)
            sync_description(row, engine)
        self.steel_defaults = None
        self.undo_stack = QUndoStack(self)
        self.undo_stack.setUndoLimit(200)
        self.engine, self.rows = engine, rows
        self.local_row_numbers = False
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
        self._reference_sources = {r['id']: r for r in self.rows if r['kind'] == 'item'}
        self._dependencies = refs.DependencyIndex(self.rows)
        self.outline = Outline(self.rows)
        self._owners, self._ends = [], {}
        self._items = self._details = 0
        owner = None
        for index, row in enumerate(self.rows):
            kind = row["kind"]
            if kind not in ('detail', 'detail_group'):
                if owner is not None:
                    self._ends[owner] = index
                owner = index if kind == "item" else None
            self._owners.append(owner)
            self._items += kind == "item"
            self._details += kind == "detail"
        if owner is not None:
            self._ends[owner] = len(self.rows)
        self.swelling_footers = {end: start for start, end in volume_blocks(self.rows)}
        self._swelling_ends = {start: end for end, start in self.swelling_footers.items()}

    def swelling_owner(self, row):
        return row if (0 <= row < len(self.rows) and self.rows[row]['kind'] == 'detail'
                       and self.rows[row]['cells'][2] == 'm3') else None

    def swelling_base(self, start, end=None):
        end = self._swelling_ends.get(start, start) if end is None else end
        try:
            return self.engine.ask_sheet_total([self.values[(i, 10)] for i in range(start, end + 1)])
        except (KeyError, ValueError, OverflowError):
            return None

    def swelling_selection(self, selected):
        indexes = sorted(set(selected))
        if (not indexes or indexes != list(range(indexes[0], indexes[-1] + 1)) or
                any(self.swelling_owner(i) is None for i in indexes) or
                self._owners[indexes[0]] != self._owners[indexes[-1]]):
            raise ValueError('Selecciona uno o varios detalles consecutivos de una misma partida m³, sin títulos intermedios.')
        return indexes[0], indexes[-1]

    def swelling_bounds(self, row):
        for end, start in self.swelling_footers.items():
            if start <= row <= end:
                return start, end
        return row, row

    def swelling_summary(self, owner):
        config = self.rows[owner]['volume_factor']
        cells = [''] * 14
        cells[8] = 'FE'
        cells[9] = factor_text(config)
        total = self.values.get((self._swelling_ends[owner], 14))
        cells[10] = 'Pendiente' if total is None else f'{total:.2f}'
        return cells

    def set_swelling(self, selected, config):
        start, end = self.swelling_selection(selected)
        before = deepcopy(self.rows[start:end + 1])
        after = deepcopy(before)
        if config is None:
            for row in after:
                row.pop('volume_factor', None)
        else:
            if not isinstance(config, dict) or set(config) != {'factor', 'note'}:
                raise ValueError('Configuración de FE inválida.')
            # Re-editing unchanged settings is a no-op; joining/replacing blocks
            # is explicit and creates an independent identity.
            old = before[0].get('volume_factor')
            same = old and all(row.get('volume_factor') == old for row in before)
            if same and config == {key: old[key] for key in ('factor', 'note')}:
                return
            value = dict(config, block=uuid4().hex)
            for row in after:
                row['volume_factor'] = dict(value)
                validate_swelling(row)
            base = self.swelling_base(start, end)
            if base is not None:
                adjusted_volume(base, config, self.engine)
        if before != after:
            self.undo_stack.push(RowEdit(self, start, before, after, 1, 'factor de esponjamiento'))

    def _refresh_summary(self):
        self.summary_text = f"{self._items} partidas · {self._details} detalles · {self._pending} detalles pendientes"

    def selection_mode(self, row):
        if row < 0 or row >= len(self.rows):
            return "standard"
        if 'reference' in self.rows[row]:
            ref = self.rows[row]['reference']
            source = self._reference_sources.get(ref['source'])
            unit = source['cells'][2] if source else ref['source_unit']
            return 'reference' if unit == self.rows[row]['cells'][2] else 'conversion'
        owner = self._owners[row]
        return "steel" if owner is not None and self.rows[owner]["cells"][2] == "kg" else "standard"

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else 14

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.TextAlignmentRole and orientation == Qt.Vertical and section in self.swelling_footers:
            return int(Qt.AlignHCenter | Qt.AlignTop)
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return getattr(self, "header_labels", LABELS)[section]
            if self.local_row_numbers:
                owner = self._owners[section]
                return str(section - owner) if owner is not None and section > owner else ''
            return str(section + 1)

    def editable(self, row, column):
        kind = self.rows[row]["kind"]
        if kind == 'detail_group':
            return column == 1
        if kind == "chapter":
            return column in (0, 1)
        if kind == "item":
            return column in (0, 1, 2)
        if 'reference' in self.rows[row]:
            return column in (1, 3, 7)
        unit = self.rows[row]["cells"][2]
        if unit == "kg":
            if 'steel_hooks' in self.rows[row] and column in (5, 6):
                return False
            return column in (1, 3, 4, 5, 6, 7, 9)
        return (column in (1, 3, 7) or
                (unit == 'm3' and column == 9) or
                column in [c for c, _ in DIMENSIONS.get(unit, ())])

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
        if 'reference' in row:
            return self.reference_data(r, c, role)
        steel = kind == "detail" and row["cells"][2] == "kg"
        if kind == 'detail_group' and c != 1:
            return ''
        if steel:
            if c == 9:
                return row["cells"][7]
            if c == 7:
                times = self.values.get((r, 7))
                if getattr(self, '_batching', False):
                    if row['direct']:
                        return row['cells'][9]
                    try:
                        times = self.engine.ask_sheet_quantity('und', [],
                            float(row['cells'][10].replace(',', '.')),
                            float(row['cells'][9].replace(',', '.') or '1'), None)
                    except (ValueError, OverflowError):
                        times = None
                if times is None:
                    return row["cells"][9] if row["direct"] else row["cells"][10]
                return f"{times:g}"
        if role == EDIT_ROLE:
            if kind == 'detail' and row['cells'][2] == 'm3' and c == 9:
                return row['cells'][9]
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
        if c == 1:
            return "   " * self.outline.levels[r] + row["cells"][c]
        return row["cells"][c]

    def reference_data(self, r, c, role):
        row = self.rows[r]
        ref = row['reference']
        source = self._reference_sources.get(ref['source'])
        source_unit = source['cells'][2] if source else ref['source_unit']
        label = refs.description(row, self._reference_sources)
        if c == 1:
            return label if role == EDIT_ROLE else '   ' * self.outline.levels[r] + label
        if c in (0, 2, 3, 7):
            return row['cells'][c]
        if c == 4:
            value = self.values.get((r, 4))
            return 'Pendiente' if value is None else f'{value:.2f}'
        if c == 5:
            if source_unit == row['cells'][2]:
                return ''
            return ref['factor'] or 'Pendiente'
        result = {'m': 8, 'm2': 9, 'm3': 10, 'kg': 11}.get(row['cells'][2], 12)
        if c == result:
            value = self.values.get((r, 12 if row['cells'][2] == 'kg' else c))
            return 'Pendiente' if value is None else f'{value:.2f}'
        return ''

    def set_reference(self, index, source_id, name='', factor=''):
        source = next((row for row in self.rows if row['kind'] == 'item' and row['id'] == source_id), None)
        if source is None:
            raise ValueError('La partida de origen no está disponible.')
        rows = deepcopy(self.rows)
        row = rows[index]
        if row['kind'] != 'detail':
            raise ValueError('Selecciona una fila de detalle para referenciar.')
        was_reference = 'reference' in row
        times = row['cells'][7] if was_reference or row['cells'][2] != 'kg' else '1'
        row['reference'] = refs.make_reference(source, row['cells'][2], name, factor)
        row['direct'] = ''
        row.pop('steel_catalog', None)
        row.pop('steel_hooks', None)
        row['cells'][1] = source['cells'][1]
        row['cells'][4:] = [''] * 10
        row['cells'][7] = times or '1'
        refs.validate_row(row)
        self.replace(rows, 'referencia de partida', (index, 1), (index, 1))

    def setData(self, index, value, role=Qt.EditRole):
        if getattr(self, '_batching', False):
            changed = self._set_data(index, value, role)
            if changed:
                self._sync_descriptions(index)
            return changed
        if role != Qt.EditRole or not index.isValid() or not self.editable(index.row(), index.column()):
            return False
        r, c = index.row(), index.column()
        end = self._ends.get(r, r + 1) if c == 2 else r + 1
        before = deepcopy(self.rows[r:end])
        self._batching = True
        try:
            changed = self._set_data(index, value, role)
            if changed:
                self._sync_descriptions(index)
            after = deepcopy(self.rows[r:end]) if changed else None
            changed = changed and before != after
        finally:
            self.rows[r:end] = before
            self._batching = False
        if changed:
            label = 'cambio de unidad' if c == 2 else 'edición de celda'
            self.undo_stack.push(RowEdit(self, r, before, after, c, label))
        return changed

    def _sync_descriptions(self, index):
        start = index.row()
        end = self._ends.get(start, start + 1) if index.column() == 2 else start + 1
        freeze_rows(self.rows[start:end])
        for row in self.rows[start:end]:
            sc.sync_dimensions(row)
            sync_description(row, self.engine)

    def _set_data(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid() or not self.editable(index.row(), index.column()):
            return False
        r, c = index.row(), index.column()
        value = str(value).strip()
        if c == 2 and value not in UNITS:
            return False
        row = self.rows[r]
        if 'reference' in row:
            if c not in (3, 7) or row['cells'][c] == value:
                return False
            row['cells'][c] = value
            self.recalculate(r)
            return True
        if row['kind'] == 'detail' and row['cells'][2] == 'kg' and c == 1:
            if value == row['cells'][1]:
                return False
            edit_description(row, value)
            self.recalculate(r)
            return True
        if row["kind"] == "detail" and row["cells"][2] == "kg" and c == 9:
            if 'steel_hooks' in row and value not in row['steel_catalog']:
                return False
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
        if row['kind'] == 'detail' and row['cells'][2] == 'm3' and c == 9:
            if value == row['cells'][9]:
                return False
            if value:
                try:
                    area = float(value.replace(',', '.'))
                    self.engine.ask_sheet_quantity('m2', [], 1.0, 1.0, area)
                except (ValueError, OverflowError):
                    return False
            row['cells'][9] = value
            row['direct'] = ''
            self.recalculate(r)
            return True
        if self.rows[r]["cells"][c] == value and not (c in (4, 5, 6) and self.rows[r]["direct"]):
            return False
        self.rows[r]["cells"][c] = value
        if c == 2 and value != 'm3':
            self.rows[r].pop('swelling', None)
        if c in (4, 5, 6, 7, 9, 10):
            self.rows[r]["direct"] = ""
        if c == 2:
            row.pop('steel_catalog', None)
            if value == 'kg' and self.steel_defaults is not None:
                sc.adopt(row, self.steel_defaults)
            for child in self.rows[r + 1:]:
                if child["kind"] not in ('detail', 'detail_group'):
                    break
                if child['kind'] == 'detail' and child['cells'][2] == 'kg' and value != 'kg':
                    child['cells'][1] = description_base(child['cells'][1])
                child["cells"][2] = value
                child.pop('steel_catalog', None)
                child.pop('steel_hooks', None)
                if value != 'm3':
                    child.pop('volume_factor', None)
                if child['kind'] == 'detail_group' or 'reference' in child:
                    continue
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
                if value == 'kg' and self.steel_defaults is not None:
                    sc.adopt(child, row['steel_catalog'])
        self.recalculate(r)
        return True

    def recalculate(self, row=None):
        if getattr(self, '_batching', False):
            return
        footer_changed = False
        if row is None or self._dependencies.blocked:
            previous_footers = self.swelling_footers
            self.values, self.errors = calculate(self.rows, self.engine)
            self._rebuild_structure()
            footer_changed = previous_footers != self.swelling_footers
            self._pending = sum(self.rows[r]["kind"] == "detail" for r in self.errors)
            start, end = 0, len(self.rows)
        else:
            owner = self._owners[row]
            if owner is not None and self._dependencies.has_links:
                self._recalculate_dependents(owner)
                return
            start = row if owner is None else owner
            end = row + 1 if owner is None else self._ends[owner]
            before = sum(r in self.errors and self.rows[r]["kind"] == "detail"
                         for r in range(start, end))
            values, errors = calculate(self.rows[start:end], self.engine)
            for r in range(start, end):
                self.errors.pop(r, None)
                for column in range(15):
                    self.values.pop((r, column), None)
            self.values.update(((r + start, c), value) for (r, c), value in values.items())
            self.errors.update((r + start, error) for r, error in errors.items())
            after = sum(self.rows[start + r]["kind"] == "detail" for r in errors)
            self._pending += after - before
            if owner is not None:
                previous = {e: s for e, s in self.swelling_footers.items() if start <= e < end}
                current = {e + start: s + start for s, e in volume_blocks(self.rows[start:end])}
                for e, s in previous.items():
                    self.swelling_footers.pop(e)
                    self._swelling_ends.pop(s)
                self.swelling_footers.update(current)
                self._swelling_ends.update({s: e for e, s in current.items()})
                footer_changed = previous != current
        self._refresh_summary()
        if footer_changed:
            self.footersChanged.emit()
        if end > start:
            self.dataChanged.emit(self.index(start, 0), self.index(end - 1, 13))
        self.changed.emit()

    def _recalculate_dependents(self, owner):
        """Row edits cannot change the graph; structural edits rebuild it once."""
        affected = self._dependencies.affected(owner)
        sources = {identity: (self.rows[i]['cells'][2], self.values.get((i, 13)))
                   for identity, i in self._dependencies.items.items()}
        footer_changed = False
        for start in affected:
            end = self._ends[start]
            before = sum(r in self.errors and self.rows[r]['kind'] == 'detail' for r in range(start, end))
            values, errors = _calculate_plain(self.rows[start:end], self.engine, sources)
            for r in range(start, end):
                self.errors.pop(r, None)
                for c in range(15):
                    self.values.pop((r, c), None)
            self.values.update(((r + start, c), value) for (r, c), value in values.items())
            self.errors.update((r + start, error) for r, error in errors.items())
            self._pending += sum(self.rows[start + r]['kind'] == 'detail' for r in errors) - before
            item = self.rows[start]
            sources[item['id']] = (item['cells'][2], values.get((0, 13)))
            self._reference_sources[item['id']] = item
            previous = {e: s for e, s in self.swelling_footers.items() if start <= e < end}
            current = {e + start: s + start for s, e in volume_blocks(self.rows[start:end])}
            for e, s in previous.items():
                self.swelling_footers.pop(e)
                self._swelling_ends.pop(s)
            self.swelling_footers.update(current)
            self._swelling_ends.update({s: e for e, s in current.items()})
            footer_changed |= previous != current
        self._refresh_summary()
        if footer_changed:
            self.footersChanged.emit()
        for start in affected:
            self.dataChanged.emit(self.index(start, 0), self.index(self._ends[start] - 1, 13))
        self.changed.emit()

    def paste_cells(self, start_row, start_column, matrix):
        """Validate on a private copy, then calculate and publish once."""
        if not matrix:
            return False
        if start_row < 0 or start_column < 0 or start_row + len(matrix) > len(self.rows) or start_column + len(matrix[0]) > 14:
            raise ValueError('El bloque no cabe. Agrega primero las filas necesarias.')
        return self.paste_mapped_cells(
            [(start_row + dr, start_column + dc, value) for dr, cells in enumerate(matrix) for dc, value in enumerate(cells)],
            (start_row, start_column))

    def paste_mapped_cells(self, targets, selection):
        """Same atomic edit path for visible tree cells and sheet rectangles."""
        staged = SheetModel(self.engine, deepcopy(self.rows))
        staged.steel_defaults = self.steel_defaults
        staged._batching = True
        changed = editable = False
        for r, c, value in targets:
            if not 0 <= r < len(self.rows) or not 0 <= c < 14:
                raise ValueError('El bloque no cabe. Agrega primero las filas necesarias.')
            if not staged.editable(r, c):
                continue
            editable = True
            index = staged.index(r, c)
            if str(staged.data(index, Qt.EditRole) or '') == value.strip():
                continue
            if not staged.setData(index, value):
                raise ValueError(f'Valor no admitido en la fila {r + 1}, columna {c + 1}. No se pegó ningún dato.')
            changed = True
        if not editable:
            raise ValueError('Selecciona celdas editables; los resultados se calculan automáticamente.')
        if changed:
            self.replace(staged.rows, 'pegado de celdas', selection, selection)
        return changed

    def replace(self, rows, label=None, before_selection=None, after_selection=None):
        ensure_ids(rows)
        refs.check_cycles(rows)
        upgrade_legacy(rows)
        freeze_rows(rows)
        for row in rows:
            sc.sync_dimensions(row)
            sync_description(row, self.engine)
        if label is not None:
            if rows != self.rows:
                self.undo_stack.push(RowStructure(self, rows, label, before_selection, after_selection))
            return
        self.undo_stack.clear()
        self._replace(rows)

    def _replace(self, rows):
        upgrade_legacy(rows)
        freeze_rows(rows)
        self.beginResetModel()
        self.rows = rows
        self.values, self.errors = calculate(rows, self.engine)
        self._rebuild_structure()
        self._pending = sum(self.rows[r]["kind"] == "detail" for r in self.errors)
        self._refresh_summary()
        self.endResetModel()
        self.changed.emit()

    def steel_catalog_for(self, index):
        row = self.rows[index]
        owner = self._owners[index]
        return editable_copy(row.get('steel_catalog') or
                        (self.rows[owner].get('steel_catalog') if owner is not None else None) or
                        self.steel_defaults or sc.initial_catalog())

    def apply_steel_hooks(self, selected, count, override=None):
        indexes = sc.selected_details(self.rows, selected)
        if type(count) is not int or count not in (1, 2):
            raise ValueError('Elige 1 o 2 ganchos.')
        if override is not None:
            sc.number(override)
        rows = deepcopy(self.rows)
        for i in indexes:
            row = rows[i]
            catalog = self.steel_catalog_for(i)
            owner = self._owners[i]
            if owner is not None and 'steel_catalog' not in rows[owner]:
                sc.adopt(rows[owner], catalog)
            sc.adopt(row, catalog)
            row['steel_hooks'] = dict(count=count, override=override)
            sc.sync_dimensions(row)
        self.replace(rows, 'aplicación de ganchos', (indexes[0], 1), (indexes[0], 1))

    def update_steel_catalog(self, catalog):
        sc.validate_catalog(catalog)
        rows = deepcopy(self.rows)
        for row in rows:
            if row['kind'] in ('item', 'detail') and row['cells'][2] == 'kg':
                sc.adopt(row, catalog, preserve_hooks=True)
        self.replace(rows, 'actualización de aceros de la obra')

    def set_direct(self, index, value):
        if self.rows[index]["kind"] != "detail" or 'reference' in self.rows[index]:
            return
        before = deepcopy(self.rows[index:index + 1])
        after = deepcopy(before)
        after[0]['direct'] = value
        after[0]['cells'][4:7] = [''] * 3
        if after[0]['cells'][2] == 'm3':
            after[0]['cells'][9] = ''
        sync_description(after[0], self.engine)
        if before != after:
            self.undo_stack.push(RowEdit(self, index, before, after, 4, 'cantidad directa'))


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
        labels = labels_for_mode(self.mode)

        def cell(first, last, top, bottom, text, rotate=False):
            visible = [i for i in range(first, last + 1) if not self.isSectionHidden(i)]
            if not visible:
                return
            x = self.sectionViewportPosition(visible[0])
            width = sum(self.sectionSize(i) for i in visible)
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
        cell(4, 6, 0, half, "REFERENCIA" if self.mode in ('reference', 'conversion') else "DIMENSIONES")
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
        editor = super().createEditor(parent, option, index)
        if index.column() == 1 and row['kind'] == 'detail':
            editor.setProperty('reference_row', index.row())
        return editor

    def eventFilter(self, editor, event):
        row = editor.property('reference_row')
        if (row is not None and event.type() == QEvent.KeyPress and event.text() == '/'
                and (editor.cursorPosition() == 0 or editor.hasSelectedText())):
            self.closeEditor.emit(editor, QAbstractItemDelegate.RevertModelCache)
            self.parent().referenceRequested.emit(row)
            return True
        return super().eventFilter(editor, event)

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

    def _body_option(self, option, index):
        # The footer is a visual band below the last real row, not a data node.
        # Domain indexes, clipboard blocks and hierarchy operations stay stable.
        body = QStyleOptionViewItem(option)
        if index.row() in index.model().swelling_footers:
            body.rect.setHeight(max(ROW_HEIGHT, body.rect.height() - FOOTER_HEIGHT))
        return body

    def updateEditorGeometry(self, editor, option, index):
        super().updateEditorGeometry(editor, self._body_option(option, index), index)

    def paint(self, painter, option, index):
        body = self._body_option(option, index)
        super().paint(painter, body, index)
        painter.save()
        painter.setPen(self._grid_pen)
        painter.drawLine(body.rect.bottomLeft(), body.rect.bottomRight())
        painter.drawLine(option.rect.topRight(), option.rect.bottomRight())
        owner = index.model().swelling_footers.get(index.row())
        if owner is not None:
            footer = QRect(option.rect.x(), body.rect.bottom() + 1, option.rect.width(), FOOTER_HEIGHT)
            painter.fillRect(footer, QColor(theme.SURFACE))
            if index.column() == 10:
                painter.setPen(QColor(theme.DETAIL))
                painter.drawLine(footer.topLeft(), footer.topRight())
            painter.setPen(self._grid_pen)
            painter.drawLine(footer.bottomLeft(), footer.bottomRight())
            painter.drawLine(footer.topRight(), footer.bottomRight())
            text = index.model().swelling_summary(owner)[index.column()]
            font = QFont('Consolas')
            font.setPixelSize(11)
            font.setWeight(QFont.DemiBold)
            painter.setFont(font)
            painter.setPen(QColor(theme.DETAIL))
            alignment = Qt.AlignCenter if index.column() == 8 else Qt.AlignRight | Qt.AlignVCenter
            painter.drawText(footer.adjusted(3, 0, -3, 0), alignment,
                             painter.fontMetrics().elidedText(text, Qt.ElideRight, footer.width() - 6))
        painter.restore()


class SheetView(QTableView):
    focusEntered = Signal()
    referenceRequested = Signal(int)

    def selected_row_numbers(self):
        """Read selection ranges, never instantiate one QModelIndex per cell."""
        rows = set()
        for selected in self.selectionModel().selection():
            rows.update(r for r in range(selected.top(), selected.bottom() + 1)
                        if not self.isRowHidden(r))
        return rows

    def selection_has_full_row(self):
        coverage = {}
        complete = (1 << self.model().columnCount()) - 1
        for selected in self.selectionModel().selection():
            mask = ((1 << selected.width()) - 1) << selected.left()
            for row in range(selected.top(), selected.bottom() + 1):
                if not self.isRowHidden(row):
                    coverage[row] = coverage.get(row, 0) | mask
                    if coverage[row] == complete:
                        return True
        return False

    def selectAll(self):
        selection = QItemSelection()
        start = None
        for row in range(self.model().rowCount() + 1):
            visible = row < self.model().rowCount() and not self.isRowHidden(row)
            if visible and start is None:
                start = row
            elif not visible and start is not None:
                selection.select(self.model().index(start, 0), self.model().index(row - 1, 13))
                start = None
        self.selectionModel().select(selection, QItemSelectionModel.ClearAndSelect)

    def setCurrentIndex(self, index):
        # Navigation/history chooses one cell even while Ctrl/Shift from its
        # shortcut is still pressed. Mouse/keyboard range selection stays native.
        self.selectionModel().setCurrentIndex(index, QItemSelectionModel.ClearAndSelect)

    def focusInEvent(self, event):
        self.focusEntered.emit()
        super().focusInEvent(event)

    def commit_editor(self):
        """Include an in-progress cell edit in Save, Close and structural actions."""
        editor = QApplication.focusWidget()
        if self.state() != QTableView.EditingState or editor is None:
            return
        while editor is not None and editor.parentWidget() is not self.viewport():
            editor = editor.parentWidget()
        if editor is not None:
            self.commitData(editor)
            self.closeEditor(editor, QAbstractItemDelegate.NoHint)

    levelRequested = Signal(bool)
    clipboardRequested = Signal(str)
    swellingRequested = Signal(int)
    def __init__(self, model):
        super().__init__()
        self._compact = False
        self._fit_width = None
        self.setModel(model)
        self.setHorizontalHeader(GroupedHeader(self))
        self.setItemDelegate(SheetDelegate(self))
        self.setShowGrid(False)
        self.setAlternatingRowColors(False)
        self.setWordWrap(False)
        self.setSelectionMode(QTableView.ExtendedSelection)
        self.setEditTriggers(QTableView.DoubleClicked | QTableView.EditKeyPressed | QTableView.AnyKeyPressed)
        self.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        self.verticalHeader().setMinimumSectionSize(24)
        self.verticalHeader().setFixedWidth(34)
        for column, width in enumerate(WIDTHS):
            self.setColumnWidth(column, width)
        self.selectionModel().currentChanged.connect(self.sync_header)
        self.model().modelReset.connect(lambda: self.sync_header(self.currentIndex()))
        self.model().changed.connect(lambda: self.sync_header(self.currentIndex()))
        self._footer_rows = set()
        self.verticalHeader().sectionResized.connect(self._keep_footer_height)
        self.model().modelReset.connect(self.sync_footers)
        self.model().footersChanged.connect(self.sync_footers)
        self.sync_footers()
        self.sync_header(self.currentIndex())

    def enable_compact_layout(self):
        """Keep model indexes intact; fit only when the viewport width changes."""
        self._compact = True
        # Reserve the scrollbar even for short partidas: selection must not
        # change available width and consequently resize every column.
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        for column in (0, 2, 13):
            self.setColumnHidden(column, True)
        self.fit_columns()

    def visible_columns(self):
        return [c for c in range(self.model().columnCount()) if not self.isColumnHidden(c)]

    def fit_columns(self):
        if not self._compact:
            return
        available = self.viewport().width()
        if available == self._fit_width:
            return
        self._fit_width = available
        widths = {3: 42, 4: 58, 5: 58, 6: 58, 7: 42,
                  8: 60, 9: 60, 10: 60, 11: 60, 12: 60}
        for column, width in widths.items():
            self.setColumnWidth(column, width)
        self.setColumnWidth(1, max(160, available - sum(widths.values())))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_columns()

    def _keep_footer_height(self, row, old_size, new_size):
        # Hiding a section emits sectionResized(..., 0). Resizing it again from
        # inside that signal leaves phantom space in QHeaderView even though
        # isRowHidden() remains true. Only enforce the minimum for visible rows.
        if (0 < new_size < ROW_HEIGHT + FOOTER_HEIGHT and
                not self.isRowHidden(row) and row in self.model().swelling_footers):
            self.setRowHeight(row, ROW_HEIGHT + FOOTER_HEIGHT)

    def sync_footers(self):
        for row in self._footer_rows:
            if row < self.model().rowCount():
                self.setRowHeight(row, ROW_HEIGHT)
        self._footer_rows = set(self.model().swelling_footers)
        for row in self._footer_rows:
            self.setRowHeight(row, ROW_HEIGHT + FOOTER_HEIGHT)
        self.viewport().update()

    def footer_owner_at(self, point):
        index = self.indexAt(point)
        if index.isValid() and index.row() in self.model().swelling_footers:
            if point.y() >= self.rowViewportPosition(index.row()) + self.rowHeight(index.row()) - FOOTER_HEIGHT:
                return self.model().swelling_footers[index.row()]
        return None

    def mousePressEvent(self, event):
        owner = self.footer_owner_at(event.position().toPoint())
        if owner is not None:
            self.commit_editor()
            self.setCurrentIndex(self.model().index(owner, 1))
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        owner = self.footer_owner_at(event.position().toPoint())
        if owner is not None:
            self.swellingRequested.emit(owner)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def event(self, event):
        # Tab belongs to the outline only on Ítem/Descripción, outside a cell editor.
        if event.type() == QEvent.KeyPress and self.state() != QTableView.EditingState and self.currentIndex().column() in (0, 1):
            if event.key() in (Qt.Key_Tab, Qt.Key_Backtab) and not event.modifiers() & (Qt.ControlModifier | Qt.AltModifier):
                inward = event.key() == Qt.Key_Tab and not event.modifiers() & Qt.ShiftModifier
                self.levelRequested.emit(bool(inward))
                event.accept()
                return True
        return super().event(event)

    def keyPressEvent(self, event):
        if event.text() == '/' and self.currentIndex().column() == 1:
            self.referenceRequested.emit(self.currentIndex().row())
        else:
            return super().keyPressEvent(event)
        event.accept()

    def sync_header(self, current, _previous=None):
        row = current.row() if current.isValid() else -1
        mode = self.model().selection_mode(row)
        if self.horizontalHeader().mode == mode:
            return
        self.horizontalHeader().set_mode(mode)
        self.model().header_labels = labels_for_mode(mode)
        self.model().headerDataChanged.emit(Qt.Horizontal, 0, 13)
        # Column widths remain fixed when switching between standard and steel headers.
