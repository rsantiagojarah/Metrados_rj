"""Configurable interpretation of AutoCAD steel distribution labels."""
from decimal import Decimal, InvalidOperation, ROUND_CEILING
import re

from metrado.steel_config import DIAMETERS


DEFAULT_TEMPLATE = '{multiplicador}Ø{diametro}@{espaciamiento}'
FIELDS = ('multiplicador', 'diametro', 'espaciamiento')
TOKEN = re.compile(r'\{([^{}]+)\}')
POSITIVE = r'(?:\d+(?:[.,]\d*)?|[.,]\d+)'
DIAMETER = r'(?:\d+\s+\d+/\d+["″]?|\d+/\d+["″]?|\d+["″]|\d+\s*mm)'


def _literal_pattern(value):
    parts = []
    whitespace = False
    for character in value:
        if character.isspace():
            whitespace = True
            continue
        if whitespace:
            parts.append(r'\s*')
            whitespace = False
        if character in 'ØøΦφ':
            parts.append(r'[ØøΦφ]')
        else:
            parts.append(re.escape(character))
    if whitespace:
        parts.append(r'\s*')
    return ''.join(parts)


def compile_template(template):
    """Compile a user template without accepting arbitrary regular expressions."""
    if not isinstance(template, str) or not template.strip() or len(template) > 200:
        raise ValueError('El formato debe contener entre 1 y 200 caracteres.')
    matches = list(TOKEN.finditer(template))
    names = [match.group(1) for match in matches]
    if any(name not in FIELDS for name in names) or len(names) != len(set(names)):
        raise ValueError('Usa cada marcador como máximo una vez: {multiplicador}, {diametro}, {espaciamiento}.')
    if not {'diametro', 'espaciamiento'} <= set(names):
        raise ValueError('El formato debe incluir {diametro} y {espaciamiento}.')
    remainder = TOKEN.sub('', template)
    if '{' in remainder or '}' in remainder:
        raise ValueError('El formato contiene llaves o marcadores no válidos.')

    patterns = {
        'multiplicador': r'(?P<multiplicador>\d+)',
        'diametro': rf'(?P<diametro>{DIAMETER})',
        'espaciamiento': rf'(?P<espaciamiento>{POSITIVE})',
    }
    pieces, cursor = [], 0
    for match in matches:
        literal = _literal_pattern(template[cursor:match.start()])
        if literal:
            pieces.append(literal)
        pieces.append(patterns[match.group(1)])
        cursor = match.end()
    literal = _literal_pattern(template[cursor:])
    if literal:
        pieces.append(literal)
    return re.compile(r'^\s*' + r'\s*'.join(pieces) + r'\s*$', re.I)


def validate_template(template):
    compile_template(template)
    return template.strip()


def _decimal(value, label):
    try:
        result = Decimal(str(value).strip().replace(',', '.'))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f'{label} debe ser un número positivo y finito.') from error
    if not result.is_finite() or result <= 0 or result > Decimal('1e12'):
        raise ValueError(f'{label} debe ser un número positivo y finito.')
    return result


def _normalize_diameter(value):
    normalized = re.sub(r'\s+', ' ', value.replace('″', '"')).strip().lower()
    if not normalized.endswith(('"', 'mm')):
        normalized += '"'
    by_key = {diameter.lower(): diameter for diameter in DIAMETERS}
    if normalized not in by_key:
        raise ValueError('El diámetro leído no existe en la tabla global de aceros.')
    return by_key[normalized]


def parse_distribution(text, template=DEFAULT_TEMPLATE):
    """Return multiplier, diameter and spacing from one selected CAD label."""
    if not isinstance(text, str) or not text.strip() or len(text) > 500:
        raise ValueError('El texto de distribución está vacío o es demasiado largo.')
    source = re.sub(r'%%c', 'Ø', text, flags=re.I).replace('\\U+2205', 'Ø')
    match = compile_template(template).fullmatch(source)
    if match is None:
        raise ValueError(f'El texto no coincide con el formato configurado: {template}')
    multiplier = int(match.groupdict().get('multiplicador') or '1')
    if multiplier <= 0 or multiplier > 1_000_000:
        raise ValueError('El multiplicador debe ser un entero positivo.')
    return {
        'multiplier': multiplier,
        'diameter': _normalize_diameter(match.group('diametro')),
        'spacing_m': _decimal(match.group('espaciamiento'), 'El espaciamiento'),
    }


def distributed_bar_count(distance_m, spacing_m, multiplier=1):
    """Count both ends: multiplier × (ceil(distribution/spacing) + 1)."""
    distance = _decimal(distance_m, 'La distancia de distribución')
    spacing = _decimal(spacing_m, 'El espaciamiento')
    if type(multiplier) is not int or multiplier <= 0:
        raise ValueError('El multiplicador debe ser un entero positivo.')
    intervals = int((distance / spacing).to_integral_value(rounding=ROUND_CEILING))
    count = multiplier * (intervals + 1)
    if count > 1_000_000_000:
        raise ValueError('La distribución produce demasiadas barras.')
    return count
