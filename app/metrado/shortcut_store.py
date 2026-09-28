"""User-wide, atomic SQLite persistence for keyboard shortcuts."""
from contextlib import closing
from pathlib import Path
import re
import sqlite3

from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QKeySequence

from metrado.database import ConflictError, _write_target


APPLICATION_ID = 0x53484B54
SCHEMA_VERSION = 1
MAX_ALTERNATIVES = 2
ACTION_ID = re.compile(r'^[a-z][a-z0-9_.-]{0,99}$')


def shortcut_path():
    return (Path(QStandardPaths.writableLocation(QStandardPaths.GenericConfigLocation)) /
            'Metrados' / 'atajos.sqlite3')


def portable_sequence(value):
    """Return one canonical portable Qt sequence or reject malformed input."""
    if not isinstance(value, str) or not value.strip() or len(value) > 100:
        raise ValueError('Cada atajo debe contener una combinación de teclas válida.')
    sequence = QKeySequence.fromString(value.strip(), QKeySequence.PortableText)
    portable = sequence.toString(QKeySequence.PortableText)
    if not portable:
        raise ValueError(f'El atajo «{value}» no es válido.')
    return portable


def normalize_shortcuts(configuration):
    """Validate and canonicalize an action -> alternatives mapping."""
    if not isinstance(configuration, dict) or len(configuration) > 500:
        raise ValueError('La configuración de atajos no es válida.')
    normalized = {}
    for action_id, alternatives in configuration.items():
        if not isinstance(action_id, str) or not ACTION_ID.fullmatch(action_id):
            raise ValueError('La configuración contiene una acción no válida.')
        if not isinstance(alternatives, (list, tuple)) or len(alternatives) > MAX_ALTERNATIVES:
            raise ValueError('Cada acción admite como máximo dos atajos.')
        values = [portable_sequence(value) for value in alternatives if str(value).strip()]
        if len(values) != len(set(value.casefold() for value in values)):
            raise ValueError('Una acción no puede repetir el mismo atajo.')
        normalized[action_id] = values
    return normalized


class ShortcutStore:
    """Persist shortcut choices independently from projects and steel catalogues."""
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else shortcut_path()

    @staticmethod
    def _read(connection):
        if (connection.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID or
                connection.execute('PRAGMA user_version').fetchone()[0] != SCHEMA_VERSION):
            raise ValueError('El archivo global de atajos tiene un formato no compatible.')
        revision = connection.execute(
            'SELECT revision FROM settings WHERE id=1').fetchone()[0]
        configuration = {}
        for action_id, _slot, sequence in connection.execute(
                'SELECT action_id, slot, sequence FROM shortcuts ORDER BY action_id, slot'):
            configuration.setdefault(action_id, []).append(sequence)
        return normalize_shortcuts(configuration), revision

    def read(self):
        if not self.path.exists():
            return {}, None
        with closing(sqlite3.connect(
                self.path.resolve().as_uri() + '?mode=ro', uri=True)) as connection:
            connection.execute('BEGIN')
            return self._read(connection)

    def save(self, configuration, expected_revision):
        configuration = normalize_shortcuts(configuration)
        exists = self.path.exists()
        if exists != (expected_revision is not None):
            raise ConflictError('La configuración global de atajos cambió. Vuelve a abrir el formulario.')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _write_target(self.path, exists) as target, closing(
                sqlite3.connect(target, timeout=2)) as connection:
            with connection:
                connection.execute('BEGIN IMMEDIATE')
                if exists:
                    old, revision = self._read(connection)
                    if revision != expected_revision:
                        raise ConflictError(
                            'Otra ventana modificó los atajos. Vuelve a abrir el formulario.')
                    if configuration == old:
                        return revision
                else:
                    revision = 0
                    connection.execute(f'PRAGMA application_id={APPLICATION_ID}')
                    connection.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
                    connection.execute(
                        'CREATE TABLE settings (id INTEGER PRIMARY KEY, revision INTEGER NOT NULL)')
                    connection.execute('INSERT INTO settings VALUES (1, 0)')
                    connection.execute('''CREATE TABLE shortcuts (
                        action_id TEXT NOT NULL,
                        slot INTEGER NOT NULL CHECK(slot IN (0, 1)),
                        sequence TEXT NOT NULL,
                        PRIMARY KEY(action_id, slot))''')
                connection.execute('DELETE FROM shortcuts')
                connection.executemany(
                    'INSERT INTO shortcuts VALUES (?, ?, ?)',
                    [(action_id, slot, sequence)
                     for action_id, sequences in configuration.items()
                     for slot, sequence in enumerate(sequences)])
                connection.execute(
                    'UPDATE settings SET revision=? WHERE id=1', (revision + 1,))
            return revision + 1
