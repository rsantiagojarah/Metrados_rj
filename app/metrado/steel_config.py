"""Versioned steel inputs. Global defaults never participate in a saved calculation."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation, ROUND_CEILING
import math

DIAMETERS = ('6mm', '8mm', '3/8"', '12mm', '1/2"', '5/8"', '3/4"', '1"', '1 3/8"')
MILLIMETERS = (6, 8, 9.525, 12, 12.7, 15.875, 19.05, 25.4, 34.925)
FIELDS = ('weight', 'hook', 'lap')
REFERENCE = (
    "Referencias editables para metrado, no una verificación estructural. "
    "Gancho longitudinal de 90°: incluye tramo libre y curva al eje; no es gancho sísmico de estribo. "
    "E.060: 7.1.2, tabla 7.1, 12.2 y 12.15. "
    "Empalme a tracción clase B: f’c=210 y fy=4200 kgf/cm²; concreto normal, sin epóxico, "
    "barra no superior, separación libre ≥2db y recubrimiento ≥db. "
    "Longitudes redondeadas hacia arriba al centímetro. Para 6 mm, el doblez es una extrapolación "
    "de referencia (6db). Ajustar siempre a los planos y condiciones de la obra."
)
SOURCE = 'https://educa.costosperu.com/wp-content/uploads/2024/08/Norma-E.060-Concreto-armado.pdf'


def number(value, *, zero=False):
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError('Introduce un número válido.')
    try:
        result = Decimal(value.strip().replace(',', '.'))
    except InvalidOperation as error:
        raise ValueError('Introduce un número válido.') from error
    if not result.is_finite() or result < 0 or (not zero and result == 0) or result > Decimal('1e12'):
        raise ValueError('Introduce un número positivo y finito (máximo 10¹²).')
    return result


def initial_catalog():
    result = {}
    fc, fy = 210 * .0980665, 4200 * .0980665
    for diameter, mm in zip(DIAMETERS, MILLIMETERS):
        db = mm / 1000
        inside = (6 if mm <= 25.4 else 8) * db
        hook = 12 * db + math.pi / 4 * (inside + db)
        development = max(.3, fy / ((2.6 if mm <= 19.05 else 2.1) * math.sqrt(fc)) * db)
        result[diameter] = dict(weight=f'{math.pi / 4 * db ** 2 * 7850:.6f}',
                                hook=f'{math.ceil(hook * 100) / 100:.2f}',
                                lap=f'{math.ceil(1.3 * development * 100) / 100:.2f}')
    return result


def validate_catalog(catalog):
    if not isinstance(catalog, dict) or set(catalog) != set(DIAMETERS):
        raise ValueError('La tabla debe contener todos los diámetros de acero.')
    for diameter, values in catalog.items():
        if not isinstance(values, dict) or set(values) != set(FIELDS):
            raise ValueError(f'Configuración incompleta de {diameter}.')
        for field in FIELDS:
            number(values[field])


def validate_row(row):
    if 'steel_catalog' not in row and 'steel_hooks' not in row:
        return
    if row['kind'] not in ('item', 'detail') or row['cells'][2] != 'kg':
        raise ValueError('El catálogo de acero solo pertenece a partidas o detalles en kg.')
    validate_catalog(row.get('steel_catalog'))
    if row['kind'] == 'item':
        if 'steel_hooks' in row:
            raise ValueError('Los ganchos se aplican a detalles, no a la partida.')
        return
    config = row.get('steel_hooks')
    if (not isinstance(config, dict) or set(config) != {'count', 'override'} or
            type(config['count']) is not int or config['count'] not in (0, 1, 2)):
        raise ValueError('Configuración de ganchos inválida.')
    if config['override'] is not None:
        number(config['override'])


def adopt(row, catalog, *, preserve_hooks=False):
    validate_catalog(catalog)
    if row['kind'] == 'detail' and row['cells'][7] and row['cells'][7] not in catalog and not row['direct']:
        raise ValueError('El diámetro ' + row['cells'][7] + ' no está en la tabla de aceros. '
                         'Corrígelo antes de actualizar; no se cambió ningún detalle.')
    old = row.get('steel_hooks')
    row['steel_catalog'] = deepcopy(catalog)
    if row['kind'] == 'detail':
        if old is not None:
            row['steel_hooks'] = deepcopy(old)
        else:
            hook = row['cells'][5].strip()
            nonzero = preserve_hooks and not row['direct'] and hook and number(hook, zero=True) > 0
            row['steel_hooks'] = dict(count=1 if nonzero else 0, override=hook if nonzero else None)
        sync_dimensions(row)


def dimensions(row):
    """Per-bar hooks and laps; exact multiples do not introduce an extra splice."""
    config = row['steel_hooks']
    entry = row['steel_catalog'][row['cells'][7]]
    hook = number(config['override'] or entry['hook']) * config['count']
    base = number(row['cells'][4]) + hook
    count = max(0, int((base / Decimal(9)).to_integral_value(rounding=ROUND_CEILING)) - 1)
    return hook, number(entry['lap']) * count, count


def sync_dimensions(row):
    if 'steel_hooks' not in row or row['direct']:
        return
    try:
        hook, lap, _ = dimensions(row)
        row['cells'][5:7] = [str(hook), str(lap)]
    except (ValueError, KeyError):
        # Pending input is allowed, but must never display stale calculated dimensions.
        row['cells'][5:7] = ['', '']


def selected_details(rows, selected):
    indexes = sorted(set(selected))
    if not indexes or any(i < 0 or i >= len(rows) or rows[i]['kind'] != 'detail' or
                          rows[i]['cells'][2] != 'kg' or rows[i]['direct'] for i in indexes):
        raise ValueError('Selecciona uno o varios detalles de acero, sin títulos ni cantidades directas.')
    for i in indexes:
        if rows[i]['cells'][7] not in DIAMETERS:
            raise ValueError('Elige primero el diámetro de todos los detalles seleccionados.')
    return indexes
