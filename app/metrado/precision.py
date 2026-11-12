"""Canonical document inputs. Quantity arithmetic and result rounding live in Rust.

Only general measurements are quantized here. Coefficients, spacing and
diameters retain their source precision.
"""
from decimal import Decimal, DecimalException, ROUND_HALF_UP, localcontext
from functools import lru_cache


@lru_cache(maxsize=8192)
def input_text(text):
    if not text.strip():
        return text
    try:
        value = Decimal(text.strip().replace(',', '.'))
        if not value.is_finite() or abs(value) > Decimal('1e308'):
            return text
        with localcontext() as context:
            context.prec = max(28, len(value.as_tuple().digits), value.adjusted() + 4)
            rounded = value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return text if rounded == value else format(rounded, '.2f')
    except (DecimalException, ValueError):
        return text  # Incomplete inputs remain editable and pending.


def normalize_row(row):
    if row['kind'] != 'detail':
        return
    cells = row['cells']
    columns = (3, 7) if 'reference' in row else (
        (3, 4, 5, 6, 9, 10) if cells[2] == 'kg' else (3, 4, 5, 6, 7, 9))
    for c in columns:
        if isinstance(cells[c], str):
            cells[c] = input_text(cells[c])
    row['direct'] = input_text(row['direct'])


def normalize_rows(rows):
    for row in rows:
        normalize_row(row)


def calculation_rows(rows):
    """Normalize external callers without mutating the supplied document."""
    result = []
    for row in rows:
        copy = dict(row, cells=list(row['cells']))
        normalize_row(copy)
        result.append(copy)
    return result


def coefficient_text(value):
    number = Decimal(str(value).replace(',', '.'))
    if not number.is_finite():
        raise ValueError('El coeficiente debe ser finito.')
    text = format(number, 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text
