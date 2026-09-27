"""Steel-takeoff labels and Ø list. Quantity formulas live in Rust."""
import re
import math

from metrado.sheet import parent_item
from metrado.steel_config import DIAMETERS

STEEL_LABELS = ("ÍTEM", "DESCRIPCIÓN", "Und", "Elem.\nsimil.", "Largo", "Ganchos", "Empalme",
                "N.º de\nveces", "Lon.", "Diámetro", "kg/m", "Kg.", "", "Total")
STEEL_WIDTHS = (88, 490, 38, 38, 56, 56, 60, 44, 72, 80, 56, 72, 44, 80)
NUMBER = r'[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+-]?\d+)?'
DIAMETER = r'\d+\s+\d+/\d+["″]?|\d+/\d+["″]?|\d+["″]|\d+\s*mm'
BAR_SPEC = re.compile(rf'(?<![\w.,])({NUMBER})\s*[ØøΦφ]\s*({DIAMETER})', re.I)
ANNOTATION = re.compile(rf'(?<![\w.,])(?:(?P<count>{NUMBER}|\?)\s*)?[ØøΦφ]\s*(?P<diameter>{DIAMETER}|\?)', re.I)


def description_base(description):
    """Move existing bar annotations out of the prose, including repeated ones."""
    if not ANNOTATION.search(description):
        return description.strip()
    return re.sub(r'\s+', ' ', ANNOTATION.sub('', description)).strip()


def sync_description(row, engine):
    """Persist one suffix, derived from the same inputs as the visible bar count."""
    if row['kind'] != 'detail' or row['cells'][2] != 'kg' or 'reference' in row:
        return
    cells = row['cells']
    try:
        count = (float(cells[9].replace(',', '.')) if row['direct'] else
                 engine.ask_sheet_quantity('und', [], float(cells[10].replace(',', '.')),
                                           float(cells[9].replace(',', '.') or '1'), None))
        quantity = f'{count:g}' if math.isfinite(count) and count != 0 else '?'
    except (ValueError, OverflowError):
        quantity = '?'
    diameter = cells[7].strip() or '?'
    if not re.fullmatch(DIAMETER, diameter, re.I):
        diameter = '?'
    base = description_base(cells[1])
    cells[1] = f'{base} {quantity} Ø{diameter}'.strip()


def edit_description(row, description):
    """An unchanged generated suffix is not a new quantity input.

    Legacy factors must survive a prose-only edit (e.g. 53 bars x 2 repetitions).
    An explicitly changed quantity means the total visible count, just like column 7.
    """
    cells = row['cells']
    old_matches = list(ANNOTATION.finditer(cells[1]))
    new_matches = list(ANNOTATION.finditer(description))
    old = old_matches[-1] if old_matches else None
    new = new_matches[-1] if new_matches else None
    if new is not None:
        count, diameter = new.group('count'), new.group('diameter')
        if count not in (None, '?') and (old is None or count != old.group('count')):
            if row['direct']:
                cells[9] = count
            else:
                cells[10], cells[9] = count, '1'
        if diameter != '?':
            diameter = re.sub(r'\s+', ' ', diameter.replace('″', '"')).strip().lower()
            if not diameter.endswith(('"', 'mm')):
                diameter += '"'
            cells[7] = diameter
    cells[1] = description


def header_mode(rows, index):
    if index < 0 or index >= len(rows) or rows[index]["kind"] == "chapter":
        return "standard"
    owner = index if rows[index]["kind"] == "item" else parent_item(rows, index)
    if owner is None:
        return "standard"
    return "steel" if rows[owner]["cells"][2] == "kg" else "standard"


def apply_bar_spec(cells, description):
    """Copy n° and Ø from a label like '53 Ø1\"'. Does not calculate quantities."""
    match = BAR_SPEC.search(description)
    if match:
        cells[10] = match.group(1)
        diameter = match.group(2).strip()
    else:
        diameter_match = re.search(r'[ØøΦφ]\s*(\d+\s+\d+/\d+"?|\d+/\d+"?|\d+"|\d+\s*mm)', description, re.I)
        if not diameter_match:
            return
        diameter = diameter_match.group(1).strip()
    if not diameter.endswith('"') and not diameter.lower().endswith("mm"):
        diameter += '"'
    cells[7] = diameter


def first_steel_item(rows):
    for index, row in enumerate(rows):
        if row["kind"] == "item" and row["cells"][2] == "kg":
            return index
    return None



def set_bar_diameter(cells, diameter):
    """Keep an existing diameter annotation consistent with the selector."""
    cells[7] = diameter
    pattern = r'([ØøΦφ]\s*)(\d+\s+\d+/\d+"?|\d+/\d+"?|\d+"|\d+\s*mm)'
    cells[1] = re.sub(pattern, lambda match: match.group(1) + diameter, cells[1], flags=re.I)
