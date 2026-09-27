"""Stable item links; iterative dependency ordering, never cached totals on disk."""
from collections import deque
import math

UNITS = ('m', 'm2', 'm3', 'kg', 'und', 'mes', 'vje', 'glb')
FIELDS = ('source', 'label', 'source_unit', 'target_unit', 'factor_name', 'factor')


def factor_number(text):
    if not isinstance(text, str):
        raise ValueError('Ingresa un factor numérico positivo.')
    try:
        value = float(text.strip().replace(',', '.'))
    except (ValueError, OverflowError) as error:
        raise ValueError('Ingresa un factor numérico positivo.') from error
    if not math.isfinite(value) or value <= 0:
        raise ValueError('El factor debe ser positivo y finito; para restar usa Elem. simil. o N.º de veces.')
    return value


def validate_row(row):
    if 'reference' not in row:
        return
    ref = row['reference']
    if (row['kind'] != 'detail' or not isinstance(ref, dict) or set(ref) != set(FIELDS)
            or any(not isinstance(ref[k], str) for k in FIELDS)
            or not ref['source'] or len(ref['source']) > 128
            or ref['source_unit'] not in UNITS or ref['target_unit'] not in UNITS
            or len(ref['label']) > 4000 or len(ref['factor_name']) > 160
            or row['direct'] or 'steel_hooks' in row or 'steel_catalog' in row):
        raise ValueError('Referencia de partida inválida.')
    if ref['source_unit'] == ref['target_unit']:
        if ref['factor'] or ref['factor_name']:
            raise ValueError('Una referencia de la misma unidad no lleva factor.')
    else:
        if not ref['factor_name'].strip():
            raise ValueError('Indica qué representa el factor de conversión.')
        factor_number(ref['factor'])


def make_reference(source, target_unit, name='', factor=''):
    source_unit = source['cells'][2]
    if source_unit == target_unit:
        name, factor = '', ''
    return dict(source=source['id'], label=source['cells'][1], source_unit=source_unit,
                target_unit=target_unit, factor_name=name.strip(), factor=factor.strip())


def conversion(ref, source_unit, target_unit):
    # Equality never needs a conversion, even after a unit edit.
    if source_unit == target_unit:
        return 1.0
    if (ref['source_unit'], ref['target_unit']) != (source_unit, target_unit) or not ref['factor']:
        raise ValueError('Cambió la unidad. Escribe / para confirmar la referencia y su nuevo factor.')
    return factor_number(ref['factor'])


def description(row, sources):
    ref = row['reference']
    source = sources.get(ref['source'])
    label = f"{source['cells'][0]} · {source['cells'][1]}" if source else ref['label'] + ' (origen no disponible)'
    source_unit = source['cells'][2] if source else ref['source_unit']
    suffix = ''
    if source_unit != row['cells'][2] and ref['factor']:
        suffix = f" · {ref['factor_name']}: {ref['factor']}"
    return '↗ ' + label + suffix


def dependency_order(rows):
    """O(rows + links), no recursion even for thousands of chained items."""
    items, blocks, owner, links = {}, {}, None, {}
    for i, row in enumerate(rows):
        if row['kind'] not in ('detail', 'detail_group'):
            if owner is not None:
                blocks[owner] = (blocks[owner][0], i)
            owner = i if row['kind'] == 'item' else None
            if owner is not None:
                blocks[owner] = (i, len(rows))
                if row.get('id'):
                    items[row['id']] = i
                links[i] = set()
        elif owner is not None and 'reference' in row:
            links[owner].add(row['reference']['source'])
    dependencies = {i: {items[s] for s in sources if s in items} for i, sources in links.items()}
    dependents = {i: [] for i in blocks}
    for i, sources in dependencies.items():
        for source in sources:
            dependents[source].append(i)
    remaining = {i: len(sources) for i, sources in dependencies.items()}
    queue = deque(i for i, count in remaining.items() if count == 0)
    order = []
    while queue:
        i = queue.popleft()
        order.append(i)
        for target in dependents[i]:
            remaining[target] -= 1
            if remaining[target] == 0:
                queue.append(target)
    return order, blocks, set(blocks).difference(order)


def check_cycles(rows):
    if any('reference' in row for row in rows) and dependency_order(rows)[2]:
        raise ValueError('Esta operación crea una referencia circular entre partidas. No se aplicó ningún cambio.')


class DependencyIndex:
    """Cached only while row identities, order and reference edges stay fixed."""
    def __init__(self, rows):
        self.items = {row['id']: i for i, row in enumerate(rows) if row['kind'] == 'item'}
        self.has_links = any('reference' in row for row in rows)
        self.blocked = set()
        self.dependents = {}
        self.rank = {}
        if not self.has_links:
            return
        order, _, self.blocked = dependency_order(rows)
        self.rank = {owner: rank for rank, owner in enumerate(order)}
        owner = None
        for i, row in enumerate(rows):
            if row['kind'] not in ('detail', 'detail_group'):
                owner = i if row['kind'] == 'item' else None
            elif owner is not None and 'reference' in row:
                source = self.items.get(row['reference']['source'])
                if source is not None:
                    self.dependents.setdefault(source, set()).add(owner)

    def affected(self, owner):
        affected, pending = {owner}, [owner]
        while pending:
            for target in self.dependents.get(pending.pop(), ()):
                if target not in affected:
                    affected.add(target)
                    pending.append(target)
        return sorted(affected, key=self.rank.__getitem__)


def linked_quantity(base, factor, similar, times, engine):
    # Keep signed arithmetic and overflow validation in the quantity engine.
    engine.ask_sheet_quantity('und', [], similar, times, None)
    if not math.isfinite(base):
        raise ValueError('Total de origen inválido.')
    if base == 0:
        return 0.0
    converted = engine.ask_sheet_quantity('und', [], factor, -1.0 if base < 0 else 1.0, abs(base))
    return engine.ask_sheet_quantity('und', [], similar, times * (-1.0 if converted < 0 else 1.0), abs(converted))


def calculate_linked(rows, engine, plain):
    order, blocks, blocked = dependency_order(rows)
    values, errors, sources = {}, {}, {}
    for i in order:
        start, end = blocks[i]
        local_values, local_errors = plain(rows[start:end], engine, sources)
        values.update(((r + start, c), v) for (r, c), v in local_values.items())
        errors.update((r + start, e) for r, e in local_errors.items())
        sources[rows[i].get('id')] = (rows[i]['cells'][2], local_values.get((0, 13)))
    for i in blocked:
        start, end = blocks[i]
        for r in range(start, end):
            if rows[r]['kind'] in ('item', 'detail'):
                errors[r] = 'Referencia circular: revisa las partidas relacionadas.'
    return values, errors
