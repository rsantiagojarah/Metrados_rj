"""SQLite UNC URI parsing; network IO is isolated from unit tests."""
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit, unquote

from metrado.database import _connect


class NetworkPathTests(unittest.TestCase):
    def test_native_sqlite_parser_rejects_old_uri_and_accepts_unc_path(self):
        # mode=memory exercises the real URI parser without contacting the server.
        path = Path(r'\\Win-3s633a51bp0\e\Puentes\Obra.metrado.db')
        with self.assertRaisesRegex(sqlite3.OperationalError, 'invalid uri authority'):
            sqlite3.connect(path.as_uri() + '?mode=memory', uri=True)
        connection = _connect(path, 'memory')
        try:
            connection.execute('CREATE TABLE prueba (n INTEGER)')
            self.assertEqual(connection.execute('SELECT count(*) FROM prueba').fetchone(), (0,))
            self.assertEqual(connection.execute('PRAGMA database_list').fetchone()[2], '')
        finally:
            connection.close()

    def test_unc_uri_uses_empty_authority_and_keeps_full_network_path(self):
        path = Path(r'\\Win-3s633a51bp0\e\Puentes á #1\01_1_PUENTE VILLA CONF\Obra %2F.metrado.db')
        with patch('metrado.database.sqlite3.connect') as connect:
            _connect(path, 'ro')
        uri = connect.call_args.args[0]
        parsed = urlsplit(uri)
        self.assertEqual(parsed.netloc, '')
        self.assertEqual(unquote(parsed.path), path.as_posix())
        self.assertEqual(parsed.query, 'mode=ro')
        self.assertEqual(parsed.fragment, '')
        self.assertTrue(connect.call_args.kwargs['uri'])

    def test_read_only_and_read_write_do_not_create_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'missing.db'
            for mode in ('ro', 'rw'):
                with self.assertRaises(sqlite3.OperationalError):
                    _connect(path, mode)
                self.assertFalse(path.exists())

    def test_local_filename_reserved_characters_remain_literal(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'á #100% base.db'
            connection = sqlite3.connect(path)
            connection.execute('CREATE TABLE datos (n INTEGER)')
            connection.close()
            connection = _connect(path, 'ro')
            try:
                self.assertEqual(connection.execute('SELECT count(*) FROM datos').fetchone(), (0,))
                with self.assertRaises(sqlite3.OperationalError):
                    connection.execute('INSERT INTO datos VALUES (1)')
            finally:
                connection.close()


if __name__ == '__main__':
    unittest.main()
