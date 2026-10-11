"""Persistent wall types and deterministic wall takeoff generation."""
from contextlib import closing
from dataclasses import dataclass, field, asdict
import json
import math
from pathlib import Path
import sqlite3

from PySide6.QtCore import QStandardPaths

from metrado.sheet import new_row, steel_detail
from metrado.steel_config import DIAMETERS
from metrado.wall_rebar import reinforcement

COMPONENTS = {
    'pantalla_vertical': 'Pantalla · vertical',
    'pantalla_horizontal': 'Pantalla · horizontal',
    'zapata': 'Zapata · longitudinal',
    'zapata_transversal': 'Zapata · transversal',
    'dentellon': 'Dentellón · longitudinal',
    'dentellon_transversal': 'Dentellón · transversal',
    'refuerzo_cortado': 'Pantalla · refuerzo cortado',
}
SIDES = {'izquierda': 'Izquierda (relleno)', 'derecha': 'Derecha',
         'superior': 'Superior', 'inferior': 'Inferior'}

# Positions in MURO MODELO.pdf; the editor never creates or removes positions.
WALL_POSITIONS = (
    ('pantalla_vertical', 'izquierda', 'Pantalla · vertical izquierda'),
    ('pantalla_vertical', 'derecha', 'Pantalla · vertical derecha'),
    ('pantalla_horizontal', 'izquierda', 'Pantalla · horizontal izquierda'),
    ('pantalla_horizontal', 'derecha', 'Pantalla · horizontal derecha'),
    ('refuerzo_cortado', 'izquierda', 'Pantalla · refuerzo cortado'),
    ('zapata_transversal', 'superior', 'Zapata · transversal superior'),
    ('zapata_transversal', 'inferior', 'Zapata · transversal inferior'),
    ('zapata', 'superior', 'Zapata · longitudinal superior'),
    ('zapata', 'inferior', 'Zapata · longitudinal inferior'),
    ('dentellon_transversal', 'izquierda', 'Dentellón · transversal'),
    ('dentellon', 'izquierda', 'Dentellón · longitudinal'),
)


def component_sides(component):
    return ('superior', 'inferior') if component.startswith('zapata') else (
        ('izquierda',) if component == 'refuerzo_cortado' else ('izquierda', 'derecha'))


def positive(value, label):
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError) as error:
        raise ValueError(f'{label}: introduce un número positivo.') from error
    if not math.isfinite(result) or not 0 < result <= 1e6:
        raise ValueError(f'{label}: introduce un número positivo, máximo 1 000 000.')
    return result


def nonnegative(value, label):
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError) as error:
        raise ValueError(f'{label} debe ser un número.') from error
    if not math.isfinite(result) or not 0 <= result <= 1e6:
        raise ValueError(f'{label} debe ser mayor o igual a cero.')
    return result


def wall_catalog_path():
    return Path(QStandardPaths.writableLocation(QStandardPaths.GenericConfigLocation)) / 'Metrados' / 'muros.sqlite3'


