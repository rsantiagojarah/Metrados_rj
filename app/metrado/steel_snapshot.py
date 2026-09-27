"""Validated immutable catalogues, interned by exact text, never global defaults.

Rows and undo commands may share these values safely. Editable forms still use
ordinary dictionaries; adoption replaces a snapshot rather than modifying it.
SQLite/JSON formats remain unchanged.
"""
from functools import lru_cache
from metrado.steel_config import DIAMETERS, FIELDS


class FrozenDict(dict):
    def __init__(self, values):
        if getattr(self, '_initialized', False):
            self._readonly()
        dict.__init__(self, values)
        self._initialized = True

    def _readonly(self, *args, **kwargs):
        raise TypeError('La instantánea de acero es inmutable. Sustituye el catálogo completo para actualizarla.')

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _readonly

    def __deepcopy__(self, memo):
        return self


class CatalogSnapshot(FrozenDict):
    def __init__(self, catalog):
        from metrado.steel_config import validate_catalog
        # Validate even when constructed directly, before trusting the type.
        values = {dia: dict(entry) for dia, entry in catalog.items()}
        validate_catalog(values)
        super().__init__({dia: FrozenDict(entry) for dia, entry in values.items()})


@lru_cache(maxsize=256)
def _snapshot(values):
    catalog = {dia: dict(zip(FIELDS, values[i * 3:i * 3 + 3])) for i, dia in enumerate(DIAMETERS)}
    return CatalogSnapshot(catalog)


def freeze(catalog):
    if isinstance(catalog, CatalogSnapshot):
        return catalog
    if not isinstance(catalog, dict) or set(catalog) != set(DIAMETERS):
        raise ValueError('La tabla debe contener todos los diámetros de acero.')
    values = []
    for dia in DIAMETERS:
        entry = catalog[dia]
        if not isinstance(entry, dict) or set(entry) != set(FIELDS):
            raise ValueError(f'Configuración incompleta de {dia}.')
        for field in FIELDS:
            if not isinstance(entry[field], str):
                raise ValueError('Los valores del catálogo deben ser textos numéricos.')
            values.append(entry[field])
    return _snapshot(tuple(values))


def freeze_rows(rows):
    for row in rows:
        if 'steel_catalog' in row:
            row['steel_catalog'] = freeze(row['steel_catalog'])


def editable_copy(catalog):
    return {dia: dict(entry) for dia, entry in catalog.items()}
