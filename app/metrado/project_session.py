"""Local last-project preference; never writes or creates the remembered database."""
import json
import os
from pathlib import Path
import tempfile
from dataclasses import dataclass
import sqlite3

from PySide6.QtCore import QStandardPaths


@dataclass
class SessionLoad:
    path: Path | None = None
    document: tuple | None = None
    error: Exception | None = None
    missing: bool = False


def read_last_project(store, opener=None):
    """Read/validate only; safe in a worker, with no widgets or preference writes."""
    if store is None:
        return SessionLoad()
    if opener is None:
        from metrado.database import open_document
        opener = open_document
    path = None
    try:
        path = store.read()
        if path is None:
            return SessionLoad()
        document = opener(path)
        if document[2] is None:
            raise ValueError('La última obra debe ser una base SQLite guardada.')
        return SessionLoad(path=path, document=document)
    except FileNotFoundError as error:
        disconnected = (path is not None and str(path).startswith('\\\\') and
                        getattr(error, 'winerror', None) not in (None, 2, 3))
        return SessionLoad(path=path, error=error, missing=not disconnected)
    except (OSError, ValueError, RecursionError, sqlite3.Error) as error:
        return SessionLoad(path=path, error=error)


def session_path():
    return (Path(QStandardPaths.writableLocation(QStandardPaths.GenericConfigLocation)) /
            'Metrados' / 'sesion.json')


class LastProjectStore:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else session_path()

    def read(self):
        try:
            with self.path.open('r', encoding='utf-8') as stream:
                data = json.loads(stream.read(131073))
        except FileNotFoundError:
            return None
        if (not isinstance(data, dict) or data.get('version') != 1 or
                not isinstance(data.get('last_project'), (str, type(None)))):
            raise ValueError('El registro de la última obra no es válido.')
        value = data['last_project']
        if value is None:
            return None
        if not value or len(value) > 32767 or '\x00' in value or not Path(value).is_absolute():
            raise ValueError('La ruta de la última obra no es válida.')
        return Path(value)

    def remember(self, path):
        self._write(str(Path(path).absolute()))

    def clear(self):
        self._write(None)

    def _write(self, value):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                                             prefix='.sesion-', suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(dict(version=1, last_project=value), stream, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
