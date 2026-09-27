"""Versioned, relational SQLite project files. No connection survives a save/open.

Inputs remain text to preserve decimal commas and unfinished edits losslessly.
Calculated quantities are deliberately not persisted (the Rust engine owns them).
"""
from contextlib import closing, contextmanager
import os
from pathlib import Path
import sqlite3
import tempfile

from metrado.hierarchy import MAX_ROWS, Outline, materialize
from metrado.identity import ensure_ids
from metrado.sheet import read_project, validate_project
from metrado.swelling import upgrade_legacy

APPLICATION_ID = 0x4D455452  # METR
SCHEMA_VERSION = 3
SQLITE_HEADER = b'SQLite format 3\x00'
# Visible columns and steel-specific inputs are explicit, queryable SQL columns.
INPUT_COLUMNS = ('code', 'description', 'unit', 'similar_elements', 'length',
                 'width_or_hook', 'height_or_lap', 'times_or_diameter',
                 'steel_repetitions', 'steel_bars')
CELL_INDEXES = (0, 1, 2, 3, 4, 5, 6, 7, 9, 10)
COLUMNS = ('id', 'parent_id', 'position', 'kind', *INPUT_COLUMNS, 'direct_quantity')
FIELD_LIST = ', '.join(COLUMNS)


class ConflictError(ValueError):
    pass


def _connect(path, mode):
    connection = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=' + mode,
                                 uri=True, timeout=2)
    try:
        connection.execute('PRAGMA foreign_keys = ON')
        connection.execute('PRAGMA synchronous = FULL')
    except BaseException:
        connection.close()
        raise
    return connection


@contextmanager
def _write_target(path, existed):
    if existed:
        yield path
        return
    # Publish a new database only after its first transaction completed and closed.
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.metrado-', suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
    try:
        yield temporary
        if path.exists():
            raise ConflictError('El destino se creó mientras guardabas. Elige otro nombre con Guardar como.')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _check_schema(connection):
    if connection.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID:
        raise ValueError('Este archivo no es una base de datos de Metrados.')
    version = connection.execute('PRAGMA user_version').fetchone()[0]
    if version not in (1, 2, SCHEMA_VERSION):
        raise ValueError('Versión de base de datos no compatible. No se modificó el archivo.')
    return version


def _create_swelling_table(connection):
    connection.execute('''CREATE TABLE item_swelling (
        item_id TEXT PRIMARY KEY NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
        enabled INTEGER NOT NULL CHECK(enabled IN (0, 1)),
        percent TEXT NOT NULL,
        note TEXT NOT NULL
    )''')


def _create_detail_factors(connection):
    connection.execute('''CREATE TABLE detail_swelling (
        detail_id TEXT PRIMARY KEY NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
        block_id TEXT NOT NULL,
        factor TEXT NOT NULL,
        note TEXT NOT NULL
    )''')
    connection.execute('CREATE INDEX detail_swelling_block ON detail_swelling(block_id)')


def _create_schema(connection):
    connection.execute(f'PRAGMA application_id = {APPLICATION_ID}')
    connection.execute(f'PRAGMA user_version = {SCHEMA_VERSION}')
    connection.execute('''CREATE TABLE project (
        singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
        title TEXT NOT NULL,
        revision INTEGER NOT NULL CHECK(revision >= 0)
    )''')
    connection.execute('''INSERT INTO project VALUES (1, '', 0)''')
    inputs = ', '.join(name + ' TEXT NOT NULL' for name in INPUT_COLUMNS)
    connection.execute(f'''CREATE TABLE nodes (
        id TEXT PRIMARY KEY NOT NULL,
        parent_id TEXT REFERENCES nodes(id) DEFERRABLE INITIALLY DEFERRED,
        position INTEGER NOT NULL CHECK(position >= 0),
        kind TEXT NOT NULL CHECK(kind IN ('chapter', 'item', 'detail', 'detail_group')),
        {inputs},
        direct_quantity TEXT NOT NULL,
        CHECK(parent_id IS NULL OR parent_id != id)
    )''')
    connection.execute('CREATE INDEX nodes_parent_position ON nodes(parent_id, position)')
    connection.execute('CREATE INDEX nodes_position ON nodes(position)')
    connection.execute('CREATE INDEX nodes_kind_unit ON nodes(kind, unit)')
    _create_swelling_table(connection)
    _create_detail_factors(connection)


