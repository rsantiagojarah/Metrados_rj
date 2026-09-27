"""Linear-time outline index and pure operations on contiguous subtrees."""
from copy import deepcopy

MAX_ROWS = 10000
MAX_LEVEL = 32
MEASUREMENT_KINDS = ('detail', 'detail_group')


class Outline:
    def __init__(self, rows, strict=False):
        self.parents, self.levels, self.ends = [], [], [len(rows)] * len(rows)
        self.owners = []
        self.previous, self.following = [], [None] * len(rows)
        last_child = {}
        stack = []
        chapter = item = None
        for i, row in enumerate(rows):
            kind = row['kind']
            default = (0 if kind == 'chapter' else
                       self.levels[chapter] + 1 if kind == 'item' and chapter is not None else
                       self.levels[item] + 1 if kind in MEASUREMENT_KINDS and item is not None else 0)
            level = row.get('level', default)
            if type(level) is not int or not 0 <= level <= MAX_LEVEL:
                raise ValueError('Nivel de jerarquía inválido.')
            while stack and self.levels[stack[-1]] >= level:
                self.ends[stack.pop()] = i
            parent = stack[-1] if stack else None
            owner = i if kind == 'item' else (
                self.owners[parent] if parent is not None and kind in MEASUREMENT_KINDS else None)
            if strict:
                expected = 0 if parent is None else self.levels[parent] + 1
                parent_kind = rows[parent]['kind'] if parent is not None else None
                allowed = ('item', 'detail_group') if kind in MEASUREMENT_KINDS else (None, 'chapter')
                if level != expected or parent_kind not in allowed:
                    raise ValueError('Jerarquía inválida: los detalles y sus títulos deben estar dentro de una partida.')
                if kind in MEASUREMENT_KINDS and (owner is None or row['cells'][2] != rows[owner]['cells'][2]):
                    raise ValueError('El detalle y su partida deben tener la misma unidad.')
            self.parents.append(parent)
            self.owners.append(owner)
            self.levels.append(level)
            previous = last_child.get(parent)
            self.previous.append(previous)
            if previous is not None:
                self.following[previous] = i
            last_child[parent] = i
            stack.append(i)
            if kind == 'chapter':
                chapter, item = i, None
            elif kind == 'item':
                item = i

    def siblings(self, index):
        parent = self.parents[index]
        result = []
        cursor = 0 if parent is None else parent + 1
        end = len(self.ends) if parent is None else self.ends[parent]
        while cursor < end:
            result.append(cursor)
            cursor = self.ends[cursor]
        return result


def materialize(rows, *, immutable_catalogs=False):
    outline = Outline(rows, strict=True)
    memo = None
    if immutable_catalogs:
        from metrado.steel_snapshot import freeze
        memo = {id(row['steel_catalog']): freeze(row['steel_catalog'])
                for row in rows if 'steel_catalog' in row}
    result = deepcopy(rows, memo)
    for row, level in zip(result, outline.levels):
        row['level'] = level
    return result


def renumber(rows):
    """Derive codes from sibling order, without changing the input or measurements."""
    outline = Outline(rows, strict=True)
    result, counters = [], {}
    for index, original in enumerate(rows):
        row = dict(original, cells=list(original['cells']))
        if row['kind'] in MEASUREMENT_KINDS:
            row['cells'][0] = ''
        else:
            parent = outline.parents[index]
            number = counters.get(parent, 0) + 1
            counters[parent] = number
            prefix = result[parent]['cells'][0] + '.' if parent is not None else ''
            row['cells'][0] = f'{prefix}{number:02d}'
        result.append(row)
    return result


def container(rows, index, outline=None):
    """Containing title, or the selected title itself."""
    outline = outline or Outline(rows)
    while index is not None and index >= 0:
        if rows[index]['kind'] == 'chapter':
            return index
        index = outline.parents[index]
    return None


def can_parent(rows, index, destination, outline=None):
    outline = outline or Outline(rows)
    kind = rows[index]['kind']
    if destination is None:
        return kind not in MEASUREMENT_KINDS
    if not 0 <= destination < len(rows) or index <= destination < outline.ends[index]:
        return False
    if kind in MEASUREMENT_KINDS:
        return rows[destination]['kind'] in ('item', 'detail_group') and rows[destination]['cells'][2] == rows[index]['cells'][2]
    return rows[destination]['kind'] == 'chapter'


