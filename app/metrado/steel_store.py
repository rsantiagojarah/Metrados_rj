"""User-wide SQLite catalogue; independent from every project transaction."""
from contextlib import closing
from pathlib import Path
import sqlite3

from PySide6.QtCore import QStandardPaths

from metrado.database import ConflictError, _write_target
from metrado.steel_config import DIAMETERS, FIELDS, initial_catalog, validate_catalog
from metrado.steel_distribution import DEFAULT_TEMPLATE, validate_template

APPLICATION_ID = 0x5354454C


def catalog_path():
    return Path(QStandardPaths.writableLocation(QStandardPaths.GenericConfigLocation)) / 'Metrados' / 'aceros.sqlite3'


class CatalogStore:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else catalog_path()

    @staticmethod
    def _read(connection):
        if (connection.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID or
                connection.execute('PRAGMA user_version').fetchone()[0] != 1):
            raise ValueError('El catálogo de aceros tiene un formato no compatible.')
        revision = connection.execute('SELECT revision FROM settings WHERE id=1').fetchone()[0]
        catalog = {dia: dict(zip(FIELDS, values)) for dia, *values in
                   connection.execute('SELECT diameter, weight, hook, lap FROM steel')}
        validate_catalog(catalog)
        return catalog, revision

    def read(self):
        if not self.path.exists():
            return initial_catalog(), None
        with closing(sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True)) as connection:
            connection.execute('BEGIN')
            return self._read(connection)

    def save(self, catalog, expected_revision):
        validate_catalog(catalog)
        exists = self.path.exists()
        if exists != (expected_revision is not None):
            raise ConflictError('El catálogo global cambió. Vuelve a abrir el formulario.')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _write_target(self.path, exists) as target, closing(sqlite3.connect(target, timeout=2)) as connection:
            with connection:
                connection.execute('BEGIN IMMEDIATE')
                if exists:
                    old, revision = self._read(connection)
                    if revision != expected_revision:
                        raise ConflictError('Otra ventana modificó el catálogo. Vuelve a abrir el formulario.')
                    if catalog == old:
                        return revision
                else:
                    revision = 0
                    connection.execute(f'PRAGMA application_id={APPLICATION_ID}')
                    connection.execute('PRAGMA user_version=1')
                    connection.execute('CREATE TABLE settings (id INTEGER PRIMARY KEY, revision INTEGER NOT NULL)')
                    connection.execute('INSERT INTO settings VALUES (1, 0)')
                    connection.execute('''CREATE TABLE steel (diameter TEXT PRIMARY KEY,
                        weight TEXT NOT NULL, hook TEXT NOT NULL, lap TEXT NOT NULL)''')
                connection.executemany('INSERT OR REPLACE INTO steel VALUES (?, ?, ?, ?)',
                    [(dia, *(catalog[dia][field] for field in FIELDS)) for dia in DIAMETERS])
                connection.execute('UPDATE settings SET revision=? WHERE id=1', (revision + 1,))
            return revision + 1

    def read_distribution_format(self):
        """Read the user-wide CAD label template without modifying old stores."""
        if not self.path.exists():
            return DEFAULT_TEMPLATE, None
        with closing(sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True)) as connection:
            connection.execute('BEGIN')
            _, revision = self._read(connection)
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='cad_distribution'"
            ).fetchone()
            row = (connection.execute('SELECT template FROM cad_distribution WHERE id=1').fetchone()
                   if exists else None)
            template = row[0] if row else DEFAULT_TEMPLATE
            return validate_template(template), revision

    def save_distribution_format(self, template, expected_revision):
        """Atomically persist the CAD label template alongside the steel defaults."""
        template = validate_template(template)
        exists = self.path.exists()
        if exists != (expected_revision is not None):
            raise ConflictError('La configuración global cambió. Vuelve a abrir el formulario.')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _write_target(self.path, exists) as target, closing(sqlite3.connect(target, timeout=2)) as connection:
            with connection:
                connection.execute('BEGIN IMMEDIATE')
                if exists:
                    _, revision = self._read(connection)
                    if revision != expected_revision:
                        raise ConflictError('Otra ventana modificó la configuración global. Vuelve a abrir el formulario.')
                    table_exists = connection.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='cad_distribution'"
                    ).fetchone()
                    old_row = (connection.execute(
                        'SELECT template FROM cad_distribution WHERE id=1').fetchone()
                               if table_exists else None)
                    old = old_row[0] if old_row else DEFAULT_TEMPLATE
                    if template == old:
                        return revision
                else:
                    revision = 0
                    connection.execute(f'PRAGMA application_id={APPLICATION_ID}')
                    connection.execute('PRAGMA user_version=1')
                    connection.execute('CREATE TABLE settings (id INTEGER PRIMARY KEY, revision INTEGER NOT NULL)')
                    connection.execute('INSERT INTO settings VALUES (1, 0)')
                    connection.execute('''CREATE TABLE steel (diameter TEXT PRIMARY KEY,
                        weight TEXT NOT NULL, hook TEXT NOT NULL, lap TEXT NOT NULL)''')
                    catalog = initial_catalog()
                    connection.executemany('INSERT INTO steel VALUES (?, ?, ?, ?)',
                        [(dia, *(catalog[dia][field] for field in FIELDS)) for dia in DIAMETERS])
                connection.execute('''CREATE TABLE IF NOT EXISTS cad_distribution (
                    id INTEGER PRIMARY KEY CHECK(id=1), template TEXT NOT NULL)''')
                connection.execute('INSERT OR REPLACE INTO cad_distribution VALUES (1, ?)', (template,))
                connection.execute('UPDATE settings SET revision=? WHERE id=1', (revision + 1,))
            return revision + 1
