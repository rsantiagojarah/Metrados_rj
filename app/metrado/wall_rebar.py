"""One reinforcement geometry for takeoff, section drawing and bar development.

Coordinates use the top of the footing as y=0. No cover is deducted.
Hook values are added lengths, independent of the geometric body of the bar.
"""
from dataclasses import dataclass
from functools import lru_cache
import math
from metrado.steel_config import initial_catalog


def position_key(item):
    return item['component'] + ':' + item['side']


def path_length(points):
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


@lru_cache(maxsize=1)
def _hook_defaults():
    return initial_catalog()


def hook_lengths(wall, item):
    saved = wall.hooks.get(position_key(item))
    if saved is not None:
        return float(saved['start']), float(saved['end'])
    length = float(_hook_defaults()[item['diameter']]['hook'])
    component = item['component']
    if component in ('pantalla_vertical', 'zapata_transversal', 'dentellon_transversal'):
        return length, length
    if component == 'refuerzo_cortado':
        return 0.0, length
    return 0.0, 0.0


@dataclass(frozen=True)
class Reinforcement:
    body: tuple
    distribution: tuple
    section: bool
    hook_start: float
    hook_end: float
    start_direction: tuple
    end_direction: tuple
    fixed_body_length: float | None = None

    @property
    def body_length(self):
        return self.fixed_body_length if self.fixed_body_length is not None else path_length(self.body)

    @property
    def total_length(self):
        return self.body_length + self.hook_start + self.hook_end

    @property
    def distribution_length(self):
        return path_length(self.distribution)

    @property
    def points(self):
        a, b = self.body[0], self.body[-1]
        first = (a[0] + self.start_direction[0] * self.hook_start,
                 a[1] + self.start_direction[1] * self.hook_start)
        last = (b[0] + self.end_direction[0] * self.hook_end,
                b[1] + self.end_direction[1] * self.hook_end)
        return (first, *self.body, last)


def reinforcement(wall, item, length=1.0, height=None):
    h = wall.screen_height if height is None else height
    base, left, b, top = wall.footing_thickness, wall.footing_left, wall.bottom_thickness, wall.top_thickness
    width = left + b + wall.footing_right
    delta = b - top
    component, side = item['component'], item['side']
    left_path = ((left + delta, h), (left - delta * base / h, -base))
    right_path = ((left + b, h), (left + b, -base))
    kr, kl = left + b, left + b - wall.dentellon_width
    key_path = ((kl - wall.dentellon_slope * (base + wall.dentellon_depth) / wall.dentellon_depth, 0),
                (kl, -base-wall.dentellon_depth), (kr, -base-wall.dentellon_depth), (kr, 0))
    direction1, direction2 = (0, 1), (0, 1)
    fixed_body = None
    section = True
    distribution = ((0, 0), (length, 0))
    if component == 'pantalla_vertical':
        body = left_path if side == 'izquierda' else right_path
        direction1 = (1, 0) if side == 'izquierda' else (-1, 0)
        direction2 = (-direction1[0], 0)
    elif component == 'refuerzo_cortado':
        # The reference's cut height is above the footing. Its developed body
        # is fixed using the type's slope, even when an instance height changes.
        cut = float(item['fixed_length'] or wall.cut_length)
        fixed_body = (cut + base) * math.hypot(1, delta / wall.screen_height)
        available = path_length(left_path)
        if fixed_body > available + 1e-9:
            raise ValueError('El refuerzo cortado supera la altura disponible. Revisa la altura del tramo.')
        end = left_path[-1]
        ratio = fixed_body / available
        start = (end[0] + (left_path[0][0]-end[0])*ratio,
                 end[1] + (left_path[0][1]-end[1])*ratio)
        body = (start, end)
        direction1, direction2 = (1, 0), (-1, 0)
    elif component == 'zapata_transversal':
        y = 0 if side == 'superior' else -base
        body = ((0, y), (width, y))
        direction1 = direction2 = (0, -1 if side == 'superior' else 1)
    elif component == 'dentellon_transversal':
        body = key_path
        direction1, direction2 = (-1, 0), (1, 0)
    else:
        section = False
        body = ((0, 0), (length, 0))
        if component == 'pantalla_horizontal':
            if wall.horizontal_in_footing:
                distribution = left_path if side == 'izquierda' else right_path
            else:
                distribution = (((left+delta,h),(left,0)) if side == 'izquierda'
                                else ((left+b,h),(left+b,0)))
        elif component == 'zapata':
            y = 0 if side == 'superior' else -base
            distribution = ((0, y), (width, y))
        elif component == 'dentellon':
            # Longitudinal bars run only along the portion of the key below
            # the footing.  The transverse U bars provide the embedment.
            distribution = ((kl, -base-wall.dentellon_depth), (kr, -base-wall.dentellon_depth))
        else:
            distribution = key_path
    hook1, hook2 = hook_lengths(wall, item)
    return Reinforcement(tuple(body), tuple(distribution), section, hook1, hook2, direction1, direction2, fixed_body)


def spaced_points(path, spacing, limit=150):
    """Include both ends, limit only drawing density, never the takeoff count."""
    lengths = [math.dist(a, b) for a, b in zip(path, path[1:])]
    total = sum(lengths)
    count = max(1, math.ceil(round(total/spacing, 10)))
    indexes = range(count+1) if count <= limit else [round(i*count/limit) for i in range(limit+1)]
    result = []
    for index in indexes:
        distance = min(index*spacing, total)
        for a, b, segment in zip(path, path[1:], lengths):
            if distance <= segment + 1e-9:
                ratio = min(1, distance/segment) if segment else 0
                result.append((a[0]+(b[0]-a[0])*ratio, a[1]+(b[1]-a[1])*ratio))
                break
            distance -= segment
    return result