def move_to(rows, index, destination):
    outline = Outline(rows, strict=True)
    if not can_parent(rows, index, destination, outline):
        raise ValueError('Destino incompatible. Los detalles y sus títulos solo se trasladan a partidas o grupos de la misma unidad.')
    result = materialize(rows)
    end = outline.ends[index]
    block = result[index:end]
    position = len(result) if destination is None else outline.ends[destination]
    level = 0 if destination is None else outline.levels[destination] + 1
    delta = level - outline.levels[index]
    for row in block:
        row['level'] += delta
    del result[index:end]
    if position >= end:
        position -= len(block)
    result[position:position] = block
    return renumber(result), position


def move_sibling(rows, index, direction):
    outline = Outline(rows, strict=True)
    siblings = outline.siblings(index)
    offset = siblings.index(index) + direction
    if offset < 0 or offset >= len(siblings):
        raise ValueError('Ya está al inicio o al final de este grupo. Usa «Mover a…» para cambiar de grupo.')
    result = materialize(rows)
    end = outline.ends[index]
    neighbor = siblings[offset]
    if direction < 0:
        result[neighbor:end] = result[index:end] + result[neighbor:index]
        position = neighbor
    else:
        neighbor_end = outline.ends[neighbor]
        result[index:neighbor_end] = result[end:neighbor_end] + result[index:end]
        position = index + neighbor_end - end
    return renumber(result), position


def change_level(rows, index, inward):
    outline = Outline(rows, strict=True)
    measurement = rows[index]['kind'] in MEASUREMENT_KINDS
    if inward:
        siblings = outline.siblings(index)
        offset = siblings.index(index)
        expected = 'detail_group' if measurement else 'chapter'
        if not offset or rows[siblings[offset - 1]]['kind'] != expected:
            raise ValueError('Para aumentar el nivel, coloca la fila después de un título o subtítulo del mismo nivel.')
        return move_to(rows, index, siblings[offset - 1])
    parent = outline.parents[index]
    if parent is None:
        raise ValueError('La fila ya está en el nivel principal.')
    if measurement and rows[parent]['kind'] == 'item':
        raise ValueError('Los detalles y sus títulos deben permanecer dentro de la partida.')
    result = materialize(rows)
    end = outline.ends[index]
    block = result[index:end]
    for row in block:
        row['level'] -= 1
    position = outline.ends[parent] - len(block)
    del result[index:end]
    result[position:position] = block
    return renumber(result), position


def level_selection(rows, selected, inward, outline=None):
    """Validate original roots, not a succession of partially moved selections."""
    outline = outline or Outline(rows, strict=True)
    roots, end = [], -1
    for index in sorted(set(selected)):
        if not 0 <= index < len(rows):
            raise ValueError('Selecciona filas válidas para cambiar de nivel.')
        if index >= end:
            roots.append(index)
            end = outline.ends[index]
    if not roots:
        raise ValueError('Selecciona una o varias filas para cambiar de nivel.')
    anchors = {}
    for index in roots:
        measurement = rows[index]['kind'] in MEASUREMENT_KINDS
        if inward:
            previous = outline.previous[index]
            # Selected siblings stay siblings, even if a selected one is a title.
            anchor = anchors.get(previous, previous)
            expected = 'detail_group' if measurement else 'chapter'
            if anchor is None or rows[anchor]['kind'] != expected:
                raise ValueError('Para aumentar nivel, cada bloque seleccionado debe seguir a un título o subtítulo no seleccionado del mismo nivel. No se cambió ninguna fila.')
            anchors[index] = anchor
        else:
            parent = outline.parents[index]
            if parent is None or (measurement and rows[parent]['kind'] == 'item'):
                raise ValueError('No se puede reducir toda la selección: hay filas en el nivel principal o detalles directamente dentro de una partida. No se cambió ninguna fila.')
    return roots


def change_levels(rows, selected, inward):
    """One atomic O(n) move of selected subtrees; outdenting skips retained siblings."""
    outline = Outline(rows, strict=True)
    roots = level_selection(rows, selected, inward, outline)
    result = materialize(rows)
    if inward:
        for index in roots:
            for row in result[index:outline.ends[index]]:
                row['level'] += 1
        return renumber(result)
    insertions, removed = {}, set()
    for index in roots:
        end = outline.ends[index]
        block = result[index:end]
        for row in block:
            row['level'] -= 1
        parent = outline.parents[index]
        insertions.setdefault(outline.ends[parent], []).append((outline.levels[parent], block))
        removed.update(range(index, end))
    moved = []
    for index in range(len(result) + 1):
        # Nested parents can end together: emit inner children before leaving
        # the outer parent. Stable sorting preserves the order of siblings.
        for _, block in sorted(insertions.get(index, ()), key=lambda pair: -pair[0]):
            moved.extend(block)
        if index < len(result) and index not in removed:
            moved.append(result[index])
    return renumber(moved)