def read_database(path):
    with closing(_connect(path, 'ro')) as connection, connection:
        # A read transaction gives title, revision and rows one consistent snapshot.
        connection.execute('BEGIN')
        version = _check_schema(connection)
        project = connection.execute('SELECT title, revision FROM project WHERE singleton=1').fetchone()
        if project is None or not isinstance(project[0], str) or type(project[1]) is not int:
            raise ValueError('La base no contiene una obra válida.')
        records = connection.execute(f'SELECT {FIELD_LIST} FROM nodes ORDER BY position LIMIT ?',
                                     (MAX_ROWS + 1,)).fetchall()
        if len(records) > MAX_ROWS:
            raise ValueError('La planilla supera el límite de 10 000 filas.')
        rows, levels, parents = [], {}, []
        for expected, record in enumerate(records):
            identity, parent, position, kind, *inputs, direct = record
            if position != expected or (parent is not None and parent not in levels):
                raise ValueError('El orden o la jerarquía de la base es inválido.')
            level = 0 if parent is None else levels[parent] + 1
            cells = [''] * 14
            for column, value in zip(CELL_INDEXES, inputs):
                cells[column] = value
            rows.append(dict(id=identity, kind=kind, level=level, cells=cells, direct=direct))
            levels[identity] = level
            parents.append(parent)
        ensure_ids(rows)
        if version >= 2:
            by_id = {row['id']: row for row in rows}
            for item_id, enabled, percent, note in connection.execute('SELECT item_id, enabled, percent, note FROM item_swelling'):
                if item_id not in by_id or enabled not in (0, 1):
                    raise ValueError('Esponjamiento asociado a una partida inválida.')
                by_id[item_id]['swelling'] = dict(enabled=bool(enabled), percent=percent, note=note)
        if version >= 3:
            for detail_id, block, factor, note in connection.execute('SELECT detail_id, block_id, factor, note FROM detail_swelling'):
                if detail_id not in by_id:
                    raise ValueError('El FE contiene una referencia inválida.')
                by_id[detail_id]['volume_factor'] = dict(block=block, factor=factor, note=note)
        title, rows = validate_project(dict(version=5, title=project[0], rows=rows))
        upgrade_legacy(rows)
        outline = Outline(rows, strict=True)
        if any(parent != (rows[index]['id'] if index is not None else None)
               for parent, index in zip(parents, outline.parents)):
            raise ValueError('Los bloques de la base no forman una jerarquía continua.')
        return title, rows, project[1]


def open_document(path):
    with open(path, 'rb') as stream:
        header = stream.read(16)
    if header == SQLITE_HEADER:
        return read_database(path)
    title, rows = read_project(path)
    ensure_ids(rows)
    return title, rows, None  # Legacy import; never save over the JSON source.


