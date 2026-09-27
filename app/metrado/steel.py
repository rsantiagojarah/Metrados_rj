"""Steel-takeoff labels and Ø list. Quantity formulas live in Rust."""
import re

from metrado.sheet import parent_item

DIAMETERS = ("6mm", "8mm", "3/8\"", "12mm", "1/2\"", "5/8\"", "3/4\"", "1\"", "1 3/8\"")
STEEL_LABELS = ("ÍTEM", "DESCRIPCIÓN", "Und", "Elem.\nsimil.", "Largo", "Gancho\ninicial", "Empalme",
                "N.º de\nveces", "Lon.", "Diámetro", "kg/m", "Kg.", "", "Total")
STEEL_WIDTHS = (88, 490, 38, 38, 56, 56, 60, 44, 72, 80, 56, 72, 44, 80)
BAR_SPEC = re.compile(
    r"(\d+)\s*[ØøΦφ]\s*(\d+\s+\d+/\d+\"?|\d+/\d+\"?|\d+\"|\d+\s*mm)", re.I)


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