@dataclass
class WallType:
    name: str
    description: str = ''
    screen_height: float = 8.30
    top_thickness: float = 0.50
    bottom_thickness: float = 1.25
    footing_left: float = 3.20
    footing_right: float = 3.00
    footing_thickness: float = 1.20
    dentellon: bool = False
    dentellon_width: float = 0.60
    dentellon_depth: float = 0.70
    dentellon_slope: float = 0.0
    cut_left: bool = False
    cut_length: float = 4.60
    cut_diameter: str = '5/8"'
    cut_spacing: float = 0.25
    distributions: list = field(default_factory=list)
    hooks: dict = field(default_factory=dict)
    horizontal_in_footing: bool = False

    def validate(self):
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name) > 160:
            raise ValueError('El tipo de muro necesita un nombre.')
        dimensions = ('screen_height', 'top_thickness', 'bottom_thickness', 'footing_thickness')
        for key in dimensions + ('dentellon_width', 'dentellon_depth', 'cut_length', 'cut_spacing'):
            setattr(self, key, positive(getattr(self, key), key.replace('_', ' ')))
        for key in ('footing_left', 'footing_right', 'dentellon_slope'):
            setattr(self, key, nonnegative(getattr(self, key), key.replace('_', ' ')))
        if self.cut_diameter not in DIAMETERS:
            raise ValueError('Selecciona un diámetro del catálogo para el refuerzo cortado.')
        if any(type(value) is not bool for value in (self.dentellon, self.cut_left, self.horizontal_in_footing)):
            raise ValueError('Opciones de muro inválidas.')
        allowed_hooks = {c + ':' + s for c in COMPONENTS for s in component_sides(c)}
        if not isinstance(self.hooks, dict) or any(key not in allowed_hooks for key in self.hooks):
            raise ValueError('Posiciones de gancho inválidas.')
        for hooks in self.hooks.values():
            if not isinstance(hooks, dict) or set(hooks) != {'start', 'end'}:
                raise ValueError('Define ambos extremos del gancho.')
            for length in hooks.values():
                if type(length) not in (int, float) or not math.isfinite(length) or not 0 <= length <= 1e6:
                    raise ValueError('El gancho debe ser un número entre 0 y 1 000 000 m.')
        if not isinstance(self.distributions, list) or len(self.distributions) > 100:
            raise ValueError('Se admiten hasta 100 distribuciones de acero.')
        for item in self.distributions:
            if not isinstance(item, dict) or set(item) != {'component', 'side', 'diameter', 'spacing', 'fixed_length'}:
                raise ValueError('Distribución de acero incompleta.')
            if item['component'] not in COMPONENTS or item['side'] not in component_sides(item['component']):
                raise ValueError('Selecciona un componente y una cara compatibles.')
            positive(item['spacing'], 'Separación del acero')
            if item['diameter'] not in DIAMETERS:
                raise ValueError('Selecciona un diámetro del catálogo.')
            if item['fixed_length'] is not None:
                positive(item['fixed_length'], 'Longitud fija')

    @classmethod
    def from_dict(cls, data):
        try:
            value = cls(**data)
        except TypeError as error:
            raise ValueError('Configuración de muro inválida.') from error
        value.validate()
        return value


def default_wall_type():
    return WallType(
        name='Muro modelo', description='Pantalla con zapata y dentellón opcional', dentellon_slope=0.4,
        cut_diameter='3/4"', cut_spacing=0.20,
        distributions=[
            dict(component='pantalla_vertical', side='izquierda', diameter='3/4"', spacing=0.20, fixed_length=None),
            dict(component='pantalla_vertical', side='derecha', diameter='3/4"', spacing=0.20, fixed_length=None),
            dict(component='pantalla_horizontal', side='izquierda', diameter='5/8"', spacing=0.25, fixed_length=None),
            dict(component='pantalla_horizontal', side='derecha', diameter='5/8"', spacing=0.25, fixed_length=None),
            dict(component='zapata', side='superior', diameter='5/8"', spacing=0.20, fixed_length=None),
            dict(component='zapata', side='inferior', diameter='5/8"', spacing=0.20, fixed_length=None),
            dict(component='zapata_transversal', side='superior', diameter='3/4"', spacing=0.15, fixed_length=None),
            dict(component='zapata_transversal', side='inferior', diameter='3/4"', spacing=0.10, fixed_length=None),
            dict(component='dentellon', side='izquierda', diameter='5/8"', spacing=0.25, fixed_length=None),
            dict(component='dentellon_transversal', side='izquierda', diameter='5/8"', spacing=0.25, fixed_length=None),
        ])


class WallTypeStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else wall_catalog_path()

    def _ensure(self, connection):
        connection.execute('CREATE TABLE IF NOT EXISTS wall_types (name TEXT PRIMARY KEY, payload TEXT NOT NULL)')

    def read(self):
        if not self.path.exists():
            return [default_wall_type()]
        with closing(sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True)) as connection:
            result = [WallType.from_dict(json.loads(payload)) for payload, in
                      connection.execute('SELECT payload FROM wall_types ORDER BY name COLLATE NOCASE')]
            return result or [default_wall_type()]

    def save(self, wall, previous_name=None):
        wall.validate()
        wall.name = wall.name.strip()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as connection:
            self._ensure(connection)
            if previous_name and previous_name != wall.name:
                if connection.execute('SELECT 1 FROM wall_types WHERE name=?', (wall.name,)).fetchone():
                    raise ValueError('Ya existe otro tipo con ese nombre.')
                connection.execute('DELETE FROM wall_types WHERE name=?', (previous_name,))
            connection.execute('INSERT OR REPLACE INTO wall_types VALUES (?, ?)',
                               (wall.name.strip(), json.dumps(asdict(wall), ensure_ascii=False)))
            connection.commit()

    def delete(self, name):
        if not self.path.exists():
            return
        with closing(sqlite3.connect(self.path)) as connection:
            self._ensure(connection)
            connection.execute('DELETE FROM wall_types WHERE name=?', (name,))
            connection.commit()

    def export_json(self, path, names=None):
        selected = [w for w in self.read() if names is None or w.name in names]
        Path(path).write_text(json.dumps([asdict(w) for w in selected], ensure_ascii=False, indent=2), encoding='utf-8')

    def import_json(self, path, replace=False):
        if Path(path).stat().st_size > 2_000_000:
            raise ValueError('El archivo de tipos supera 2 MB.')
        values = json.loads(Path(path).read_text(encoding='utf-8'))
        if not isinstance(values, list):
            raise ValueError('El archivo no contiene una lista de muros.')
        if len(values) > 1000:
            raise ValueError('Se admiten hasta 1 000 tipos por importación.')
        imported = [WallType.from_dict(value) for value in values]
        current = {w.name for w in self.read()}
        for wall in imported:
            if wall.name in current and not replace:
                base, suffix = wall.name, 1
                while wall.name in current:
                    wall.name = f'{base} (importado {suffix})'
                    suffix += 1
            current.add(wall.name)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            self._ensure(connection)
            connection.executemany('INSERT OR REPLACE INTO wall_types VALUES (?, ?)',
                                   [(wall.name, json.dumps(asdict(wall), ensure_ascii=False)) for wall in imported])


def _bars(length, spacing):
    count = max(1, math.ceil(round(length / spacing, 10)) + 1)
    if count > 1000000:
        raise ValueError('La distribución supera un millón de barras. Revisa la separación.')
    return count


def generate_wall_rows(wall, length, height=None):
    """Return detail rows for concrete, formwork and reinforcement per tramo."""
    wall.validate()
    length = positive(length, 'Longitud del tramo')
    height = positive(wall.screen_height if height is None else height, 'Altura de pantalla')
    rows = []
    thickness_avg = (wall.top_thickness + wall.bottom_thickness) / 2
    rows.append(("m3", 'Muro · concreto de pantalla', [length, thickness_avg, height], 1, 'pantalla'))
    footing_width = wall.footing_left + wall.footing_right + wall.bottom_thickness
    rows.append(("m3", 'Muro · concreto de zapata', [length, footing_width, wall.footing_thickness], 1, 'zapata'))
    if wall.dentellon:
        rows.append(("m3", 'Muro · concreto de dentellón', [length, wall.dentellon_width + wall.dentellon_slope / 2, wall.dentellon_depth], 1, 'dentellon'))
    rows.extend([
        ("m2", 'Muro · encofrado de pantalla izquierda',
         [length, math.hypot(height, wall.bottom_thickness - wall.top_thickness)], 1, 'pantalla'),
        ("m2", 'Muro · encofrado de pantalla derecha', [length, height], 1, 'pantalla'),
        ("m2", 'Muro · encofrado de zapata', [length, wall.footing_thickness], 2, 'zapata'),
    ])
    distributions = list(wall.distributions)
    if wall.cut_left and not any(item['component'] == 'refuerzo_cortado' for item in distributions):
        distributions.append(dict(component='refuerzo_cortado', side='izquierda',
                                  diameter=wall.cut_diameter, spacing=wall.cut_spacing,
                                  fixed_length=wall.cut_length))
    for item in distributions:
        component = item['component']
        spacing = float(item['spacing'])
        if component == 'refuerzo_cortado' and not wall.cut_left:
            continue
        if component.startswith('dentellon') and not wall.dentellon:
            continue
        geometry = reinforcement(wall, item, length, height)
        count = _bars(geometry.distribution_length, spacing)
        row = steel_detail(f"Muro · {COMPONENTS[component]} · {SIDES[item['side']]}", count,
                           geometry.body_length, geometry.hook_start + geometry.hook_end, 0,
                           item['diameter'], 1)
        category = 'pantalla' if component.startswith(('pantalla', 'refuerzo')) else 'zapata'
        rows.append(('kg', row, 1, category))
    return rows
