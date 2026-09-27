"""Consecutive detail blocks. Raw measurements are never overwritten."""
import math
from uuid import uuid4


def percent_number(text):
    if not isinstance(text, str):
        raise ValueError('El porcentaje debe ser texto numérico.')
    try:
        number = float(text.strip().replace(',', '.'))
    except (ValueError, OverflowError) as error:
        raise ValueError('Ingresa un porcentaje no negativo, por ejemplo 25 o 12,5.') from error
    if not math.isfinite(number) or number < 0:
        raise ValueError('El porcentaje debe ser no negativo y finito.')
    return number


def validate_swelling(row):
    if 'volume_factor' in row:
        config = row['volume_factor']
        if row['kind'] != 'detail' or row['cells'][2] != 'm3':
            raise ValueError('El FE solo se admite en detalles m3.')
        if (not isinstance(config, dict) or set(config) != {'block', 'factor', 'note'} or
                not isinstance(config.get('block'), str) or not config['block'] or len(config['block']) > 128 or
                not isinstance(config.get('note'), str) or len(config['note']) > 1200):
            raise ValueError('Configuración de FE inválida.')
        factor_number(config['factor'])
    if 'swelling' not in row:
        return
    config = row['swelling']
    if row['kind'] != 'item' or row['cells'][2] != 'm3':
        raise ValueError('El esponjamiento solo se admite en partidas m3.')
    if (not isinstance(config, dict) or set(config) != {'enabled', 'percent', 'note'} or
            type(config.get('enabled')) is not bool or not isinstance(config.get('note'), str)):
        raise ValueError('Configuración de esponjamiento inválida.')
    if len(config['note']) > 1000:
        raise ValueError('La observación admite hasta 1000 caracteres.')
    percent_number(config['percent'])


def swelling_factor(config):
    if config and 'factor' in config:
        return factor_number(config['factor'])
    return 1.0 + percent_number(config['percent']) / 100.0 if config and config['enabled'] else 1.0


def factor_number(text):
    try:
        number = percent_number(text)
    except ValueError as error:
        raise ValueError('Ingresa un FE numérico y finito, por ejemplo 1,20.') from error
    if number < 1:
        raise ValueError('El factor de esponjamiento debe ser mayor o igual a 1 (por ejemplo 1,20).')
    return number


def factor_text(config):
    factor = swelling_factor(config)
    return (f'{factor:.2f}' if factor == round(factor, 2) else format(factor, '.15g')).replace('.', ',')


def volume_blocks(rows):
    """Yield inclusive bounds of runs; inserted/free/title rows split a block.

    Membership lives on each detail so moving, deleting or partially copying a
    block cannot leave stale references, silently include rows or lose a factor.
    """
    start, previous = None, None
    for index, row in enumerate(rows):
        config = row.get('volume_factor')
        if config != previous or config is None:
            if start is not None:
                yield start, index - 1
            start = index if config is not None else None
        previous = config
    if start is not None:
        yield start, len(rows) - 1


def upgrade_legacy(rows):
    """Convert the old whole-item adjustment, retaining empty-item settings.

    No disk writes. An empty legacy item is converted when it gains details.
    Disabled settings preserve the old percentage in the note and use FE=1.
    """
    owner, details = None, []

    def finish():
        if owner is None or not details or 'swelling' not in rows[owner]:
            return
        validate_swelling(rows[owner])
        config = rows[owner]['swelling']
        if any('volume_factor' in rows[i] for i in details):
            raise ValueError('La partida mezcla el ajuste antiguo con FE por detalles.')
        note = config['note']
        if not config['enabled']:
            note += f"\nFE anterior desactivado: {percent_number(config['percent']):.15g} %"
        converted = dict(block=uuid4().hex, factor=format(swelling_factor(config), '.17g'), note=note.strip())
        for i in details:
            rows[i]['volume_factor'] = dict(converted)
        rows[owner].pop('swelling')

    for index, row in enumerate(rows):
        if row['kind'] not in ('detail', 'detail_group'):
            finish()
            owner = index if row['kind'] == 'item' else None
            details = []
        elif row['kind'] == 'detail':
            details.append(index)
    finish()


def adjusted_volume(base, config, engine):
    factor = swelling_factor(config)
    # Empty items have a legitimate zero total; the detail engine requires > 0.
    if base == 0 or factor == 1:
        return base
    return engine.ask_sheet_quantity('m3', [], -1.0 if base < 0 else 1.0, factor, abs(base))
