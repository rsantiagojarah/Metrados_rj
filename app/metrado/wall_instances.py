"""Self-contained wall instances; replace only one instance in one undo step."""
from copy import deepcopy
from dataclasses import asdict
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from metrado.hierarchy import materialize, Outline, MAX_ROWS
from metrado.identity import ensure_ids
from metrado.sheet import new_row
from metrado.wall_types import WallType, generate_wall_rows, positive
from metrado.wall_rebar import hook_lengths, position_key


DESTINATION_UNITS = {
    'pantalla:m3': 'm3', 'zapata:m3': 'm3',
    'pantalla:m2': 'm2', 'zapata:m2': 'm2',
    'pantalla:kg': 'kg', 'zapata:kg': 'kg',
}


def validate_wall_row(row):
    config = row.get('wall_generated')
    if config is None:
        return
    if row['kind'] not in ('detail', 'detail_group') or not isinstance(config, dict):
        raise ValueError('Vínculo de muro inválido.')
    # Previous builds only kept a label and dimensions, without an instance ID.
    if 'version' not in config:
        if set(config) != {'type', 'component', 'length', 'height'}:
            raise ValueError('Vínculo de muro antiguo inválido.')
        return
    if config.get('version') != 1:
        raise ValueError('Versión de muro no compatible.')
    for field in ('instance_id', 'name', 'key'):
        if not isinstance(config.get(field), str) or not 0 < len(config[field]) <= 200:
            raise ValueError('Identificación de tramo inválida.')
    WallType.from_dict(deepcopy(config.get('wall')))
    positive(config.get('length'), 'Longitud del tramo')
    if config.get('height') is not None:
        positive(config['height'], 'Altura del tramo')
    destinations = config.get('destinations')
    if (not isinstance(destinations, dict) or not destinations or
            any((key not in DESTINATION_UNITS and key not in ('m2', 'm3', 'kg')) or
                not isinstance(identity, str) or not identity
                for key, identity in destinations.items())):
        raise ValueError('Partidas de destino inválidas.')
    if 'description' in config and (not isinstance(config['description'], str) or
                                    len(config['description']) > 160):
        raise ValueError('Descripción de tramo inválida.')


def selected_wall(rows, index):
    if not 0 <= index < len(rows):
        raise ValueError('Selecciona un detalle de un muro generado.')
    config = rows[index].get('wall_generated')
    if not config:
        raise ValueError('Selecciona un detalle de un muro generado.')
    validate_wall_row(rows[index])
    if 'instance_id' not in config:
        raise ValueError('Este detalle se creó con la versión anterior y no tiene vínculo de tramo. '
                         'Sus cantidades se conservan; para edición conjunta debes generar un tramo nuevo.')
    return deepcopy(config)


def apply_wall(rows, wall, length, height, destinations, name, instance_id=None, description=None):
    """Return a new sheet without mutating its source; IDs survive regeneration."""
    if not isinstance(name, str) or not name.strip() or len(name) > 160:
        raise ValueError('Escribe un nombre de tramo de hasta 160 caracteres.')
    wall = WallType.from_dict(asdict(wall))
    distributions = list(wall.distributions)
    if wall.cut_left and not any(item['component'] == 'refuerzo_cortado' for item in distributions):
        distributions.append(dict(component='refuerzo_cortado',side='izquierda',diameter=wall.cut_diameter))
    for item in distributions:
        start,end = hook_lengths(wall,item)
        wall.hooks[position_key(item)] = dict(start=start,end=end)
    entries = generate_wall_rows(wall, length, height)
    if not destinations:
        raise ValueError('Selecciona al menos una partida de destino.')
    source = materialize(rows)
    ensure_ids(source)
    item_by_id = {row['id']: row for row in source if row['kind'] == 'item'}
    for key, identity in destinations.items():
        unit = DESTINATION_UNITS.get(key, key if key in ('m2', 'm3', 'kg') else None)
        if unit is None or identity not in item_by_id or item_by_id[identity]['cells'][2] != unit:
            raise ValueError('Una partida de destino ya no existe o cambió de unidad. Selecciónala de nuevo.')
    old = [row for row in source if instance_id and row.get('wall_generated', {}).get('instance_id') == instance_id]
    if instance_id and not old:
        raise ValueError('El tramo seleccionado ya no existe.')
    old_ids = {row['wall_generated']['key']: row['id'] for row in old if row['kind'] == 'detail'}
    if len(old_ids) != len([row for row in old if row['kind'] == 'detail']):
        raise ValueError('El tramo tiene detalles duplicados; no se modificó ninguna fila.')
    instance_id = instance_id or uuid4().hex
    result = [row for row in source if row.get('wall_generated', {}).get('instance_id') != instance_id]
    outline = Outline(result, strict=True)
    by_id = {row['id']: i for i, row in enumerate(result)}
    additions = {identity: [] for identity in destinations.values()}
    counters = {}
    for unit, value, *rest in entries:
        category = 'zapata' if rest[-1] == 'dentellon' else rest[-1]
        destination_key = f'{category}:{unit}'
        destination = destinations.get(destination_key, destinations.get(unit))
        counters[destination_key] = counters.get(destination_key, 0) + 1
        if destination is None:
            continue
        key = f'{destination_key}:{counters[destination_key]}'
        if unit == 'kg':
            row = value
        else:
            row = new_row('detail', description=value, unit=unit)
            row['cells'][3] = str(rest[1])
            # The sheet calculates from the same two-decimal dimensions it shows.
            # Keep the type snapshot and steel geometry at their original precision.
            row['cells'][4:4 + len(rest[0])] = [
                str(Decimal(str(v)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
                for v in rest[0]
            ]
        row['cells'][1] = (row['cells'][1] if destination_key in destinations else
                           f'{name.strip()} · {row["cells"][1]}')
        row['id'] = old_ids.get(key, uuid4().hex)
        row['level'] = outline.levels[by_id[destination]] + (2 if destination_key in destinations else 1)
        row['wall_generated'] = dict(version=1, instance_id=instance_id, key=key,
                                    name=name.strip(), wall=asdict(wall), length=float(length),
                                    height=None if height is None else float(height),
                                    destinations=dict(destinations), description=description or '')
        validate_wall_row(row)
        additions[destination].append(row)
    if len(result) + sum(map(len, additions.values())) > MAX_ROWS:
        raise ValueError('La generación supera el límite de 10 000 filas.')
    if not any(additions.values()):
        raise ValueError('No hay detalles para las partidas seleccionadas.')
    grouped = any(key in DESTINATION_UNITS for key in destinations)
    for destination, details in sorted(additions.items(), key=lambda pair: by_id[pair[0]], reverse=True):
        if grouped and details:
            title = new_row('detail_group', description=name.strip(), unit=item_by_id[destination]['cells'][2])
            title['id'] = uuid4().hex
            title['level'] = outline.levels[by_id[destination]] + 1
            title['wall_generated'] = dict(version=1, instance_id=instance_id,
                                           key='title:' + destination, name=name.strip(), wall=asdict(wall),
                                           length=float(length), height=None if height is None else float(height),
                                           destinations=dict(destinations), description=description or '')
            validate_wall_row(title)
            details = [title, *details]
        end = outline.ends[by_id[destination]]
        result[end:end] = details
    Outline(result, strict=True)
    return result