def write_database(path, title, rows, expected_revision=None):
    """One atomic transaction; unchanged nodes incur no UPDATE.

    The expected revision detects another editor's save under the same write lock.
    Omit it only for an explicitly chosen Save As destination.
    """
    normalized = materialize(rows)
    validate_project(dict(version=5, title=title, rows=normalized))
    upgrade_legacy(normalized)
    ensure_ids(normalized)
    outline = Outline(normalized, strict=True)
    records = []
    swelling_records = []
    factor_records = []
    for position, row in enumerate(normalized):
        parent = outline.parents[position]
        records.append((row['id'], normalized[parent]['id'] if parent is not None else None,
                        position, row['kind'], *(row['cells'][c] for c in CELL_INDEXES), row['direct']))
        if 'swelling' in row:
            config = row['swelling']
            swelling_records.append((row['id'], int(config['enabled']), config['percent'], config['note']))
        if 'volume_factor' in row:
            config = row['volume_factor']
            factor_records.append((row['id'], config['block'], config['factor'], config['note']))
    path = Path(path)
    existed = path.exists()
    if expected_revision is not None and not existed:
        raise ConflictError('El archivo original ya no existe. Usa Guardar como para crear otra copia.')
    with _write_target(path, existed) as destination, closing(_connect(destination, 'rw')) as connection:
        try:
            connection.execute('BEGIN IMMEDIATE')
            if existed:
                version = _check_schema(connection)
            else:
                _create_schema(connection)
                version = SCHEMA_VERSION
            project = connection.execute('SELECT title, revision FROM project WHERE singleton=1').fetchone()
            if project is None:
                raise ValueError('La base no contiene una obra válida.')
            old_title, revision = project
            if expected_revision is not None and revision != expected_revision:
                raise ConflictError('Otra instancia modificó esta obra. Abre la versión actual o usa Guardar como; no se sobrescribieron sus cambios.')
            migrated = version < SCHEMA_VERSION
            if migrated:
                if version < 2:
                    _create_swelling_table(connection)
                _create_detail_factors(connection)
                connection.execute(f'PRAGMA user_version = {SCHEMA_VERSION}')
            old_swelling = {record[0]: record for record in connection.execute('SELECT item_id, enabled, percent, note FROM item_swelling')}
            old_factors = {record[0]: record for record in connection.execute('SELECT detail_id, block_id, factor, note FROM detail_swelling')}
            old = {record[0]: record for record in connection.execute(f'SELECT {FIELD_LIST} FROM nodes')}
            current_ids = {record[0] for record in records}
            deleted = [(identity,) for identity in old if identity not in current_ids]
            updates = [record for record in records if old.get(record[0]) != record]
            connection.executemany('DELETE FROM nodes WHERE id=?', deleted)
            assignments = ', '.join(f'{name}=excluded.{name}' for name in COLUMNS[1:])
            marks = ', '.join('?' for _ in COLUMNS)
            connection.executemany(f'INSERT INTO nodes ({FIELD_LIST}) VALUES ({marks}) '
                                   f'ON CONFLICT(id) DO UPDATE SET {assignments}', updates)
            swelling_ids = {record[0] for record in swelling_records}
            removed_swelling = [(identity,) for identity in old_swelling if identity not in swelling_ids]
            changed_swelling = [record for record in swelling_records if old_swelling.get(record[0]) != record]
            connection.executemany('DELETE FROM item_swelling WHERE item_id=?', removed_swelling)
            connection.executemany('''INSERT INTO item_swelling VALUES (?, ?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET enabled=excluded.enabled, percent=excluded.percent, note=excluded.note''', changed_swelling)
            factor_ids = {record[0] for record in factor_records}
            removed_factors = [(identity,) for identity in old_factors if identity not in factor_ids]
            changed_factors = [record for record in factor_records if old_factors.get(record[0]) != record]
            connection.executemany('DELETE FROM detail_swelling WHERE detail_id=?', removed_factors)
            connection.executemany('''INSERT INTO detail_swelling VALUES (?, ?, ?, ?)
                ON CONFLICT(detail_id) DO UPDATE SET block_id=excluded.block_id, factor=excluded.factor, note=excluded.note''', changed_factors)
            if deleted or updates or old_title != title or migrated or removed_swelling or changed_swelling or removed_factors or changed_factors:
                revision += 1
                connection.execute('UPDATE project SET title=?, revision=? WHERE singleton=1', (title, revision))
            connection.commit()
            return revision
        except BaseException:
            connection.rollback()
            raise
